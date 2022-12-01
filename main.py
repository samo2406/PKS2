from math import ceil
from os import stat, path
from binascii import crc32
from threading import Thread
from time import sleep
import socket

KA = False

def KA_thread(sender, adress):
    while True:
        if not KA:
            return

        sender.sendto(str.encode('7'), adress)
        try:
            sender.settimeout(10)
            response = str(sender.recv(1500).decode())

            if response != '7':
                print("Keep alive - wrong response")
        except socket.timeout:
            if KA :
                print("Keep alive - no response")
                sender.close()
            return
    
        for i in range(10):
            if KA:
                sleep(1)

def start_KA(vysielac, adresa, interval):
    global KA
    thread = Thread(target=KA_thread, args=(vysielac, adresa, interval))
    thread.daemon = True
    thread.start()
    KA = True
    return thread

def send_fragment(message, fragment_number, fragment_size):
    # Rozdelenie správy na fragmenty
    data = message[fragment_number*fragment_size:(fragment_number+1)*fragment_size]
    
    # Struct pack alternative
    # payload =

    # Vypočítanie CRC pomocou binascii
    crc = crc32(payload)
    # payload += crc
    print("Sending fragment number "+ str(fragment_number) + ", with fragment size " + str(len(data)) + "B")
    s.sendto(payload, (ip_adress, int(port)))


def sender(ip_adress, port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(str.encode('1'), (ip_adress, int(port)))
        response = str(sender.recv(1500).decode())
        if response != '1':
            print("Didn't recieve initial response")
            s.close()
            return

        thread = Thread(target=KA_thread, args=(s, (ip_adress, int(port))))
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
                file_path = input("Enter file name : ")
            fragment_size = int(input("Fragment size : "))
            if fragment_size <= 0 or fragment_size >= 65498:
                print("Invalid frament size, using 1500")
                fragment_size = 1500
            
            if i == '1':
                number_of_fragments = ceil(len(message) / fragment_size)
                # Typ správy - 3 - odosielanie textovej správy
                msg_init = '3' + str(number_of_fragments)
            if i == '2':
                file_size = stat(file_path).st_size
                number_of_fragments = ceil(file_size / fragment_size)
                with open(file_path,'r') as f:
                    message = f.read()
                # Typ správy - 4 - odosielanie súboru
                msg_init = '4' + str(number_of_fragments)

            # Odoslanie inicializačnej správy
            s.sendto(str.encode(msg_init), (ip_adress, int(port)))

            for fragment_number in range(number_of_fragments):
                send_fragment(message, fragment_number, fragment_size)

            try :
                response = str(s.recv(1500).decode())
                    
                if response[:1] == '6':
                    failed_fragments = response[1:].split(",")
                    for f in failed_fragments:
                        print("Sending failed framgents :")
                        send_fragment(message, f, fragment_size)
            
                if response[:1] == '5':
                    print("Successful transfer")
            except socket.timeout:
                print("Didn't recieve file transfer response")
                continue


def reciever(port):
    messages = []
    failed_fragments  = ''
    recieved_message = ''

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as r:
        r.bind(("127.0.0.1", int(port)))
        response, address = s.recvfrom(1500)
        r.sendto(str.encode("1"), response[1])
        print("Connection successful (" + str(response[1]) + ")")
        while True:
            try:
                # Keep alive casovac
                r.settimeout(20)
                response = str(s.recv(1500).decode())        

                # Keep alive odpoved
                if response[:1] == '7' and KA:                   
                    r.sendto(str.encode('7'), address)
                    print("KEEP ALIVE - posielam odpoveď")

                if response[:1] == '3' or response[:1] == '4':
                    number_of_fragments = response[1:]
                    print("Recieving " + number_of_fragments + " fragments :")

                    # Prijímanie správy :
                    del messages, failed_fragments, recieved_message
                    for i in range(number_of_fragments):
                        data = r.recv(65498)
                        # Unpack alternative
                    

                        if calculated_crc == recieved_crc:
                            print("Recieved fragment number "+ str(fragment_number), ", with fragment size ", str(fragment_size), "B")
                            if response[:1] == '3':
                                messages[fragment_number] = message.decode()
                            else:
                                messages[fragment_number] = message
                        else:
                            print("Recieved wrong packet - ", fragment_number)
                            failed_fragments += str(fragment_number) + ","

                    if not failed_fragments:
                        for m in messages:
                            recieved_message += m
                        if response[:1] == '3':                           
                            print("Recieved message :\n", recieved_message)
                        elif response[:1] == '4':                                    
                            file_path = path.dirname(path.realpath(__file__)) + "\\recieved_file.txt"
                            with open(file_path,'w') as f:
                                f.write(recieved_message)
                                f.close()
                            print("Recieved file :\n", file_path)  
                        r.sendto(str.encode("5"), address)
                        return
                    else:
                        # Prerobit struct pack
                        r.sendto(struct.pack("c", str.encode("6")) + chybne_spravy[:-1].encode(), adresa)

            except socket.timeout:
                print("KEEP ALIVE - vypršal čas, spojenie bolo zrušené")
                r.close()
                return

while True:
    i = input("[1] Sender\n[2] Reciever\n[0] Exit\n")
    if i == '0':
        break
    elif i == '1':
        # ip = input("IP adress: ")
        # port = input("Port: ")
        # sender(ip, port)
        sender('127.0.0.1', '123')
    elif i == '2':
        port = input("Port: ")
        reciever(port)