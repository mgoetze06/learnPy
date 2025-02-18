# server.py

from flask import Flask, request
from playsound import playsound
import glob,os,random

app = Flask(__name__)

#multiple files per score; 
#automatically select file, if file has one of the allowed extensions
#allowed extension list


#delay based on score. Autodarts caller takes different amount of time to say different scores.
#Saying 3 takes less time than saying 26 



def getRandomSoundFile(folder,extension):

    searchfolder = os.path.join(os.getcwd(),folder)
    globExtensionString = "*"+ extension 
    searchLocation = os.path.join(searchfolder,globExtensionString)
    files = glob.glob(searchLocation)
    if files:
        return random.sample(files, 1)[0]
    return None

def playSoundFile(file):
    if file is None:
        return
    playsound(file)
    return

@app.route('/play', methods=['GET'])
def get():
    print(request)
    print(request.data)
    file = getRandomSoundFile("","wmv")
    print(file)
    return "", 201

if __name__ == '__main__':
    app.run("0.0.0.0",debug=True)