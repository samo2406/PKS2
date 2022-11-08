import socket
import threading
import binascii
import struct

def sender(ip_adress, port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(str.encode('1'), (ip_adress, int(port)))
        response = s.recvfrom(1500)

        while True:
            message = input("Type a message to send: ")
            s.sendto(str.encode(message), (ip_adress, int(port)))


def reciever(port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", int(port)))
        response = s.recvfrom(1500)
        s.sendto(str.encode("1"), response[1])
        print("Connection successful (" + str(response[1]) + ")")
        while True:
            response = s.recvfrom(1500)
            print("Received message:", response[0])

while True:
    i = input("[1] Sender\n[2] Reciever\n[0] Exit\n")
    if i == '0':
        break
    elif i == '1':
        #ip = input("IP adress: ")
        #port = input("Port: ")
        #sender(ip, port)
        sender('127.0.0.1', '123')
    elif i == '2':
        port = input("Port: ")
        reciever(port)