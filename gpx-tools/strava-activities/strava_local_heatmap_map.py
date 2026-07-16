#this script was adapted from https://github.com/remisalmon/Strava-local-heatmap

# imports
import os
import glob
import time
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from urllib.error import URLError
from urllib.request import Request, urlopen
from argparse import ArgumentParser, Namespace
from datetime import datetime
from xml.etree import ElementTree as ET
import folium
from folium.plugins import HeatMap

import shutil

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HEATMAP_DIR = PROJECT_ROOT / 'heatmap'
HEATMAP_GPX_DIR = HEATMAP_DIR / 'gpx'
HEATMAP_TILES_DIR = HEATMAP_DIR / 'tiles'
HEATMAP_TEMPLATES_DIR = HEATMAP_DIR / 'templates'
HEATMAP_OUTPUT_FILE = HEATMAP_DIR / 'heatmap.png'
HEATMAP_LASTFILES_FILE = HEATMAP_DIR / 'lastfiles.txt'
HEATMAP_LOG_FILE = HEATMAP_DIR / 'log.txt'

# globals
HEATMAP_MAX_SIZE = (2160, 3840) # maximum heatmap size in pixel
HEATMAP_MARGIN_SIZE = 32 # margin around heatmap trackpoints in pixel

PLT_COLORMAP = 'hot' # matplotlib color map

OSM_TILE_SERVER = 'https://tile.openstreetmap.org/{}/{}/{}.png' # OSM tile url from https://wiki.openstreetmap.org/wiki/Raster_tile_providers
OSM_TILE_SIZE = 256 # OSM tile size in pixel
OSM_MAX_ZOOM = 19 # OSM maximum zoom level
OSM_MAX_TILE_COUNT = 100 # maximum number of tiles to download
BOUNDARY_MARGIN_DEG = 0.7 # degrees around previous bounds to consider "close"

# functions
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

    try:
        tree = ET.parse(gpx_file)
    except ET.ParseError:
        return points

    def local_name(tag: str) -> str:
        return tag.split('}', 1)[1] if '}' in tag else tag

    for element in tree.getroot().iter():
        if local_name(element.tag) != 'trkpt':
            continue

        lat_text = element.get('lat')
        lon_text = element.get('lon')
        if lat_text is None or lon_text is None:
            continue

        try:
            lat = float(lat_text)
            lon = float(lon_text)
        except ValueError:
            continue

        time_element = None
        for child in element:
            if local_name(child.tag) == 'time':
                time_element = child
                break

        if time_element is None or not (time_element.text or '').strip():
            continue

        timestamp = (time_element.text or '').strip()
        if year_filter is None or timestamp[:4] in year_filter:
            points.append((lat, lon))

    return points


def bounds_from_points(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    latitudes = [p[0] for p in points]
    longitudes = [p[1] for p in points]
    return min(latitudes), max(latitudes), min(longitudes), max(longitudes)


def point_close_to_bounds(point: tuple[float, float],
                          bounds: tuple[float, float, float, float],
                          margin: float) -> bool:
    lat_min, lat_max, lon_min, lon_max = bounds

    # Expand the bounding rectangle by the given margin and only consider
    # the first trackpoint as the activity anchor for inclusion.
    lat_min_exp = lat_min - margin
    lat_max_exp = lat_max + margin
    lon_min_exp = lon_min - margin
    lon_max_exp = lon_max + margin

    lat, lon = point
    return lat_min_exp <= lat <= lat_max_exp and lon_min_exp <= lon <= lon_max_exp


def start_point_close_to_bounds(points: list[tuple[float, float]],
                                bounds: tuple[float, float, float, float],
                                margin: float) -> bool:
    if not points:
        return False

    return point_close_to_bounds(points[0], bounds, margin)


def normalize_path(path: str) -> str:
    try:
        normalized = Path(path).resolve()
    except Exception:
        normalized = Path(path).absolute()

    normalized_str = normalized.as_posix()
    if os.name == 'nt':
        normalized_str = normalized_str.casefold()
    return normalized_str


def get_new_gpx_files(filename_lastfile: str, gpx_files: list[str]) -> list[str]:
    if not os.path.exists(filename_lastfile):
        return gpx_files

    last_files: set[str] = set()
    with open(filename_lastfile, 'r', encoding='UTF-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            last_files.add(normalize_path(line))

    return [file for file in gpx_files if normalize_path(file) not in last_files]


def move_gpx_to_ausgelagert(gpx_file: str, base_dir: str) -> None:
    target_dir = os.path.join(base_dir, 'ausgelagert')
    os.makedirs(target_dir, exist_ok=True)
    dest_file = os.path.join(target_dir, os.path.basename(gpx_file))
    try:
        shutil.move(gpx_file, dest_file)
        print('Moved excluded file to ausgelagert: {}'.format(os.path.basename(gpx_file)))
        logToFile('Moved excluded file to ausgelagert: {}'.format(gpx_file))
    except Exception as e:
        logToFile('Failed to move {} to ausgelagert: {}'.format(gpx_file, e))


def main(args: Namespace) -> None:
    logToFile("start copying files from HA")
    copyFilesFromHAtoHeatmapGeneration()

    time.sleep(2)
    # read GPX trackpoints
    gpx_files = glob.glob('{}/{}'.format(args.dir,
                                         args.filter))

    if not gpx_files:
        logstring = str('ERROR no data matching {}/{}'.format(args.dir,
                                                   args.filter))
        logToFile(logstring)
        exit(logstring)

    new_gpx_files = get_new_gpx_files(str(HEATMAP_LASTFILES_FILE), gpx_files)
    if not new_gpx_files:
        print("nothing changed in gpx_files")
        logToFile("nothing changed in gpx_files")
        return

    writeLastFileNames(str(HEATMAP_LASTFILES_FILE), gpx_files)
    logToFile("new files, starting creation")

    gpx_files_count = 0
    lat_lon_data: list[tuple[float, float]] = []

    year_filter = set(args.year) if args.year else None
    previous_files = [f for f in gpx_files if f not in new_gpx_files]

    for gpx_file in previous_files:
        print('Reading {}'.format(os.path.basename(gpx_file)))
        points = extract_gpx_points(gpx_file, year_filter)
        if points:
            gpx_files_count += 1
            lat_lon_data.extend(points)

    if previous_files:
        previous_bounds = bounds_from_points(lat_lon_data)
        for gpx_file in sorted(new_gpx_files, key=os.path.getmtime):
            print('Checking newest file {}'.format(os.path.basename(gpx_file)))
            new_points = extract_gpx_points(gpx_file, year_filter)
            if new_points and start_point_close_to_bounds(new_points, previous_bounds, BOUNDARY_MARGIN_DEG):
                print('Including points from {}'.format(os.path.basename(gpx_file)))
                gpx_files_count += 1
                lat_lon_data.extend(new_points)
            else:
                print('Skipping points from {} because the start point is not near existing bounds'.format(os.path.basename(gpx_file)))
                move_gpx_to_ausgelagert(gpx_file, str(HEATMAP_DIR))
    else:
        for gpx_file in new_gpx_files:
            print('Reading {}'.format(os.path.basename(gpx_file)))
            points = extract_gpx_points(gpx_file, year_filter)
            if points:
                gpx_files_count += 1
                lat_lon_data.extend(points)

    lat_lon_data = np.array(lat_lon_data)

    if lat_lon_data.size == 0:
        exit('ERROR no data matching {}/{}{}'.format(args.dir,
                                                     args.filter,
                                                     ' with year {}'.format(' '.join(args.year)) if args.year else ''))

    # determine bounding box from the aggregated data (previous + included new activities)
    lat_bound_min = float(np.min(lat_lon_data[:, 0]))
    lat_bound_max = float(np.max(lat_lon_data[:, 0]))
    lon_bound_min = float(np.min(lat_lon_data[:, 1]))
    lon_bound_max = float(np.max(lat_lon_data[:, 1]))

    # crop to bounding box (keeps previous behavior; computed from data)
    lat_lon_data = lat_lon_data[np.logical_and(lat_lon_data[:, 0] >= lat_bound_min,
                                               lat_lon_data[:, 0] <= lat_bound_max), :]
    lat_lon_data = lat_lon_data[np.logical_and(lat_lon_data[:, 1] >= lon_bound_min,
                                               lat_lon_data[:, 1] <= lon_bound_max), :]

    if lat_lon_data.size == 0:
        exit('ERROR no data matching {}/{} within computed bounds'.format(args.dir, args.filter))

    print('Read {} trackpoints'.format(lat_lon_data.shape[0]))

    # find tiles coordinates
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
        exit('ERROR zoom value too high, too many tiles to download')

    # download tiles
    HEATMAP_TILES_DIR.mkdir(parents=True, exist_ok=True)
    logToFile("starting to create tiles")

    supertile = np.zeros(((y_tile_max-y_tile_min+1)*OSM_TILE_SIZE,
                          (x_tile_max-x_tile_min+1)*OSM_TILE_SIZE, 3))

    n = 0
    for x in range(x_tile_min, x_tile_max+1):
        for y in range(y_tile_min, y_tile_max+1):
            n += 1

            tile_file = str(HEATMAP_TILES_DIR / 'tile_{}_{}_{}.png'.format(zoom, x, y))

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
        supertile = np.sum(supertile*[0.2126, 0.7152, 0.0722], axis=2) # to grayscale
        supertile = 1.0-supertile # invert colors
        supertile = np.dstack((supertile, supertile, supertile)) # to rgb

    # fill trackpoints
    sigma_pixel = args.sigma if not args.orange else 1

    data = np.zeros(supertile.shape[:2])

    xy_data = deg2xy(lat_lon_data[:, 0], lat_lon_data[:, 1], zoom)

    xy_data = np.array(xy_data).T
    xy_data = np.round((xy_data-[x_tile_min, y_tile_min])*OSM_TILE_SIZE)

    ij_data = np.flip(xy_data.astype(int), axis=1) # to supertile coordinates

    for i, j in ij_data:
        data[i-sigma_pixel:i+sigma_pixel, j-sigma_pixel:j+sigma_pixel] += 1.0

    # threshold to max accumulation of trackpoint
    if not args.orange:
        res_pixel = 156543.03*np.cos(np.radians(np.mean(lat_lon_data[:, 0])))/(2.0**zoom) # from https://wiki.openstreetmap.org/wiki/Slippy_map_tilenames

        # trackpoint max accumulation per pixel = 1/5 (trackpoint/meter) * res_pixel (meter/pixel) * activities
        # (Strava records trackpoints every 5 meters in average for cycling activites)
        m = max(1.0, np.round((1.0/5.0)*res_pixel*gpx_files_count))

    else:
        m = 1.0

    data[data > m] = m

    # equalize histogram and compute kernel density estimation
    if not args.orange:
        data_hist, _ = np.histogram(data, bins=int(m+1))

        data_hist = np.cumsum(data_hist)/data.size # normalized cumulated histogram

        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                data[i, j] = m*data_hist[int(data[i, j])] # histogram equalization

        data = gaussian_filter(data, float(sigma_pixel)) # kernel density estimation with normal kernel

        data = (data-data.min())/(data.max()-data.min()) # normalize to [0,1]

    # colorize
    if not args.orange:
        cmap = plt.get_cmap(PLT_COLORMAP)

        data_color = cmap(data)
        data_color[data_color == cmap(0.0)] = 0.0 # remove background color

        for c in range(3):
            supertile[:, :, c] = (1.0-data_color[:, :, c])*supertile[:, :, c]+data_color[:, :, c]

    else:
        color = np.array([255, 82, 0], dtype=float)/255 # orange

        for c in range(3):
            supertile[:, :, c] = np.minimum(supertile[:, :, c]+gaussian_filter(data, 1.0), 1.0) # white
            supertile[:, :, c] = np.maximum(supertile[:, :, c], 0.0)

        data = gaussian_filter(data, 0.5)
        data = (data-data.min())/(data.max()-data.min())

        for c in range(3):
            supertile[:, :, c] = (1.0-data)*supertile[:, :, c]+data*color[c]

    # crop image
    i_min, j_min = np.min(ij_data, axis=0)
    i_max, j_max = np.max(ij_data, axis=0)

    supertile = supertile[max(i_min-HEATMAP_MARGIN_SIZE, 0):min(i_max+HEATMAP_MARGIN_SIZE, supertile.shape[0]),
                          max(j_min-HEATMAP_MARGIN_SIZE, 0):min(j_max+HEATMAP_MARGIN_SIZE, supertile.shape[1])]

    # save image
    plt.imsave(args.output, supertile)

    print('Saved {}'.format(args.output))
    logToFile("Saved from plt")

    # save csv
    if args.csv and not args.orange:
        csv_file = '{}.csv'.format(os.path.splitext(args.output)[0])

        with open(csv_file, 'w') as file:
            file.write('latitude,longitude,intensity\n')

            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    if data[i, j] > 0.1:
                        x = x_tile_min+j/OSM_TILE_SIZE
                        y = y_tile_min+i/OSM_TILE_SIZE

                        lat, lon = xy2deg(x, y, zoom)

                        file.write('{},{},{}\n'.format(lat, lon, data[i,j]))

        print('Saved {}'.format(csv_file))
        logToFile("Saved csv")

    # save html
    if not args.orange:

        print("starting folium map generation")
        logToFile("starting folium map generation")

        #the_map = create_folium_map(tiles='stamenterrain')
        mapcenter_lat = (lat_min + lat_max)/2
        mapcenter_lon = (lon_min + lon_max)/2 
        #the_map = folium.Map(location=(mapcenter_lat,mapcenter_lon))
        the_map_heatmap = folium.Map(location=(mapcenter_lat,mapcenter_lon))

        heatmap_list = []
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                if data[i, j] > 0.1:
                    x = x_tile_min+j/OSM_TILE_SIZE
                    y = y_tile_min+i/OSM_TILE_SIZE

                    lat, lon = xy2deg(x, y, zoom)

                    #file.write('{},{},{}\n'.format(lat, lon, data[i,j]))
                    radius = 1 * data[i,j]
                    heatmap_value = 3*radius
                    list = [lat,lon,heatmap_value]
                    heatmap_list.append(list)
                    #folium.CircleMarker(location=[lat,lon],radius=radius,color=getFoliumColorNameFromHeatmapScore(radius)).add_to(the_map)

        heat_map = HeatMap(heatmap_list,min_opacity=0.5,blur = 3,radius=3)
        heat_map.add_to(the_map_heatmap)
        HEATMAP_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        #map_filename = os.path.join("templates","map.html")
        heatmap_filename = str(HEATMAP_TEMPLATES_DIR / "heatmap.html")
        #the_map.save(map_filename)
        heat_map.save(heatmap_filename)
        print('Saved {}'.format(heatmap_filename))
        logToFile("Saved heatmap")

        #print('Saved {}'.format(map_filename))

        #print('Saved {}'.format(csv_file))

    time.sleep(2)
    overlayFileTimeStamp("heatmap.png")
    copyHeatmapToHA()
    removeGPXFilesFromHA()
    return

def overlayFileTimeStamp(fileName):
    from PIL import Image, ImageDraw, ImageFont
    try:
        fontSize = 15
        topLeftWidthDivider = 10 # increase to make the textbox shorter in width
        topLeftHeightDivider = 45 # increase to make the textbox shorter in height
        textPadding = 2
        mydir = str(HEATMAP_DIR) + os.sep
        fileName2 = fileName.split('.')
        filePath = HEATMAP_DIR / fileName
        fileInfo = os.stat(filePath)
        timeInfo = time.strftime("%d.%m.%Y %H:%M", time.localtime(fileInfo.st_mtime))
        print(fileName + ": " + timeInfo)

        im = Image.open(filePath).convert("RGBA")
        fontSize = max(12, min(18, int(im.size[1] * 0.015)))
        try:
            font = ImageFont.truetype("DejaVuSans.ttf", size=fontSize)
        except OSError:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(im)
        try:
            text_bbox = draw.textbbox((0, 0), timeInfo, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except AttributeError:
            text_width, text_height = draw.textsize(timeInfo, font=font)

        text_x = 10
        text_y = 10
        padding = 4
        box = [text_x - padding,
               text_y - padding,
               text_x + text_width + padding,
               text_y + text_height + padding]
        draw.rectangle(box, fill=(0, 0, 0, 190))
        draw.text((text_x, text_y), timeInfo, fill=(255, 255, 255, 255), font=font)
        del draw

        output_path = HEATMAP_DIR / (fileName2[0] + ".png")
        im.save(output_path, 'PNG')
        im.close()


    except Exception as e: 
        logToFile(str(e))
        logToFile("overlaying timestamp failed")
        pass

def copyFilesFromHAtoHeatmapGeneration():
    try:
        src_dir = Path("/mnt/homeassistant/www/gpx/")
        if not src_dir.exists():
            print(f"Skipping Home Assistant import because {src_dir} does not exist")
            return

        HEATMAP_GPX_DIR.mkdir(parents=True, exist_ok=True)
        for file in src_dir.glob('*.gpx'):
            print("copying file from homeassistant: ", file)
            logToFile("copying file from homeassistant: " + str(file))
            shutil.copyfile(file, HEATMAP_GPX_DIR / file.name)
    except Exception as e:
        logToFile(str(e))
        logToFile("copying from HA to heatmap generation failed")
def removeGPXFilesFromHA():
    try:
        src_dir = Path("/mnt/homeassistant/www/gpx/")
        if not src_dir.exists():
            return

        for file in src_dir.glob('*.gpx'):
            print("removing file from homeassistant: ", file)
            file.unlink()
    except Exception as e:
        logToFile(str(e))
        logToFile("removing from HA gpx folder failed")

def copyHeatmapToHA():
    try:
        target_dir = Path("/mnt/homeassistant/www/")
        if not target_dir.exists():
            return

        shutil.copyfile(HEATMAP_TEMPLATES_DIR / "heatmap.html", target_dir / "heatmap.html")
        shutil.copyfile(HEATMAP_OUTPUT_FILE, target_dir / "heatmap.png")
    except Exception as e:
        logToFile(str(e))
        logToFile("copyHeatmapToHA failed")

def isNewFileAvailable(filename_lastfile, gpx_files):
    if not os.path.exists(filename_lastfile):
        print("file doesn't exists",filename_lastfile)
        logToFile("neue datei gefunden, starte heatmap 1")
        return True

    print("opening file",filename_lastfile)
    last_files = set()
    with open(filename_lastfile, "r", encoding='UTF-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            last_files.add(normalize_path(line))

    for file in gpx_files:
        if normalize_path(file) not in last_files:
            print("newfile found:", file)
            logToFile("neue datei gefunden, starte heatmap 2")
            return True
    logToFile("keine neue datei gefunden, keine neue heatmap")
    return False

def writeLastFileNames(filename_lastfile, gpx_files):
    print("writing all last files to file : ", filename_lastfile)
    normalized_files = sorted(normalize_path(file) for file in gpx_files)
    with open(filename_lastfile, "w", encoding='UTF-8', newline='') as f:
        for file in normalized_files:
            f.write(file + "\n")
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

def logToFile(log):
    HEATMAP_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HEATMAP_LOG_FILE, "a", encoding="utf-8") as file:
        file.write(str(datetime.now()))
        file.write(": ")
        file.write(log + os.linesep)

if __name__ == '__main__':
    parser = ArgumentParser(description='Generate a PNG heatmap from local Strava GPX files',
                            epilog='Report issues to https://github.com/remisalmon/Strava-local-heatmap/issues')

    parser.add_argument('--dir', default=str(HEATMAP_GPX_DIR),
                        help='GPX files directory  (default: gpx)')
    parser.add_argument('--filter', default='*.gpx',
                        help='GPX files glob filter (default: *.gpx)')
    parser.add_argument('--year', nargs='+', default=[],
                        help='GPX files year(s) filter (default: all)')
    # bounds are computed from previous activities and included new activities; not provided via CLI
    parser.add_argument('--output', default=str(HEATMAP_OUTPUT_FILE),
                        help='heatmap name (default: heatmap.png)')
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

    args = parser.parse_args()

    main(args)
