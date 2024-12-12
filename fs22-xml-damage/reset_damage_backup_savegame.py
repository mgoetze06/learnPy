# importing the module.
import xml.etree.ElementTree as ET
import os
import datetime
import shutil
import numpy as np


savegamePath = "C:\\Users\\Maurice\\Documents\\My Games\\FarmingSimulator2025\\savegame1"
backupPath = "D:\\backups"

# parsing directly.
print("looking for vehicles.xml")


now = datetime.datetime.now()

print(now)
backupZipFilename = now.strftime("%Y%m%d_%H%M%S")
backupZipFilename = backupZipFilename + "_savegame1"
backupPath = os.path.join(backupPath,backupZipFilename)
shutil.make_archive(backupPath, 'zip', savegamePath)


vehiclePath = os.path.join(savegamePath,'vehicles.xml')
tree = ET.parse(vehiclePath)
root = tree.getroot()
# parsing using the string.

# printing the root.
print(root)

all_vehicles = root.findall("vehicle")
print("Vehicle Count: ",len(all_vehicles))

damages = []

for v in all_vehicles:
    wear = v.find("wearable")
    if wear:
        #print(wear.get("damage"))
        damages.append(float(wear.get("damage")))
        wear.set("damage", '0.00')

print("damage reset to zero")
tree.write(vehiclePath)
print('updated file vehicles.xml')

#print(damages)
print('max damage: ',np.max(damages))
print('min damage: ',np.min(damages))
print('mean damage: ',np.mean(damages))