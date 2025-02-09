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
from kleinanzeigen import saveImageFromUrlToDirectory,updateImmos,write_json

downloadImages = True

DRIVER_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"

def saveAllImagesFromDriver(driver,files,immo_ID):
    print("getting images from driver")
    filecount = 0
    for file in files:
        dir = "Orte\ID_"+str(immo_ID)
        filename = str(filecount)+".jpg"
        saveImageFromUrlToDirectory(file,filename,dir)
        filecount += 1
    files = os.listdir(".")
    for path in files:
        if not os.path.splitext(path)[1]:
            if not os.path.isdir(path):
                print(path)
                newfilename = str(filecount)+".jpg"
                newdirAndFilename = os.path.join(dir,newfilename)
                shutil.move(path, newdirAndFilename)
                filecount += 1

def getFirstImagesUrlFromGallery(driver,img_list):
    titles = driver.find_elements(By.CLASS_NAME,'imageContainer_0wG-W')
    #titles = driver.find_elements(By.CLASS_NAME,'gallery-element')
    for title in titles:
        #print(title.text)
        imgsrc = title.get_attribute('innerHTML')
        imgsrc = imgsrc.replace("<img src=\"","")
        #print(imgsrc)
        imgsrc = imgsrc.split("\"")[0]
        img_list.append(imgsrc)
        print(imgsrc)
    return img_list

def getAllThumbnailImageUrlFromGallery(driver,thumbnail_list):
    titles = driver.find_elements(By.CLASS_NAME,'thumbnail_8uYUI ')
    #titles = driver.find_elements(By.CLASS_NAME,'gallery-element')
    for title in titles:
        img_tag = title.get_attribute('innerHTML')
        #print(img_tag)
        startsrc = img_tag.index('src=') + 5
        #print(startsrc)
        endsrc = img_tag.index('">',startsrc,len(img_tag))
        #print(endsrc)
        
        imgsrc = img_tag[startsrc:endsrc]
        imgsrc = imgsrc.split("\" ")[0]
        #print(imgsrc)
        thumbnail_list.append(imgsrc)

    return thumbnail_list


def acceptCookies(driver):
    #x = WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, "sc-eeDRCY.fnyekb")))
    #accept_cookies.click()
    #driver.execute_script("arguments[0].click();", accept_cookies)
    #button = driver.find_element(By.XPATH, '//button[text()="Alle akzeptieren"]')
    #if button:
    #    button.click()
    #    #'sc-dcJsrY.ezjNCe'

    print("Please Click Cookies in Webdriver")

def clickTitleImageToGetImageGallery(driver):
    driver.find_element(By.CLASS_NAME,'button.is24-fullscreen-gallery-trigger').click()

def getOrigSizePath(src):
    src = src.split("/ORIG/")[1]
    #print(src)
    return src

def getRealImagesFromThumbnails(thumbnail_list,high_quality_path):
    image_paths = []
    for thumbnail in thumbnail_list:
        thumbnail = thumbnail.split("/ORIG/")[0]
        print(thumbnail)
        image_paths.append(thumbnail)
        thumbnail = thumbnail + "/ORIG/" + high_quality_path
        #print(thumbnail)
    return image_paths

def getTitleImageUrl(driver,img_list):
    titles = driver.find_elements(By.CLASS_NAME,'gallery-element.is24-fullscreen-gallery-trigger')
    #titles = driver.find_elements(By.CLASS_NAME,'gallery-element')
    for title in titles:
        img_tag = title.get_attribute('outerHTML')
        #print(img_tag)
        startsrc = img_tag.index('src=') + 5
        endsrc = img_tag.index('">')
        imgsrc = img_tag[startsrc:endsrc]
        #print(imgsrc)
        img_list.append(imgsrc)
        return img_list

def getPriceFromDriver(driver):
    config = driver.find_element(By.CLASS_NAME,'is24-preis-value')
    price = config.text
    price = price.split("€")[0].strip()
    price = price.replace(".","")
    return price

def getImmoTitleFromDriver(driver):
    config = driver.find_element(By.ID,'expose-title')
    return config.text

def getDescriptionFromDriver(driver):
    description = driver.find_elements(By.CLASS_NAME,'is24qa-objektbeschreibung.text-content.short-text')
    text = ""
    for title in description:
        text += title.text

    text = text.replace("\n",";")
    try:
        description = driver.find_elements(By.CLASS_NAME,'is24qa-lage.text-content.full-text')
        for title in description:
            text += title.text

        text = text.replace("\n",";")
    except:
        pass

    return text

def getAdDateFromDriver(driver):
    config = driver.find_element(By.ID,'viewad-extra-info')
    text = config.text.split("\n")[0]
    return text

def getSizesAndYearFromDriver(driver):

    wohnen,grund,jahr = None,None,None
    details = driver.find_elements(By.CLASS_NAME,'is24qa-wohnflaeche-ca.grid-item.three-fifths')
    wohnen = details[0].text.split(" ")[0]
    details = driver.find_elements(By.CLASS_NAME,'is24qa-grundstueck-ca.grid-item.three-fifths')
    grund = details[0].text.split(" ")[0]
    try:
        details = driver.find_elements(By.CLASS_NAME,'is24qa-baujahr.grid-item.three-fifths')
        jahr = details[0].text
    except:
        pass

    return wohnen,grund,jahr

def getInformationenFromImmoscoutURL(url):
    if url is None or url == '':
        return
    options = Options()
    options.headless = True  # Enable headless mode for invisible operation
    options = webdriver.ChromeOptions() 
    options.add_argument("start-maximized")
    driver = uc.Chrome(options=options)
    driver = webdriver.Chrome(options=options)

    with open('immo.json', encoding='utf-8') as f:
        data = json.load(f)
        f.close()


    immos_count = len(data["immos"])
    print("Current Length of Immos: ", immos_count)
    print("Last Immo ID: ", data["immos"][immos_count-1]["id"])
    print("New Immo ID: ", immos_count)


    driver.get(url)

    img_list = []
    acceptCookies(driver)
    input("cookies akzeptiert?")
    print("getting first images from gallery")
    img_list = getTitleImageUrl(driver,[])
    print("image list from gallery:")
    print(img_list)
    if len(img_list) > 0:
        newtitleimage = "title_"+str(immos_count)+".jpg"
        saveImageFromUrlToDirectory(img_list[0],newtitleimage,"static\images")
    livingarea,propertyarea,year = getSizesAndYearFromDriver(driver)
    description = getDescriptionFromDriver(driver)
    title = getImmoTitleFromDriver(driver)
    price = getPriceFromDriver(driver)
    time.sleep(3)
    print("clicking button to access gallery")

    clickTitleImageToGetImageGallery(driver)
    time.sleep(3)
    print("clicking done")

    thumbnail_list = []
    print("geting all thumbnails image Url FromGallery ")
    thumbnail_list = getAllThumbnailImageUrlFromGallery(driver,thumbnail_list)
    print("thumbnails done")
    #high_quality_path = getOrigSizePath(img_list[0])

    print("getting real images")
    image_paths = getRealImagesFromThumbnails(thumbnail_list,'')
    print("saving images")
    saveAllImagesFromDriver(driver,image_paths,immos_count)

        # New element to add
    new_immo = {
        "id": immos_count,
        "title": title,
        "price": price,
        "city": "",
        "address": "",
        "lat": None,
        "lon": None,
        "ad_date": None,
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
    url = ''
    getInformationenFromImmoscoutURL(url)
