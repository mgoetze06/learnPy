import glob
import shutil
import ctypes  # An included library with Python install.   

remote_folder = "//<user>/Documents/My Games/FarmingSimulator2025/mods"
local_folder = "<user>/Documents/My Games/FarmingSimulator2025/mods"

filetype = "*.zip"


remote_file_list = glob.glob(remote_folder+"//"+filetype)
local_file_list = glob.glob(local_folder+"//"+filetype)

#print(remote_file_list)
#print(local_file_list)
print("Remotefiles: ",len(remote_file_list))
for index,file in enumerate(remote_file_list):
    remote_file_list[index] = file.replace(remote_folder,"").replace("\\","")
    #print(file)
print("localfiles", len(local_file_list))
for index,file in enumerate(local_file_list):
    local_file_list[index] = file.replace(local_folder,"").replace("\\","")
    #print(file)

print("getting differences")
syncedFiles = 0
for index,file in enumerate(remote_file_list):
    if file not in local_file_list:
        print("need to sync file: ",file)
        src = remote_folder + "//" + file
        dst = local_folder + "//" + file
        shutil.copyfile(src, dst)
        syncedFiles += 1


gesamttext = "Gesamtanzahl Mods " + str(len(remote_file_list))
neuetext = "Neue Mods " + str(syncedFiles)

print(gesamttext)
print(neuetext)

ctypes.windll.user32.MessageBoxW(0, neuetext, gesamttext, 1)
