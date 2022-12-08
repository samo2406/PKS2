from math import ceil
from os import stat, path
from binascii import crc32
from threading import Thread
from time import sleep
from struct import pack, unpack
import socket

KA = False
ADDRESS = ("127.0.0.1", 123)
PORT = 123

def KA_thread(s:socket.socket):
    while True:
        if not KA:
            return

        s.sendto(str.encode('7'), ADDRESS)
        try:
            s.settimeout(10)
            response = str(s.recv(1500).decode())

            if response != '7':
                print("Keep alive - wrong response")
        except socket.timeout:
            if KA :
                print("Keep alive - no response")
                s.close()
            return
    
        for i in range(10):
            if KA:
                sleep(1)

def start_KA(s:socket.socket, interval):
    global KA
    thread = Thread(target=KA_thread, args=[s])
    thread.daemon = True
    thread.start()
    KA = True
    return thread

def send_fragment(s:socket.socket, message, fragment_number:int, fragment_size:int, message_type):
    # Rozdelenie správy na fragmenty
    data = message[fragment_number*fragment_size:(fragment_number+1)*fragment_size]

    # Struct pack podla typu správy
    if message_type == "1":
        payload = pack("cHH", str.encode('3'), fragment_size, fragment_number) + (data.encode())
    elif message_type == "2":
        payload = pack("cHH", str.encode('4'), fragment_size, fragment_number) + (data)
    
    # Vypočítanie CRC pomocou binascii
    crc = crc32(payload)
    # Pridanie vypočítaného CRC na koniec payloadu
    payload += pack("I", crc)

    # Odoslanie fragmentu
    print("Sending fragment number "+ str(fragment_number) + ", with fragment size " + str(len(data)) + "B")
    s.sendto(payload, ADDRESS)

def sender():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        global ADDRESS
        s.sendto(str.encode('1'), ADDRESS)
        response = str(s.recv(1500).decode())
        if response != '1':
            print("Didn't recieve initial response")
            s.close()
            return

        thread = Thread(target=KA_thread, args=[s])
        thread.daemon = True
        thread.start()
        global KA
        KA = True

        while True:
            i = input("[1] Send a text message\n[2] Send a file\n[3] Switch roles\n[0] Exit\n")
            if i == '0':
                break
            if i == '3':
                s.sendto(str.encode('8'), ADDRESS)
                response, address = s.recvfrom(1500)
                if str(response.decode()) != '8':
                    print("Switching roles - wrong response, can't switch roles")
                ADDRESS = address
                return reciever()
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
                with open(file_path,'rb') as f:
                    message = f.read()
                # Typ správy - 4 - odosielanie súboru
                msg_init = '4' + str(number_of_fragments)

            # Odoslanie inicializačnej správy
            s.sendto(str.encode(msg_init), ADDRESS)

            for fragment_number in range(number_of_fragments):
                send_fragment(s, message, fragment_number, fragment_size, i)

            try :
                response = str(s.recv(1500).decode())
                    
                if response[:1] == '6':
                    failed_fragments = response[1:].split(",")
                    for f in failed_fragments:
                        print("Sending failed framgents :")
                        send_fragment(s, message, f, fragment_size, i)
            
                if response[:1] == '5':
                    print("Successful transfer")
            except socket.timeout:
                print("Didn't recieve file transfer response")
                continue


def reciever():
    messages = []
    failed_fragments  = ''
    recieved_message = ''

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as r:
        r.bind(("", PORT))
        response, address = r.recvfrom(1500)
        global ADDRESS
        ADDRESS = address
        r.sendto(str.encode("1"), ADDRESS)
        print("Connection successful (" + str(ADDRESS) + ")")
        while True:
            try:
                # Keep alive casovac
                r.settimeout(20)
                initial = str(r.recv(1500).decode())        

                # Keep alive odpoved
                if initial[:1] == '7' and KA:                   
                    r.sendto(str.encode('7'), ADDRESS)
                    print("KEEP ALIVE - response")
                if initial[:1] == '8':
                    r.sendto(str.encode('8'), ADDRESS)
                    print("Switching roles")
                    return sender()                  

                if initial[:1] == '3' or initial[:1] == '4':
                    number_of_fragments = initial[1:]
                    print("Recieving " + number_of_fragments + " fragments :")

                    # Prijímanie správy :
                    messages = [""] * int(number_of_fragments)
                    failed_fragments = ""
                    recieved_message = ""
                    for i in range(int(number_of_fragments)):
                        message = r.recv(65498)
                        # Struct unpack prijatej spravy
                        payload = unpack("cHH", message[:6])    # [:6] pretože nás zaujíma prvých 5 byte-ov hlavičky
                        recieved_crc = unpack("I", message[-4:])[0]     # [-4:] pretože CRC sú posledné 4 byte hlavičky
                        data = message[6:-4]    # [6:-4] zostávajúce byte sú práve prenášané dáta 
                        fragment_size = payload[1]    # 1. blok v hlavičke
                        fragment_number = payload[2]    # 2. blok v hlavičke
                        # Správu naspäť "poskladám" a vypočítam z nej CRC
                        packed_payload = pack("cHH", payload[0], payload[1], payload[2]) + data
                        calculated_crc = crc32(packed_payload)

                        if calculated_crc == recieved_crc:
                            print("Recieved fragment number "+ str(fragment_number), ", with fragment size ", str(fragment_size), "B")
                            if initial[:1] == '3':
                                messages[fragment_number] = data.decode()
                            else:
                                messages[fragment_number] = data
                        else:
                            # Ak sa CRC nerovnajú, zapíšem nesprávny paket
                            print("Recieved wrong packet - ", fragment_number)
                            failed_fragments += str(fragment_number) + ","

                    # Pokial je zoznam nesprávnych paketov prázdny, odošlem odpoveď o úspešnej komunikácií
                    if not failed_fragments:
                        for m in messages:
                            recieved_message += m
                        if initial[:1] == '3':                           
                            print("Recieved message :\n", recieved_message)
                        elif initial[:1] == '4':                                    
                            file_path = path.dirname(path.realpath(__file__)) + "\\recieved_file.txt"
                            with open(file_path,'wb') as f:
                                f.write(recieved_message)
                                f.close()
                            print("Recieved file :\n", file_path)  
                        r.sendto(str.encode("5"), ADDRESS)
                        return
                    else:
                        failed_fragments = failed_fragments[:-1]    # Odstránenie poslednej "trailing" čiarky
                        # Odoslanie odpovede o neúspešnej komunikácií
                        r.sendto(pack("B", str.encode("6")) + failed_fragments.encode(), ADDRESS)

            except socket.timeout:
                print("KEEP ALIVE - timeout - socket closed")
                r.close()
                return

while True:
    i = input("[1] Sender\n[2] Reciever\n[0] Exit\n")
    if i == '0':
        break
    elif i == '1':
        # ip = input("IP adress: ")
        # port = input("Port: ")
        # ADDRESS = (ip, port)
        # sender()
        sender()
    elif i == '2':
        PORT = int(input("Port: "))
        reciever()