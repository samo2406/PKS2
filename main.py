import socket
import threading
import binascii
import struct
import time

KA = False

def KA_thread(sender, adress):
    while True:
        if not KA:
            return

        sender.sendto(str.encode('7'), adress)
        try:
            sender.settimeout(10)
            response = str(sender.recv(1500).decode())

            if response == '7':
                global posledna_sprava
                posledna_sprava = time.time()
        except socket.timeout:
            if KA :
                print("Keep alive - no response")
                sender.close()
            return
    
        for i in range(10):
            if KA:
                time.sleep(1)

def start_KA(vysielac, adresa, interval):
    global KA
    thread = threading.Thread(target=KA_thread, args=(vysielac, adresa, interval))
    thread.daemon = True
    thread.start()
    KA = True
    return thread

def sender(ip_adress, port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(str.encode('1'), (ip_adress, int(port)))
        response = str(sender.recv(1500).decode())
        if response != '1':
            print("Didn't recieve initial response")
            s.close()
            return

        thread = threading.Thread(target=KA_thread, args=(s, (ip_adress, int(port))))
        thread.daemon = True
        thread.start()
        global KA
        KA = True

        while True:
            i = input("[1] Send a text message\n[2] Send a file\n[0] Exit\n")
            if i == '0':
                break
            elif i == '1':
                message = input("Enter a message : ")
            elif i == '2':
                file = input("Enter file name : ")
            fragment = int(input("Zadaj maximálnu veľkosť fragmentu : "))


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