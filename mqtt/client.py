import websocket
import time
import rel
import ssl
import RPi.GPIO as GPIO
import json

#Callback function when receiving a message via websocket 
#===================================================================================================
def on_message(ws, message):
#===================================================================================================
    print(message)

#Callback function when websocket error occurs
#===================================================================================================
def on_error(ws, error):
#===================================================================================================
    if(error.args[0] == 'Connection to remote host was lost.'):
        print("Server closed connection")
    else:
        print(error)

#Callback function when websocket is closed
#===================================================================================================
def on_close(ws, close_status_code, close_msg):
#===================================================================================================
    print("connection closed")

#Callback function when websocket is opened
#===================================================================================================
def on_open(ws):
#===================================================================================================
    print("connection opened")

#Callback function for interupt on GPIO pin
#===================================================================================================
def gpio_callback(pin): 
#=================================================================================================== 
    try:
        time.sleep(0.1)
        res =  GPIO.input(pin)
        
        if res == 0:
            ws.send(json.dumps({'data': 'off', 'pin': pin, 'client': clientName}))
        elif res == 1:
            ws.send(json.dumps({'data': 'on', 'pin': pin, 'client': clientName}))
    except:
        pass

#main method - connection the websocket, setting interupts on all GPIO pins
#===================================================================================================
if __name__ == "__main__":
    websocket.enableTrace(False)
    
    #collecting credentials on command line
    username = input("Enter Your Username: ")
    password = input("Enter Your Password: ")
    global clientName 
    clientName = input("Enter unique Client Name: ")
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    #setting interupts
    try:
        for i in range(2,28,1):
            GPIO.setup(i, GPIO.IN)  
            GPIO.add_event_detect(i, GPIO.BOTH, callback=gpio_callback, bouncetime=150)
    except:
        pass

    global ws
    #opening websocket
    ws = websocket.WebSocketApp(f"wss://localhost:8080/wss/user={username}&pass={password}",
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)

    ws.run_forever(dispatcher=rel,sslopt={"cert_reqs": ssl.CERT_NONE})  # Set dispatcher to automatic reconnection
    rel.signal(2, rel.abort)  # Keyboard Interrupt
    rel.dispatch()

