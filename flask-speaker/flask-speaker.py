# server.py

from flask import Flask, request
from playsound import playsound
import glob,os,random, time

app = Flask(__name__)

#multiple files per score; 
#automatically select file, if file has one of the allowed extensions
#allowed extension list


#delay based on score. Autodarts caller takes different amount of time to say different scores.
#Saying 3 takes less time than saying 26 

def combineCurrentDirWithScoreType(scoreType):
    return os.path.join(os.getcwd(),scoreType)

def getFilesFromFolderWithExtension(folder,extension):
    searchfolder = combineCurrentDirWithScoreType(folder)
    globExtensionString = "*"+ extension 
    searchLocation = os.path.join(searchfolder,globExtensionString)
    files = glob.glob(searchLocation)
    return files, searchfolder

def getRandomSoundFile(folder,extension):
    files,searchfolder = getFilesFromFolderWithExtension(folder,extension)
    if files:
        randomFile = random.sample(files, 1)[0]
        randomFileWithoutFolder = randomFile.replace(searchfolder,"")[1:]
        return randomFile,randomFileWithoutFolder
    return None

def playSoundFile(file):
    if file is None:
        return
    playsound(file)
    return

def getDelayMilliSecondsFromType(typeOfScore):
    files,_ = getFilesFromFolderWithExtension(typeOfScore,"txt")
    if files:
        delayFile = files[0]
        #read from file and store in delay

    return 3


def delaySoundBasedOnType(typeOfScore):
    delayMilliSec = getDelayMilliSecondsFromType(typeOfScore)
    time.sleep(delayMilliSec)

@app.route('/play', methods=['GET'])
def get():
    try:
        typeOfScore = request.args.get("type")
    except:
        typeOfScore = None
    if not typeOfScore:
        return "", 201

    if not os.path.isdir(typeOfScore):
        return "", 201

    fileFullPath,file = getRandomSoundFile(typeOfScore,"wmv")
    print(file)
    print(fileFullPath)

    delaySoundBasedOnType(typeOfScore)

    playSoundFile(fileFullPath)
    #return the status parallel to playing the file
    return file, 201

if __name__ == '__main__':
    app.run("0.0.0.0",debug=True)