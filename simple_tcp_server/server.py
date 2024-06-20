#! /usr/bin/python
# a simple tcp server
import socket,os

def getResponseFromCommand(command):
    resp = ""
    command = command.decode().strip()
    print("server recieved: ",command)
    match command:
        case "R0":
            resp = "R0 A"
    
        case "R1":
            resp = "R1 A"
        
        case "SI":
            resp = "S S       12,0 KG"
    
        case _:
            resp = "AW L"

    
    print("server response: ",resp)
    resp = str.encode(resp)
    return resp

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
sock.bind(('127.0.0.1', 12345))  
sock.listen(5)  
while True:  
    connection,address = sock.accept()  
    buf = connection.recv(1024)  
    print(buf)
    connection.send(getResponseFromCommand(buf))    		
    connection.close()



