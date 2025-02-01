from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from pprint import pprint
import wget
import os

downloadImages = True


# Set the path to the Chromedriver
DRIVER_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"

# Initialize the Chrome driver
options = Options()
options.headless = True  # Enable headless mode for invisible operation

# Initialize Chrome with the specified options
driver = webdriver.Chrome(options=options)

url = ''


driver.get(url)

#html = driver.page_source
#print(html)
#all_links = driver.find_elements(By.TAG_NAME,'img')
#print(all_links)




main = driver.find_elements(By.ID,'viewad-main-info')
print(main)
print(str(main[0].text.split("\n")[0].replace(":","")) + ".txt")
f = open(str(main[0].text.split("\n")[0].replace(":","")) + ".txt", "a")
for title in main:
    f.write(title.text)
    print(title.text)

config = driver.find_elements(By.ID,'viewad-price')
for title in config:
    f.write("\n")
    f.write("PREIS: ")
    f.write(title.text)
    f.write("\n")

config = driver.find_elements(By.ID,'viewad-configuration')
for title in config:
    f.write(title.text)
    #print(title.text)

location = driver.find_elements(By.ID,'viewad-map')
for title in location:
    f.write(title.text)
    #print(title.text)


description = driver.find_elements(By.ID,'viewad-description')
for title in description:
    f.write(title.text)
    #print(title.text)
f.close()

titles = driver.find_elements(By.ID,'viewad-image')
#print(titles.get_attribute('outerHTML'))
if downloadImages:
    for title in titles:
        print(title.get_attribute('outerHTML'))

        imgsrc = title.get_attribute('outerHTML')
        imgsrc = imgsrc.replace("<img src=\"","")
        print(imgsrc)
        imgsrc = imgsrc.split("\"")[0]
        print(imgsrc)

        try:
            wget.download(imgsrc)
        except:
            pass


    files = os.listdir(".")
    for path in files:
        if not os.path.splitext(path)[1]:
            if not os.path.isdir(path):
                print(path)
                os.rename(path, path+'.jpg')