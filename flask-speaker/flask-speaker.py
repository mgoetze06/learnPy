# server.py

from flask import Flask, request
from playsound import playsound


app = Flask(__name__)

@app.route('/play', methods=['GET'])
def get():

    # Path to the sound file
    sound_file = '26.wmv'

    # Play the sound file
    playsound(sound_file)

    return "", 201

if __name__ == '__main__':
    app.run("0.0.0.0",debug=True)