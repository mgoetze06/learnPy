from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from pprint import pprint
import wget
import os
import requests
import json
import shutil
import time

downloadImages = True

DRIVER_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"

def saveAllImagesFromDriver(driver):
    print("getting images from driver")

    #gallery-element
    #'imageContainer_0wG-W'
    titles = driver.find_elements(By.CLASS_NAME,'gallery-element')
    filecount = 0
    for title in titles:
        #print(title.get_attribute('outerHTML'))
        print(title.text)
        imgsrc = title.get_attribute('innerHTML')
        imgsrc = imgsrc.replace("<img src=\"","")
        #print(imgsrc)
        imgsrc = imgsrc.split("\"")[0]
        print(imgsrc)

#        dir = "Orte\ID_"+str(immo_ID)
#        filename = str(filecount)+".jpg"
        #saveImageFromUrlToDirectory(imgsrc,filename,dir)
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
            grund = text.split("\n")[1].split(" m")[0].replace(".","")
        if "jahr" in text:
            jahr = text.split("\n")[1]

    return wohnen,grund,jahr

def getInformationenFromImmoscoutURL(url):
    if url is None or url == '':
        return
    options = Options()
    options.headless = True  # Enable headless mode for invisible operation
    options = webdriver.ChromeOptions() 
    options.add_argument("start-maximized")
    driver = uc.Chrome(options=options)
    #driver = webdriver.Chrome(options=options)

    #with open('immo.json', encoding='utf-8') as f:
    #    data = json.load(f)
    #    f.close()


    #immos_count = len(data["immos"])
    #print("Current Length of Immos: ", immos_count)
    #print("Last Immo ID: ", data["immos"][immos_count-1]["id"])
    #print("New Immo ID: ", immos_count)


    driver.get(url)
    time.sleep(5)
    saveAllImagesFromDriver(driver)

if __name__ == "__main__":
    url = ""
    getInformationenFromImmoscoutURL(url)
