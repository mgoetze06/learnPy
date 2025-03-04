from selenium import webdriver
from selenium.webdriver.firefox.options import Options 
options = Options()
options.binary_location = r'/usr/bin/firefox'
#from selenium.webdriver.firefox.service import Service
#service = Service('/home/pi/.local/bin/geckodriver')
driver = webdriver.Firefox(options=options)
#driver = webdriver.Firefox()