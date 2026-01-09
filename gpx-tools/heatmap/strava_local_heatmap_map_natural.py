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
#HEATMAP_MAX_SIZE = (2160, 3840) # maximum heatmap size in pixel
HEATMAP_MAX_SIZE = (2*2160, 2*3840) # maximum heatmap size in pixel
HEATMAP_MARGIN_SIZE = 32 # margin around heatmap trackpoints in pixel

PLT_COLORMAP = 'rainbow' # matplotlib color map

OSM_TILE_SERVER = 'https://tile.openstreetmap.org/{}/{}/{}.png' # OSM tile url from https://wiki.openstreetmap.org/wiki/Raster_tile_providers
OSM_TILE_SIZE = 256 # OSM tile size in pixel
OSM_MAX_ZOOM = 19 # OSM maximum zoom level
OSM_MAX_TILE_COUNT = 100 # maximum number of tiles to download

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

def main(args: Namespace) -> None:
    logToFile("start copying files from HA")
    copyFilesFromHAtoHeatmapGeneration()

    time.sleep(2)

    # read GPX trackpoints
    gpx_files = glob.glob('{}/{}'.format(args.dir,
                                         args.filter))

    if not gpx_files:
        exit('ERROR no data matching {}/{}'.format(args.dir,
                                                   args.filter))

    # if not isNewFileAvailable("lastfiles.txt",gpx_files):
    #     print("nothing changed in gpx_files")
    #     logToFile("nothing changed in gpx_files")

    #     return
    
    writeLastFileNames("lastfiles.txt",gpx_files)
    logToFile("new files, starting creation")

    gpx_files_count = 0

    lat_lon_data = []

    for gpx_file in gpx_files:
        print('Reading {}'.format(os.path.basename(gpx_file)))
        if args.year:
            with open(gpx_file, encoding='utf-8') as file:
                for line in file:
                    if '<time' in line:
                        l = line.split('>')[1][:4]

                        if not args.year or l in args.year:
                            gpx_files_count += 1

                            for line in file:
                                if '<trkpt' in line:
                                    l = line.split('"')

                                    lat_lon_data.append([float(l[1]),
                                                         float(l[3])])

                        else:
                            break
        else:
            with open(gpx_file, encoding='utf-8') as file:
                for line in file:
                    if '<trkpt' in line:
                        l = line.split('"')
                        lat_lon_data.append([float(l[1]),
                                             float(l[3])])

    lat_lon_data = np.array(lat_lon_data)

    if lat_lon_data.size == 0:
        exit('ERROR no data matching {}/{}{}'.format(args.dir,
                                                     args.filter,
                                                     ' with year {}'.format(' '.join(args.year)) if args.year else ''))

    # crop to bounding box
    lat_bound_min, lat_bound_max, lon_bound_min, lon_bound_max = args.bounds

    lat_lon_data = lat_lon_data[np.logical_and(lat_lon_data[:, 0] > lat_bound_min,
                                               lat_lon_data[:, 0] < lat_bound_max), :]
    lat_lon_data = lat_lon_data[np.logical_and(lat_lon_data[:, 1] > lon_bound_min,
                                               lat_lon_data[:, 1] < lon_bound_max), :]

    if lat_lon_data.size == 0:
        exit('ERROR no data matching {}/{} with bounds {}'.format(args.dir, args.filter, args.bounds))

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
    os.makedirs('tiles', exist_ok=True)
    logToFile("starting to create tiles")

    supertile = np.zeros(((y_tile_max-y_tile_min+1)*OSM_TILE_SIZE,
                          (x_tile_max-x_tile_min+1)*OSM_TILE_SIZE, 3))

    n = 0
    for x in range(x_tile_min, x_tile_max+1):
        for y in range(y_tile_min, y_tile_max+1):
            n += 1

            tile_file = 'tiles/tile_{}_{}_{}.png'.format(zoom, x, y)

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

    #if not args.orange:
        #supertile = np.sum(supertile*[0.2126, 0.7152, 0.0722], axis=2) # to grayscale
        #supertile = 1.0-supertile # invert colors
        #supertile = np.dstack((supertile, supertile, supertile)) # to rgb

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
    
    
    #data = gaussian_filter(data, float(sigma_pixel)) # kernel density estimation with normal kernel

    data[data > m] = m

    # equalize histogram and compute kernel density estimation
    data_hist, _ = np.histogram(data, bins=int(m+1))

    data_hist = np.cumsum(data_hist)/data.size # normalized cumulated histogram

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            data[i, j] = m*data_hist[int(data[i, j])] # histogram equalization

    #data = gaussian_filter(data, float(sigma_pixel)) # kernel density estimation with normal kernel

    data = (data-data.min())/(data.max()-data.min()) # normalize to [0,1]

    cmap = plt.get_cmap(PLT_COLORMAP)

    data_color = cmap(data)
    data_color[data_color == cmap(0.0)] = 0.0 # remove background color

    for c in range(3):
        supertile[:, :, c] = (1.0-data_color[:, :, c])*supertile[:, :, c]+data_color[:, :, c]
        #supertile[:, :, c] =  data_color[:, :, c]
        #supertile[:, :, c] = supertile[:, :, c]+, 1.0)

    # crop image
    i_min, j_min = np.min(ij_data, axis=0)
    i_max, j_max = np.max(ij_data, axis=0)

    supertile = supertile[max(i_min-HEATMAP_MARGIN_SIZE, 0):min(i_max+HEATMAP_MARGIN_SIZE, supertile.shape[0]),
                          max(j_min-HEATMAP_MARGIN_SIZE, 0):min(j_max+HEATMAP_MARGIN_SIZE, supertile.shape[1])]
    data_color = data_color[max(i_min-HEATMAP_MARGIN_SIZE, 0):min(i_max+HEATMAP_MARGIN_SIZE, data_color.shape[0]),
                          max(j_min-HEATMAP_MARGIN_SIZE, 0):min(j_max+HEATMAP_MARGIN_SIZE, data_color.shape[1])]
    # save image
    plt.imsave(args.output, supertile)
    plt.imsave("data.png", data_color)

    print('Saved {}'.format(args.output))
    logToFile("Saved from plt")
    return
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
        if not os.path.exists("templates"):
            os.mkdir("templates")
        #map_filename = os.path.join("templates","map.html")
        heatmap_filename = os.path.join("templates","heatmap.html")
        #the_map.save(map_filename)
        heat_map.save(heatmap_filename)
        print('Saved {}'.format(heatmap_filename))
        logToFile("Saved heatmap")

        #print('Saved {}'.format(map_filename))

        #print('Saved {}'.format(csv_file))

    time.sleep(3)
    copyHeatmapToHA()
    removeGPXFilesFromHA()
    return

def copyFilesFromHAtoHeatmapGeneration():
    try:
        dest_dir = "/home/boris/projects/gpx-heatmap/heatmap/gpx"
        src_dir = "/mnt/homeassistant/www/gpx/"
        for file in glob.glob(src_dir+r'*.gpx'):
            print("copying file from homeassistant: ",file)
            logToFile("Saved heatmap")

            newfile = file.split(src_dir)[1]

            newfile = os.path.join(dest_dir,newfile)

            shutil.copyfile(file, newfile)
    except:
        logToFile("copying from HA to heatmap generation failed")

        pass
def removeGPXFilesFromHA():
    try:
        src_dir = "/mnt/homeassistant/www/gpx/"
        for file in glob.glob(src_dir+r'*.gpx'):
            print("removing file from homeassistant: ",file)
            os.remove(file)
    except:
        logToFile("removing from HA gpx folder failed")

        pass

def copyHeatmapToHA():
    try:
        shutil.copyfile("/home/boris/projects/gpx-heatmap/heatmap/heatmap.png","/mnt/homeassistant/www/heatmap.png")
        shutil.copyfile("/home/boris/projects/gpx-heatmap/heatmap/templates/heatmap.html","/mnt/homeassistant/www/heatmap.html")
    except:
        logToFile("copyHeatmapToHA failed")
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

def logToFile(log):
    f = open("log.txt", "a",encoding='UTF-8')
    f.write(str(datetime.now()))
    f.write(": ")
    f.write(log + os.linesep)
    f.close()

if __name__ == '__main__':
    parser = ArgumentParser(description='Generate a PNG heatmap from local Strava GPX files',
                            epilog='Report issues to https://github.com/remisalmon/Strava-local-heatmap/issues')

    parser.add_argument('--dir', default='gpx',
                        help='GPX files directory  (default: gpx)')
    parser.add_argument('--filter', default='*.gpx',
                        help='GPX files glob filter (default: *.gpx)')
    parser.add_argument('--year', nargs='+', default=[],
                        help='GPX files year(s) filter (default: all)')
    parser.add_argument('--bounds', type=float, nargs=4, metavar='BOUND', default=[-90.0, +90.0, -180.0, +180.0],
                        help='heatmap bounding box as lat_min, lat_max, lon_min, lon_max (default: -90 +90 -180 +180)')
    parser.add_argument('--output', default='heatmap.png',
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
