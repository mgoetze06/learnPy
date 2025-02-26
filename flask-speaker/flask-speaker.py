# server.py

from flask import Flask, request
from playsound import playsound
import glob,os,random, time, threading

app = Flask(__name__)

#multiple files per score; 
#automatically select file, if file has one of the allowed extensions
#allowed extension list


#delay based on score. Autodarts caller takes different amount of time to say different scores.
#Saying 3 takes less time than saying 26 

VALID_EXTENSIONS = ["wmv","mp3","m4a"]


def delayAndPlaySound(file,delayMS):
    delaySound(delayMS)
    playSoundFile(file)

    return

def combineCurrentDirWithScoreType(scoreType):
    return os.path.join(os.getcwd(),scoreType)

def getFilesFromFolderWithExtension(folder,extension):
    searchfolder = combineCurrentDirWithScoreType(folder)
    globExtensionString = "*"+ extension 
    searchLocation = os.path.join(searchfolder,globExtensionString)
    files = glob.glob(searchLocation)
    return files, searchfolder

def getRandomSoundFile(folder):
    allFiles = []
    for extension in VALID_EXTENSIONS:
        files,searchfolder = getFilesFromFolderWithExtension(folder,extension)
        if files:
            allFiles += files

    if len(allFiles)>0:
        randomFile = random.sample(allFiles, 1)[0]
        randomFileWithoutFolder = randomFile.replace(searchfolder,"")[1:]
        return randomFile,randomFileWithoutFolder
    return None

def playSoundFile(file):
    if file is None:
        return
    print("playing sound file: ", file)
    playsound(file)
    return

def getDelayMilliSecondsFromType(typeOfScore):
    files,_ = getFilesFromFolderWithExtension(typeOfScore,"txt")
    print("files", files)
    delay = 1
    if files:
        delayFile = files[0]
        #read from file and store in delay
        with open(delayFile) as f:
            s = f.read()
            delay = int(s)
            f.close()
    return delay


def delaySound(delaySeconds):
    print(f"total sleeping time {delaySeconds}s")
    for i in range(delaySeconds):
        print(f"sleeping {i+1}/{delaySeconds} seconds")
        time.sleep(1)

@app.route('/play', methods=['GET'])
def get():
    try:
        typeOfScore = request.args.get("type")
    except:
        typeOfScore = None
    if not typeOfScore:
        return "", 401

    if not os.path.isdir(typeOfScore):
        return "", 401

    fileFullPath,file = getRandomSoundFile(typeOfScore)
    print(file)
    print(fileFullPath)

    delayMilliSec = getDelayMilliSecondsFromType(typeOfScore)

    x = threading.Thread(target=delayAndPlaySound, args=(fileFullPath,delayMilliSec))
    x.start()
    #return the status parallel to playing the file
    return file, 201

if __name__ == '__main__':
    app.run("0.0.0.0",debug=True)