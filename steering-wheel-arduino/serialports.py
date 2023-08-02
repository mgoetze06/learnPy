import serial.tools.list_ports
 
print(serial.tools.list_ports.comports())
ports = list(serial.tools.list_ports.comports())
port_count= 0
for p in ports:
    port_count += 1
    print (p)

if port_count > 1:
    port = input("multiple Ports detected, please enter port:")
else:
    if port_count == 0:
        print("no COM ports detected, exiting")
        exit
    else:
        print("only one port detected, selecting this one:")
        port = ports[0]

print(port)
#print(dir(port))
#print(port.interface)
print(port.device)
#print(port.hwid)
#print(port.location)
