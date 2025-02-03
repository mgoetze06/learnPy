from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from pprint import pprint
import wget
import os
import requests
import json
import shutil

downloadImages = True
DRIVER_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"


def write_json(new_data, filename='immo.json'):
    # Print the updated JSON data
    print(json.dumps(new_data, indent=4))

    # Optionally, save the updated JSON to a file
    with open(filename, "w") as file:
        json.dump(new_data, file, indent=4)


def updateImmos(newimmo,data):
    data["immos"].append(newimmo)
    return data

def saveAllImagesFromDriver(driver,immo_ID):
    titles = driver.find_elements(By.ID,'viewad-image')
    filecount = 0
    for title in titles:
        #print(title.get_attribute('outerHTML'))

        imgsrc = title.get_attribute('outerHTML')
        imgsrc = imgsrc.replace("<img src=\"","")
        #print(imgsrc)
        imgsrc = imgsrc.split("\"")[0]
        print(imgsrc)

        dir = "Orte\ID_"+str(immo_ID)
        filename = str(filecount)+".jpg"
        saveImageFromUrlToDirectory(imgsrc,filename,dir)
        wget.download(imgsrc)
    files = os.listdir(".")
    for path in files:
        if not os.path.splitext(path)[1]:
            if not os.path.isdir(path):
                print(path)
                newfilename = str(filecount)+".jpg"
                newdirAndFilename = os.path.join(dir,newfilename)
                shutil.move(path, newdirAndFilename)
                filecount += 1
    
def saveImageFromUrlToDirectory(url,filename,directory=None):
    if directory:
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Full path to save the image
        full_path = os.path.join(directory, filename)
    else:
        full_path = filename
    # Send a GET request to the image URL
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Save the image with the new name
        with open(full_path, 'wb') as file:
            file.write(response.content)
        print(f"Image downloaded and saved as '{full_path}'.")
    else:
        print(f"Failed to download the image. Status code: {response.status_code}")


def getTitleImageUrlFromDriver(driver):
    description = driver.find_elements(By.CLASS_NAME,'galleryimage-element')
    title = description[0]

    all_meta = title.find_elements(By.TAG_NAME,'meta')
    for meta in all_meta:

        text = meta.get_attribute('outerHTML')
        if "contentUrl" in text:
            url = text.split('content="')[1].split('">')[0]
            return url

def getPriceFromDriver(driver):
    config = driver.find_element(By.ID,'viewad-price')
    price = config.text
    price = price.split("€")[0].strip()
    price = price.replace(".","")
    return price

def getImmoTitleFromDriver(driver):
    config = driver.find_element(By.ID,'viewad-title')
    return config.text

def getDescriptionFromDriver(driver):
    description = driver.find_elements(By.ID,'viewad-description')
    text = ""
    for title in description:
        text += title.text

    text = text.replace("\n",";")
    return text

def getAdDateFromDriver(driver):
    config = driver.find_element(By.ID,'viewad-extra-info')
    text = config.text.split("\n")[0]
    return text

def getSizesAndYearFromDriver(driver):
    details = driver.find_elements(By.CLASS_NAME,'addetailslist--detail')

    wohnen,grund,jahr = None,None,None

    for detail in details:
        #print(detail.text)
        text = detail.text
        if "Wohnfläche" in text:
            wohnen = text.split("\n")[1].split(" m")[0]
        if "Grund" in text:
            grund = text.split("\n")[1].split(" m")[0]
        if "jahr" in text:
            jahr = text.split("\n")[1]

    return wohnen,grund,jahr

def getInformationenFromKleinanzeigenURL(url):
    if url is None or url == '':
        return
    options = Options()
    options.headless = True  # Enable headless mode for invisible operation

    driver = webdriver.Chrome(options=options)

    #url = 'https://www.kleinanzeigen.de/s-anzeige/renovierungsbeduerftig/2776025846-208-11843'


    with open('immo.json', encoding='utf-8') as f:
        data = json.load(f)
        f.close()


    immos_count = len(data["immos"])
    print("Current Length of Immos: ", immos_count)
    print("Last Immo ID: ", data["immos"][immos_count-1]["id"])
    print("New Immo ID: ", immos_count)


    driver.get(url)
    price = getPriceFromDriver(driver)
    title = getImmoTitleFromDriver(driver)
    description = getDescriptionFromDriver(driver)
    imageUrl = getTitleImageUrlFromDriver(driver)
    adDate = getAdDateFromDriver(driver)
    livingarea,propertyarea,year = getSizesAndYearFromDriver(driver)
    print(imageUrl)
    newtitleimage = "title_"+str(immos_count)+".jpg"
    saveImageFromUrlToDirectory(imageUrl,newtitleimage,"static\images")


    saveAllImagesFromDriver(driver,immos_count)

    # New element to add
    new_immo = {
        "id": immos_count,
        "title": title,
        "price": price,
        "city": "",
        "address": "",
        "lat": None,
        "lon": None,
        "ad_date": adDate,
        "description": description,
        "constructionyear": year,
        "livingarea": livingarea,
        "propertyarea": propertyarea,
        "details": "-",
        "link": url
    }

    data = updateImmos(newimmo=new_immo,data=data)
    write_json(data)


if __name__ == "__main__":
    getInformationenFromKleinanzeigenURL()
