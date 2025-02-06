import gpxpy
import gpxpy.gpx
import numpy as np
import folium
import json
import os
from urllib.parse import urlparse

def parseGoogleMapsLinkToLatLon(url):
    if url == None:
        return None,None
    
    # Extract the path from the URL
    parsed_url = urlparse(url)
    path = parsed_url.path  # This will give '/maps/@51.4886157,12.5599667,40837m/data=!3m1!1e3'

    # Split the path to get the coordinates
    coordinates_part = path.split('@')[1]  # This will give '51.4886157,12.5599667,40837m/data=!3m1!1e3'
    coordinates = coordinates_part.split(',')  # Split by comma

    # Extract latitude and longitude
    lat = float(coordinates[0])  # Latitude
    lon = float(coordinates[1])  # Longitude

    # Print the results
    print(f"Latitude: {lat}")
    print(f"Longitude: {lon}")

    return lat,lon

def getMapCenter():
    lat = 51.5969943
    lon = 12.3482471

    return lat,lon

def getLocation(immo):

    #lat = 51.542011
    #lon = 12.4234463

    lat = immo["lat"]
    lon = immo["lon"]
    return lat,lon

def getTitle(immo):

    title = immo["title"]
    return title

def getLocationAdress(immo):

    street = immo["address"]
    city = immo["city"]
    address = street + " " + city
    return address

def getPrice(immo):

    return immo["price"]

def getLivingArea(immo):
    return immo["livingarea"]

def getPropertyArea(immo):
    return immo["propertyarea"]

def getYearOfConstruction(immo):
    return immo["constructionyear"]

def getLink(immo):
    return immo["link"]

def getTitleFilename(immo):
    id = str(immo["id"])

    filename = "title_"+id
    extension = getFileExtension(filename)
    if extension == None:
        file = "static/images/title_None.jpg"
    else:
        file = "static/images/"+filename+extension
    print(file)
    return file

def getFileExtension(filename):
    files = os.listdir("static/images/")
    for path in files:
        if filename in path:
            return os.path.splitext(path)[1]
        
    return None

def generateAndSaveMap():
    map = generateMap()
    map.save('templates/map.html')

def generateMap():
    lat,lon = getMapCenter()
    map = folium.Map(
        location=[lat, lon],
        zoom_start=11,
        tiles='OpenStreetMap'
    )
    with open('immo.json', encoding='utf-8') as f:
        immos = json.load(f)
        #print(d)

    for immo in immos["immos"]:
        print(immo)
        popuphtml = "<h1>" + getTitle(immo) + "</h1><br>"
        popuphtml = popuphtml + "<table>"
        popuphtml = popuphtml + "<tr><td>Preis</td><td>" + str(getPrice(immo)) + " €</td></tr>"
        popuphtml = popuphtml + "<tr><td>Wohnfläche</td><td>" + str(getLivingArea(immo)) + " m^2</td></tr>"
        popuphtml = popuphtml + "<tr><td>Grundstücksfläche</td><td>" + str(getPropertyArea(immo)) + " m^2</td></tr>"
        popuphtml = popuphtml + "<tr><td>Baujahr</td><td>" + str(getYearOfConstruction(immo)) + "</td></tr>"
        popuphtml = popuphtml + "<tr><td>Adresse</td><td>" + str(getLocationAdress(immo)) + "</td></tr>"
        popuphtml = popuphtml + "</table>"
        popuphtml = popuphtml + "<a href=" + getLink(immo) + ">"+getLink(immo)+"</a>"
        popuphtml = popuphtml + "<a href=" + getLink(immo) + ">"
        popuphtml = popuphtml + "<img src='"+getTitleFilename(immo)+"'></a>"

        lat,lon = getLocation(immo)
        if lat:
            marker = folium.Marker(
                        location=(lat,lon),
                        icon=folium.Icon(icon='home'),
                        tooltip=getTitle(immo),
                        popup=folium.Popup(popuphtml),
                    )
            marker.add_to(map)

    with open('arbeit.json', encoding='utf-8') as f:
        work = json.load(f)
        #print(d)

    for workplace in work["work"]:
        print(workplace)

        lat,lon = getLocation(workplace)
        marker = folium.Marker(
                    location=(lat,lon),
                    icon=folium.Icon(color="orange",icon='flag'),
                    tooltip=workplace["name"]
                )
        marker.add_to(map)

    with open('bahn.json', encoding='utf-8') as f:
        bahn = json.load(f)
        #print(d)

    for station in bahn["stations"]:
        print(station)

        lat,lon = getLocation(station)
        marker = folium.Marker(
                    location=(lat,lon),
                    icon=folium.Icon(color="red",icon='info-sign'),
                    tooltip=station["name"]
                )
        marker.add_to(map)

    return map
