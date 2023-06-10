# importing the module.
import xml.etree.ElementTree as ET

# parsing directly.

print("looking for vehicles.xml")

tree = ET.parse('vehicles.xml')
root = tree.getroot()
# parsing using the string.

# printing the root.
print(root)

all_vehicles = root.findall("vehicle")
print("current damage: ")
for v in all_vehicles:
    wear = v.find("wearable")
    if wear:
        print(wear.get("damage"))
        wear.set("damage", '0.00')

print("damage reset to zero")
tree.write('vehicles.xml')
print('updated file vehicles.xml')