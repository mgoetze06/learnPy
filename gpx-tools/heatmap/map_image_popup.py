from PIL import ExifTags
from PIL.ExifTags import TAGS
from pprint import pprint
from PIL import Image
import piexif
import glob
from exif import Image as ImageExif
import folium




codec = 'ISO-8859-1'  # or latin-1

def exif_to_tag(exif_dict):
    exif_tag_dict = {}
    thumbnail = exif_dict.pop('thumbnail')
    exif_tag_dict['thumbnail'] = thumbnail.decode(codec)

    for ifd in exif_dict:
        exif_tag_dict[ifd] = {}
        for tag in exif_dict[ifd]:
            try:
                element = exif_dict[ifd][tag].decode(codec)

            except AttributeError:
                element = exif_dict[ifd][tag]

            exif_tag_dict[ifd][piexif.TAGS[ifd][tag]["name"]] = element

    return exif_tag_dict

def main_piexif(filename):

    im = Image.open(filename)

    exif_dict = piexif.load(im.info.get('exif'))
    exif_dict = exif_to_tag(exif_dict)

    pprint(exif_dict['GPS'])

def getPictureSize(filename):
    if filename:
        im = Image.open(filename)
        return im.size
    return None

def computeNewSize(finalWidth,imageSize):
    wpercent = (finalWidth / float(imageSize[0]))
    hsize = int((float(imageSize[1]) * float(wpercent)))

    return (finalWidth,hsize)
    

def decimal_coords(coords, ref):
    decimal_degrees = coords[0] + coords[1] / 60 + coords[2] / 3600
    if ref == "S" or ref =='W' :
        decimal_degrees = -decimal_degrees
    return decimal_degrees

def image_coordinates(image_path):

    with open(image_path, 'rb') as src:
        img = ImageExif(src)
    if img.has_exif:
        try:
            img.gps_longitude
            coords = (decimal_coords(img.gps_latitude,
                      img.gps_latitude_ref),
                      decimal_coords(img.gps_longitude,
                      img.gps_longitude_ref))
        except AttributeError:
            print ('No Coordinates')
    else:
        print ('The Image has no EXIF information')
        
    return({"imageTakenTime":img.datetime_original, "geolocation_lat":coords[0],"geolocation_lng":coords[1]})

if __name__ == '__main__':
    list_images = glob.glob("*.JPG")
    first = True
    #filename = 'IMG_2685.jpg'  # obviously one of your own pictures
    for image in list_images:
        filename = image
        main_piexif(filename)
        coords = image_coordinates(filename)
        print(coords)
        lat,lon = coords['geolocation_lat'], coords['geolocation_lng']
        if first:
            map = folium.Map(
                location=[lat, lon],
                zoom_start=11,
                tiles='OpenStreetMap'
            )
            fg = folium.FeatureGroup(name="Images", show=False).add_to(map)
            first = False
        print(filename)
        #filename = filename.replace("/","//")
        popuphtml = "<img src='"+filename+"' style=\"max-height: 1000px; max-width: 800px;\">"
        original_picture_size = getPictureSize(filename)
        iconSizeWidth = 50
        iconSize = computeNewSize(iconSizeWidth,original_picture_size)
        icon_image = filename
        icon = folium.CustomIcon(
            icon_image,
            icon_size=iconSize,
            icon_anchor=(iconSizeWidth//2, 0),
            popup_anchor=(iconSizeWidth//2, 0),
        )
        #if lat:
        marker = folium.Marker(
                        location=(lat,lon),
                        #icon=folium.Icon(icon='home'),
                        icon=icon,
                        popup=folium.Popup(popuphtml),
                    )
        marker.add_to(fg)
        marker = folium.Marker(
                        location=(lat,lon),
                        icon=folium.Icon(icon='camera'),
                        popup=folium.Popup(popuphtml),
                    )
        marker.add_to(fg)
    folium.LayerControl().add_to(map)
    map.save('image_popup.html')