#this script was adapted from https://github.com/remisalmon/Strava-local-heatmap

# imports
import os
import glob
import time

import numpy as np
import matplotlib.pyplot as plt

from urllib.error import URLError
from urllib.request import Request, urlopen
from argparse import ArgumentParser, Namespace
from datetime import datetime
import folium
from folium.plugins import HeatMap

import shutil
# globals
HEATMAP_MAX_SIZE = (2160, 3840) # maximum heatmap size in pixel
HEATMAP_MARGIN_SIZE = 32 # margin around heatmap trackpoints in pixel

PLT_COLORMAP = 'hot' # matplotlib color map

OSM_TILE_SERVER = 'https://tile.openstreetmap.org/{}/{}/{}.png' # OSM tile url from https://wiki.openstreetmap.org/wiki/Raster_tile_providers
OSM_TILE_SIZE = 256 # OSM tile size in pixel
OSM_MAX_ZOOM = 19 # OSM maximum zoom level
OSM_MAX_TILE_COUNT = 100 # maximum number of tiles to download
BOUNDARY_MARGIN_DEG = 0.45 # degrees around previous bounds to consider "close"
HARDCODED_BASE_DIR = '/home/boris/projects/gpx-heatmap/heatmap'
HARDCODED_GPX_DIR = os.path.join(HARDCODED_BASE_DIR, 'gpx')
HARDCODED_OUTPUT = os.path.join(HARDCODED_BASE_DIR, 'heatmap.png')

# functions

def get_base_dir(args: Namespace | None = None) -> str:
    if getattr(args, 'use_local_dir', False):
        return os.path.dirname(os.path.abspath(__file__))
    return HARDCODED_BASE_DIR


def get_runtime_paths(args: Namespace | None = None) -> dict[str, str]:
    base_dir = get_base_dir(args)
    gpx_dir = getattr(args, 'dir', None)
    if not gpx_dir:
        gpx_dir = os.path.join(base_dir, 'gpx') if getattr(args, 'use_local_dir', False) else HARDCODED_GPX_DIR

    if not os.path.isabs(gpx_dir):
        gpx_dir = os.path.abspath(gpx_dir)

    return {
        'base_dir': base_dir,
        'gpx_dir': gpx_dir,
        'lastfiles': os.path.join(base_dir, 'lastfiles.txt'),
        'logfile': os.path.join(base_dir, 'log.txt'),
        'templates_dir': os.path.join(base_dir, 'templates'),
        'tiles_dir': os.path.join(base_dir, 'tiles'),
        'ausgelagert_dir': os.path.join(base_dir, 'ausgelagert'),
    }


def resolve_output_path(args: Namespace | None = None) -> str:
    if getattr(args, 'output', None):
        return os.path.abspath(args.output)

    if getattr(args, 'use_local_dir', False):
        return os.path.join(get_base_dir(args), 'heatmap.png')

    return HARDCODED_OUTPUT
def deg2xy(lat_deg: float, lon_deg: float, zoom: int) -> tuple[float, float]:
    """Returns OSM coordinates (x,y) from (lat,lon) in degree"""

    # from https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
    lat_rad = np.radians(lat_deg)
    n = 2.0**zoom
    x = (lon_deg+180.0)/360.0*n
    y = (1.0-np.arcsinh(np.tan(lat_rad))/np.pi)/2.0*n

    return x, y

def xy2deg(x: float, y: float, zoom: int) -> tuple[float, float]:
    """Returns (lat, lon) in degree from OSM coordinates (x,y)"""

    # from https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames
    n = 2.0**zoom
    lon_deg = x/n*360.0-180.0
    lat_rad = np.arctan(np.sinh(np.pi*(1.0-2.0*y/n)))
    lat_deg = np.degrees(lat_rad)

    return lat_deg, lon_deg

def gaussian_filter(image: np.ndarray, sigma: float) -> np.ndarray:
    """Returns image filtered with a gaussian function of variance sigma**2"""

    i, j = np.meshgrid(np.arange(image.shape[0]),
                       np.arange(image.shape[1]),
                       indexing='ij')

    mu = (int(image.shape[0]/2.0),
          int(image.shape[1]/2.0))

    gaussian = 1.0/(2.0*np.pi*sigma*sigma)*np.exp(-0.5*(((i-mu[0])/sigma)**2+\
                                                        ((j-mu[1])/sigma)**2))

    gaussian = np.roll(gaussian, (-mu[0], -mu[1]), axis=(0, 1))

    image_fft = np.fft.rfft2(image)
    gaussian_fft = np.fft.rfft2(gaussian)

    image = np.fft.irfft2(image_fft*gaussian_fft)

    return image


def extract_gpx_points(gpx_file: str, year_filter: set[str] | None = None) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    current_point: tuple[float, float] | None = None

    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    text = None

    for encoding in encodings:
        try:
            with open(gpx_file, 'r', encoding=encoding) as file:
                text = file.read()
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        print('Skipping {} because it could not be decoded'.format(gpx_file))
        return points

    for line in text.splitlines():
        if '<trkpt' in line:
            parts = line.split('"')
            if len(parts) >= 4:
                try:
                    lat = float(parts[1])
                    lon = float(parts[3])
                    current_point = (lat, lon)
                except ValueError:
                    current_point = None
            else:
                current_point = None
        elif current_point is not None and '<time' in line:
            if year_filter is None:
                points.append(current_point)
            else:
                year = line.split('>')[1][:4]
                if year in year_filter:
                    points.append(current_point)
            current_point = None

    return points


def bounds_from_points(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    latitudes = [p[0] for p in points]
    longitudes = [p[1] for p in points]
    return min(latitudes), max(latitudes), min(longitudes), max(longitudes)


def points_close_to_bounds(points: list[tuple[float, float]],
                           bounds: tuple[float, float, float, float],
                           margin: float) -> bool:
    lat_min, lat_max, lon_min, lon_max = bounds
    for lat, lon in points:
        if (
            abs(lat - lat_min) <= margin or
            abs(lat - lat_max) <= margin or
            abs(lon - lon_min) <= margin or
            abs(lon - lon_max) <= margin
        ):
            return True
    return False


def get_new_gpx_files(filename_lastfile: str, gpx_files: list[str]) -> list[str]:
    if not os.path.exists(filename_lastfile):
        return gpx_files

    last_files: list[str] = []
    with open(filename_lastfile, 'r', encoding='UTF-8') as file:
        for line in file:
            last_files.append(line.rstrip())

    return [file for file in gpx_files if file not in last_files]


def move_gpx_to_ausgelagert(gpx_file: str, base_dir: str, args: Namespace | None = None) -> None:
    target_dir = os.path.join(base_dir, 'ausgelagert')
    os.makedirs(target_dir, exist_ok=True)
    dest_file = os.path.join(target_dir, os.path.basename(gpx_file))
    try:
        shutil.move(gpx_file, dest_file)
        print('Moved excluded file to ausgelagert: {}'.format(os.path.basename(gpx_file)))
        logToFile('Moved excluded file to ausgelagert: {}'.format(gpx_file), args)
    except Exception as e:
        logToFile('Failed to move {} to ausgelagert: {}'.format(gpx_file, e), args)


def filter_points_by_bounds(points: list[tuple[float, float]] | np.ndarray,
                             bounds: tuple[float, float, float, float]) -> np.ndarray:
    lat_lon_data = np.array(points, dtype=float)
    if lat_lon_data.size == 0:
        return np.empty((0, 2), dtype=float)

    lat_bound_min, lat_bound_max, lon_bound_min, lon_bound_max = bounds
    lat_lon_data = lat_lon_data[np.logical_and(lat_lon_data[:, 0] > lat_bound_min,
                                               lat_lon_data[:, 0] < lat_bound_max), :]
    lat_lon_data = lat_lon_data[np.logical_and(lat_lon_data[:, 1] > lon_bound_min,
                                               lat_lon_data[:, 1] < lon_bound_max), :]

    return lat_lon_data


def ride_bounds(points: np.ndarray) -> tuple[float, float, float, float]:
    if points.size == 0:
        return 0.0, 0.0, 0.0, 0.0

    points = np.asarray(points, dtype=float)
    if points.ndim == 1:
        points = points.reshape(1, -1)

    latitudes = points[:, 0]
    longitudes = points[:, 1]
    return float(np.min(latitudes)), float(np.max(latitudes)), float(np.min(longitudes)), float(np.max(longitudes))


def bounds_overlap(bounds_a: tuple[float, float, float, float],
                   bounds_b: tuple[float, float, float, float]) -> bool:
    lat_min_a, lat_max_a, lon_min_a, lon_max_a = bounds_a
    lat_min_b, lat_max_b, lon_min_b, lon_max_b = bounds_b

    return not (
        lat_max_a < lat_min_b or
        lat_min_a > lat_max_b or
        lon_max_a < lon_min_b or
        lon_min_a > lon_max_b
    )


def cluster_rides_by_bbox(rides: list[tuple[str, np.ndarray]],
                          min_cluster_size: int = 2) -> list[list[tuple[str, np.ndarray]]]:
    clusters: list[list[tuple[str, np.ndarray]]] = []

    for ride_name, points in rides:
        ride_points = np.asarray(points, dtype=float)
        if ride_points.size == 0:
            continue
        if ride_points.ndim == 1:
            ride_points = ride_points.reshape(1, -1)

        ride_bbox = ride_bounds(ride_points)
        assigned_cluster = None

        for cluster in clusters:
            cluster_bboxes = [ride_bounds(np.asarray(item[1], dtype=float)) for item in cluster]
            if any(bounds_overlap(ride_bbox, cluster_bbox) for cluster_bbox in cluster_bboxes):
                assigned_cluster = cluster
                break

        if assigned_cluster is None:
            clusters.append([(ride_name, ride_points)])
        else:
            assigned_cluster.append((ride_name, ride_points))

    return [cluster for cluster in clusters if len(cluster) >= min_cluster_size]


def split_rides_for_main_and_clusters(rides: list[tuple[str, np.ndarray]],
                                      clusters: list[list[tuple[str, np.ndarray]]]) -> tuple[list[tuple[str, np.ndarray]], list[list[tuple[str, np.ndarray]]]]:
    if not clusters:
        return list(rides), []

    sorted_clusters = sorted(clusters, key=lambda cluster: len(cluster), reverse=True)
    main_cluster = sorted_clusters[0]
    remaining_clusters = sorted_clusters[1:]
    return list(main_cluster), remaining_clusters


def generate_heatmap_from_points(lat_lon_data: np.ndarray,
                                 output_path: str,
                                 args: Namespace,
                                 gpx_files_count: int,
                                 bounds: tuple[float, float, float, float] | None = None) -> None:
    if lat_lon_data.size == 0:
        raise ValueError('No points available for heatmap generation')

    lat_lon_data = np.array(lat_lon_data, dtype=float)
    if lat_lon_data.ndim == 1:
        lat_lon_data = lat_lon_data.reshape(1, -1)

    bounds = args.bounds if bounds is None else bounds
    lat_lon_data = filter_points_by_bounds(lat_lon_data, bounds)
    if lat_lon_data.size == 0:
        raise ValueError('No points available for heatmap generation after bounds filtering')

    print('Read {} trackpoints'.format(lat_lon_data.shape[0]))

    lat_min, lon_min = np.min(lat_lon_data, axis=0)
    lat_max, lon_max = np.max(lat_lon_data, axis=0)

    if args.zoom > -1:
        zoom = min(args.zoom, OSM_MAX_ZOOM)

        x_tile_min, y_tile_max = map(int, deg2xy(lat_min, lon_min, zoom))
        x_tile_max, y_tile_min = map(int, deg2xy(lat_max, lon_max, zoom))

    else:
        zoom = OSM_MAX_ZOOM

        while True:
            x_tile_min, y_tile_max = map(int, deg2xy(lat_min, lon_min, zoom))
            x_tile_max, y_tile_min = map(int, deg2xy(lat_max, lon_max, zoom))

            if ((x_tile_max-x_tile_min+1)*OSM_TILE_SIZE <= HEATMAP_MAX_SIZE[0] and
                (y_tile_max-y_tile_min+1)*OSM_TILE_SIZE <= HEATMAP_MAX_SIZE[1]):
                break

            zoom -= 1

        print('Auto zoom = {}'.format(zoom))

    tile_count = (x_tile_max-x_tile_min+1)*(y_tile_max-y_tile_min+1)

    if tile_count > OSM_MAX_TILE_COUNT:
        raise ValueError('ERROR zoom value too high, too many tiles to download')

    paths = get_runtime_paths(args)
    tiles_dir = paths['tiles_dir']
    os.makedirs(tiles_dir, exist_ok=True)
    logToFile('starting to create tiles', args)

    supertile = np.zeros(((y_tile_max-y_tile_min+1)*OSM_TILE_SIZE,
                          (x_tile_max-x_tile_min+1)*OSM_TILE_SIZE, 3))

    n = 0
    for x in range(x_tile_min, x_tile_max+1):
        for y in range(y_tile_min, y_tile_max+1):
            n += 1

            tile_file = os.path.join(tiles_dir, 'tile_{}_{}_{}.png'.format(zoom, x, y))

            if not glob.glob(tile_file):
                print('downloading tile {}/{}'.format(n, tile_count))

                url = OSM_TILE_SERVER.format(zoom, x, y)

                request = Request(url, headers={'User-Agent': 'Strava-local-heatmap/master'})

                try:
                    with urlopen(request, timeout=1) as response:
                        data = response.read()

                    with open(tile_file, 'wb') as file:
                        file.write(data)

                    tile = plt.imread(tile_file)

                except URLError as e:
                    print('ERROR downloading failed, using blank tile: {}'.format(e))

                    tile = np.ones((OSM_TILE_SIZE,
                                    OSM_TILE_SIZE, 3))

                finally:
                    time.sleep(0.1)

            else:
                print('reading local tile {}/{}'.format(n, tile_count))

                tile = plt.imread(tile_file)

            i = y-y_tile_min
            j = x-x_tile_min

            supertile[i*OSM_TILE_SIZE:(i+1)*OSM_TILE_SIZE,
                      j*OSM_TILE_SIZE:(j+1)*OSM_TILE_SIZE, :] = tile[:, :, :3]

    if not args.orange:
        supertile = np.sum(supertile*[0.2126, 0.7152, 0.0722], axis=2)
        supertile = 1.0-supertile
        supertile = np.dstack((supertile, supertile, supertile))

    sigma_pixel = args.sigma if not args.orange else 1
    data = np.zeros(supertile.shape[:2])

    xy_data = deg2xy(lat_lon_data[:, 0], lat_lon_data[:, 1], zoom)
    xy_data = np.array(xy_data).T
    xy_data = np.round((xy_data-[x_tile_min, y_tile_min])*OSM_TILE_SIZE)
    ij_data = np.flip(xy_data.astype(int), axis=1)

    for i, j in ij_data:
        data[i-sigma_pixel:i+sigma_pixel, j-sigma_pixel:j+sigma_pixel] += 1.0

    if not args.orange:
        res_pixel = 156543.03*np.cos(np.radians(np.mean(lat_lon_data[:, 0])))/(2.0**zoom)
        m = max(1.0, np.round((1.0/5.0)*res_pixel*gpx_files_count))
    else:
        m = 1.0

    data[data > m] = m

    if not args.orange:
        data_hist, _ = np.histogram(data, bins=int(m+1))
        data_hist = np.cumsum(data_hist)/data.size

        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                data[i, j] = m*data_hist[int(data[i, j])]

        data = gaussian_filter(data, float(sigma_pixel))
        data = (data-data.min())/(data.max()-data.min())

    if not args.orange:
        cmap = plt.get_cmap(PLT_COLORMAP)
        data_color = cmap(data)
        data_color[data_color == cmap(0.0)] = 0.0

        for c in range(3):
            supertile[:, :, c] = (1.0-data_color[:, :, c])*supertile[:, :, c]+data_color[:, :, c]
    else:
        color = np.array([255, 82, 0], dtype=float)/255

        for c in range(3):
            supertile[:, :, c] = np.minimum(supertile[:, :, c]+gaussian_filter(data, 1.0), 1.0)
            supertile[:, :, c] = np.maximum(supertile[:, :, c], 0.0)

        data = gaussian_filter(data, 0.5)
        data = (data-data.min())/(data.max()-data.min())

        for c in range(3):
            supertile[:, :, c] = (1.0-data)*supertile[:, :, c]+data*color[c]

    i_min, j_min = np.min(ij_data, axis=0)
    i_max, j_max = np.max(ij_data, axis=0)

    supertile = supertile[max(i_min-HEATMAP_MARGIN_SIZE, 0):min(i_max+HEATMAP_MARGIN_SIZE, supertile.shape[0]),
                          max(j_min-HEATMAP_MARGIN_SIZE, 0):min(j_max+HEATMAP_MARGIN_SIZE, supertile.shape[1])]

    output_path = os.path.abspath(output_path)
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    plt.imsave(output_path, supertile)

    print('Saved {}'.format(output_path))
    logToFile('Saved from plt', args)

    if args.csv and not args.orange:
        csv_file = '{}.csv'.format(os.path.splitext(output_path)[0])

        with open(csv_file, 'w', encoding='utf-8') as file:
            file.write('latitude,longitude,intensity\n')

            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    if data[i, j] > 0.1:
                        x = x_tile_min+j/OSM_TILE_SIZE
                        y = y_tile_min+i/OSM_TILE_SIZE

                        lat, lon = xy2deg(x, y, zoom)

                        file.write('{},{},{}\n'.format(lat, lon, data[i,j]))

        print('Saved {}'.format(csv_file))
        logToFile('Saved csv', args)

    if not args.orange:
        print('starting folium map generation')
        logToFile('starting folium map generation', args)

        mapcenter_lat = (lat_min + lat_max)/2
        mapcenter_lon = (lon_min + lon_max)/2
        the_map_heatmap = folium.Map(location=(mapcenter_lat,mapcenter_lon))

        heatmap_list = []
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                if data[i, j] > 0.1:
                    x = x_tile_min+j/OSM_TILE_SIZE
                    y = y_tile_min+i/OSM_TILE_SIZE

                    lat, lon = xy2deg(x, y, zoom)
                    radius = 1 * data[i,j]
                    heatmap_value = 3*radius
                    heatmap_list.append([lat, lon, heatmap_value])

        heat_map = HeatMap(heatmap_list,min_opacity=0.5,blur = 3,radius=3)
        heat_map.add_to(the_map_heatmap)

        template_dir = paths['templates_dir']
        os.makedirs(template_dir, exist_ok=True)
        html_output = os.path.join(template_dir, '{}.html'.format(os.path.splitext(os.path.basename(output_path))[0]))
        heat_map.save(html_output)
        print('Saved {}'.format(html_output))
        logToFile('Saved heatmap', args)


def main(args: Namespace) -> None:
    paths = get_runtime_paths(args)
    output_path = resolve_output_path(args)

    if not args.use_local_dir:
        logToFile("start copying files from HA", args)
        copyFilesFromHAtoHeatmapGeneration(args)
        time.sleep(2)

    # read GPX trackpoints
    gpx_files = glob.glob(os.path.join(paths['gpx_dir'], args.filter))

    if not gpx_files:
        logstring = str('ERROR no data matching {}/{}'.format(paths['gpx_dir'], args.filter))
        logToFile(logstring, args)
        exit(logstring)

    new_gpx_files = get_new_gpx_files(paths['lastfiles'], gpx_files)
    if not new_gpx_files:
        print("nothing changed in gpx_files")
        logToFile("nothing changed in gpx_files", args)
        return

    writeLastFileNames(paths['lastfiles'], gpx_files)
    logToFile("new files, starting creation", args)

    gpx_files_count = 0
    lat_lon_data: list[tuple[float, float]] = []
    included_rides: list[tuple[str, np.ndarray]] = []

    year_filter = set(args.year) if args.year else None
    previous_files = [f for f in gpx_files if f not in new_gpx_files]

    for gpx_file in previous_files:
        print('Reading {}'.format(os.path.basename(gpx_file)))
        points = extract_gpx_points(gpx_file, year_filter)
        if points:
            filtered_points = filter_points_by_bounds(points, args.bounds)
            if filtered_points.size:
                gpx_files_count += 1
                included_rides.append((os.path.basename(gpx_file), filtered_points))
                lat_lon_data.extend(filtered_points.tolist())

    if previous_files:
        previous_bounds = bounds_from_points(lat_lon_data) if lat_lon_data else None
        for gpx_file in sorted(new_gpx_files, key=os.path.getmtime):
            print('Checking newest file {}'.format(os.path.basename(gpx_file)))
            new_points = extract_gpx_points(gpx_file, year_filter)
            filtered_new_points = filter_points_by_bounds(new_points, args.bounds)
            if filtered_new_points.size and (previous_bounds is None or points_close_to_bounds(filtered_new_points, previous_bounds, BOUNDARY_MARGIN_DEG)):
                print('Including points from {}'.format(os.path.basename(gpx_file)))
                gpx_files_count += 1
                included_rides.append((os.path.basename(gpx_file), filtered_new_points))
                lat_lon_data.extend(filtered_new_points.tolist())
            else:
                print('Skipping points from {} because they are not near existing bounds'.format(os.path.basename(gpx_file)))
                move_gpx_to_ausgelagert(gpx_file, paths['base_dir'], args)
    else:
        for gpx_file in new_gpx_files:
            print('Reading {}'.format(os.path.basename(gpx_file)))
            points = extract_gpx_points(gpx_file, year_filter)
            if points:
                filtered_points = filter_points_by_bounds(points, args.bounds)
                if filtered_points.size:
                    gpx_files_count += 1
                    included_rides.append((os.path.basename(gpx_file), filtered_points))
                    lat_lon_data.extend(filtered_points.tolist())

    lat_lon_data = np.array(lat_lon_data, dtype=float)

    if lat_lon_data.size == 0:
        exit('ERROR no data matching {}/{}{}'.format(paths['gpx_dir'],
                                                     args.filter,
                                                     ' with year {}'.format(' '.join(args.year)) if args.year else ''))

    print('Read {} trackpoints'.format(lat_lon_data.shape[0]))

    if args.cluster_distance > 0:
        clusters = cluster_rides_by_bbox(included_rides,
                                         min_cluster_size=args.cluster_min_size)
        main_rides, _ = split_rides_for_main_and_clusters(included_rides, clusters)
        main_points = np.vstack([points for _, points in main_rides]) if main_rides else np.empty((0, 2), dtype=float)
        generate_heatmap_from_points(main_points, output_path, args, len(main_rides), bounds=args.bounds)

        output_dir = os.path.dirname(output_path)
        base_name = os.path.splitext(os.path.basename(output_path))[0]

        for index, cluster in enumerate(clusters, start=1):
            cluster_points = np.vstack([points for _, points in cluster])
            cluster_output = os.path.join(output_dir, '{}_cluster_{:02d}.png'.format(base_name, index))
            print('Generating clustered heatmap {} from {} rides'.format(cluster_output, len(cluster)))
            generate_heatmap_from_points(cluster_points, cluster_output, args, len(cluster), bounds=args.bounds)
    else:
        generate_heatmap_from_points(lat_lon_data, output_path, args, gpx_files_count, bounds=args.bounds)

    time.sleep(2)
    overlayFileTimeStamp(os.path.basename(output_path), args)
    if not args.use_local_dir:
        copyHeatmapToHA(args)
        removeGPXFilesFromHA()
    return

def overlayFileTimeStamp(fileName, args: Namespace | None = None):
    from PIL import Image, ImageDraw, ImageFont
    try:
        fontSize = 15
        topLeftWidthDivider = 10 # increase to make the textbox shorter in width
        topLeftHeightDivider = 45 # increase to make the textbox shorter in height
        textPadding = 2 # 
        mydir = get_base_dir(args) + "/"
        fileName2 = fileName.split('.')
        fileInfo = os.stat(mydir + fileName)
        timeInfo = time.strftime("%d.%m.%Y", time.localtime(fileInfo.st_mtime))
        print(fileName + ": " + timeInfo)
        
        im = Image.open(mydir + fileName)
        #myfont = ImageFont.truetype(fontFile, fontSize)
        topLeftWidth = int(im.size[0] - (im.size[0] / topLeftWidthDivider))
        topLeftHeight = int(im.size[1] - (im.size[1] / topLeftHeightDivider))
        draw = ImageDraw.Draw(im)
        draw.rectangle([topLeftWidth, topLeftHeight, im.size[0], im.size[1]], fill="grey")
        #draw.text([topLeftWidth + textPadding, topLeftHeight + textPadding], timeInfo, fill="lime", font=myfont)
        draw.text([topLeftWidth + textPadding, topLeftHeight + textPadding], timeInfo, fill="white")
        del draw
        
        #write image
        im.save(mydir + fileName2[0] + ".png", 'PNG')


    except Exception as e: 
        logToFile(str(e), args)
        logToFile("overlaying timestamp failed", args)
        pass

def copyFilesFromHAtoHeatmapGeneration(args: Namespace | None = None):
    try:
        dest_dir = get_runtime_paths(args)['gpx_dir']
        src_dir = "/mnt/homeassistant/www/gpx/"
        for file in glob.glob(src_dir+r'*.gpx'):
            print("copying file from homeassistant: ",file)
            logToFile("copying file from homeassistant: " + str(file), args)

            newfile = file.split(src_dir)[1]

            newfile = os.path.join(dest_dir,newfile)

            shutil.copyfile(file, newfile)
    except Exception as e: 
        logToFile(str(e), args)
        logToFile("copying from HA to heatmap generation failed", args)

        pass
def removeGPXFilesFromHA():
    try:
        src_dir = "/mnt/homeassistant/www/gpx/"
        for file in glob.glob(src_dir+r'*.gpx'):
            print("removing file from homeassistant: ",file)
            os.remove(file)
    except Exception as e: 
        logToFile(str(e))
        logToFile("removing from HA gpx folder failed")

        pass

def copyHeatmapToHA(args: Namespace | None = None):
    try:
       paths = get_runtime_paths(args)
       template_output = os.path.join(paths['templates_dir'], 'heatmap.html')
       image_output = resolve_output_path(args)
       shutil.copyfile(template_output, "/mnt/homeassistant/www/heatmap.html")
       shutil.copyfile(image_output, "/mnt/homeassistant/www/heatmap.png")
    except Exception as e:
        logToFile(str(e), args)
        logToFile("copyHeatmapToHA failed", args)
        pass

def isNewFileAvailable(filename_lastfile, gpx_files):
    last_files = []
    if not os.path.exists(filename_lastfile):
        print("file doesn't exists",filename_lastfile)
        logToFile("neue datei gefunden, starte heatmap 1")
        return True
    
    print("opening file",filename_lastfile)
    with open(filename_lastfile, "r",encoding='UTF-8') as file:
        for line in file:
            #print(line.rstrip())
            last_files.append(line.rstrip())

    for file in gpx_files:
        if file not in last_files:
            print("newfile found:", file)
            logToFile("neue datei gefunden, starte heatmap 2")

            return True
        #print("found file in lastfiles: ",file)
    logToFile("keine neue datei gefunden, keine neue heatmap")

    return False

def writeLastFileNames(filename_lastfile, gpx_files):
    print("writing all last files to file : ",filename_lastfile)
    f = open(filename_lastfile, "w",encoding='UTF-8')
    for file in gpx_files:
        f.write(file + os.linesep)
        #print(file)
    f.close()
    logToFile("writing all last files to file : " + filename_lastfile)


def getFoliumColorNameFromHeatmapScore(score):
    name = 'green'
    if score < 0.2:
        return 'darkgreen'

    if score < 0.4:
        return 'green'

    if score < 0.6:
        return 'lightgreen'

    if score < 1:
        return 'red'



    return name

def logToFile(log, args: Namespace | None = None):
    paths = get_runtime_paths(args)
    log_dir = os.path.dirname(paths['logfile'])
    os.makedirs(log_dir, exist_ok=True)
    with open(paths['logfile'], "a", encoding='UTF-8') as f:
        f.write(str(datetime.now()))
        f.write(": ")
        f.write(log + os.linesep)

if __name__ == '__main__':
    parser = ArgumentParser(description='Generate a PNG heatmap from local Strava GPX files',
                            epilog='Report issues to https://github.com/remisalmon/Strava-local-heatmap/issues')

    parser.add_argument('--dir', default=None,
                        help='GPX files directory (defaults to the selected base directory gpx folder)')
    parser.add_argument('--filter', default='*.gpx',
                        help='GPX files glob filter (default: *.gpx)')
    parser.add_argument('--year', nargs='+', default=[],
                        help='GPX files year(s) filter (default: all)')
    parser.add_argument('--bounds', type=float, nargs=4, metavar='BOUND', default=[-90.0, +90.0, -180.0, +180.0],
                        help='heatmap bounding box as lat_min, lat_max, lon_min, lon_max (default: -90 +90 -180 +180)')
    parser.add_argument('--output', default=None,
                        help='heatmap name (default: heatmap.png in the selected base directory)')
    parser.add_argument('--zoom', type=int, default=-1,
                        help='heatmap zoom level 0-19 or -1 for auto (default: -1)')
    parser.add_argument('--sigma', type=int, default=1,
                        help='heatmap Gaussian kernel sigma in pixel (default: 1)')
    parser.add_argument('--orange', action='store_true',
                        help='not a heatmap...')
    parser.add_argument('--csv', action='store_true',
                        help='also save the heatmap data to a CSV file')
    parser.add_argument('--html', action='store_true',
                        help='also save the heatmap data to a html map')
    parser.add_argument('--cluster-distance', type=float, default=0.35,
                        help='maximum degree distance for clustering rides by their centroids (default: 0.35)')
    parser.add_argument('--cluster-min-size', type=int, default=2,
                        help='minimum number of rides needed for an extra cluster heatmap (default: 2)')
    parser.add_argument('--use-local-dir', action='store_true',
                        help='use the local project directory instead of the hard-coded /home/boris paths')

    args = parser.parse_args()

    main(args)
