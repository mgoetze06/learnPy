# server.py

from flask import Flask, request

app = Flask(__name__)

@app.route('/update', methods=['GET'])
def get():
    print("payload get")
    print(request.data)

    return "", 201

@app.route('/update', methods=['POST'])
def post():
    print("payload post")
    print(request.data)
    return "", 201

if __name__ == '__main__':
    app.run("0.0.0.0",debug=True)