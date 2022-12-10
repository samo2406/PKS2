from math import ceil
from os import stat, path
from binascii import crc32
from threading import Thread
from time import sleep
from struct import pack, unpack
import socket

KA = False
PORT = 123 

class KA():
    def __init__(self, socket:socket.socket):
        self.thread = Thread(target=self.KA_thread, args=[socket])
        self.thread.daemon = True
        self.thread.start()
        self.active = True
        self.socket = socket

    def KA_thread(self):
        while True:
            if not self.active:
                return

            self.socket.sendto(str.encode('7'), ADDRESS)
            try:
                self.socket.settimeout(10)
                response = str(self.socket.recv(1500).decode())

                if response != '7':
                    print("Keep alive - wrong response")
            except socket.timeout:
                if KA :
                    print("Keep alive - no response")
                    self.socket.close()
                return
        
            for _ in range(5):
                if self.active:
                    sleep(1)

class Sender():
    def __init__(self, address):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = address
        
        # Odošleme správu na inicializáciu komunikácie
        self.socket.sendto(str.encode('1'), address)
        
        # Čakáme na inicializačnú odpoveď
        self.opened = self.recieve_init()
        if self.opened:
            # Ak dostaneme inicializačnú odpoveď, spustíme keep alive thread
            self.keep_alive = KA(self.socket)
        else:
            # Ak nedostaneme inicializačnú odpoveď zavrieme socket
            self.socket.close()
        
    def is_open(self) -> bool:
        return self.opened

    def send_file(self, file_path:str, fragment_size:int=1500) -> bool: 
        # Typ správy - 4 - odosielanie súboru
        self.message_type = '4'    
        file_size = stat(file_path).st_size
        self.fragment_size = fragment_size
        self.number_of_fragments = ceil(file_size / fragment_size)

        with open(file_path,'rb') as f:
            self.message = f.read()
        
        return self.send_init()

    def send_text(self, message:str, fragment_size:int=1500) -> bool:
        # Typ správy - 3 - odosielanie textovej správy  
        self.message_type = '3'
        self.message = message
        self.fragment_size = fragment_size                   
        self.number_of_fragments = ceil(len(message) / fragment_size)
      
        return self.send_init()
       
    def send_init(self) -> bool:
        # Odoslanie inicializačnej správy
        init_message = self.message_type + str(self.number_of_fragments)
        self.socket.sendto(str.encode(init_message), self.address)

        # Odosielanie fragmentov
        for fragment_number in range(self.number_of_fragments):
            self.send_fragment(fragment_number)

        return self.recieve_ack()

    def send_fragment(self, fragment_number:int):
        # Rozdelenie správy na fragmenty
        data = self.message[fragment_number*self.fragment_size:(fragment_number+1)*self.fragment_size]

        # Struct pack podla typu správy
        payload = pack('cHH', str.encode(self.message_type), self.fragment_size, fragment_number)
        if self.message_type == '3':
            payload += data.encode()
        elif self.message_type == '4':
            payload += data
        
        # Vypočítanie CRC pomocou binascii
        crc = crc32(payload)
        # Pridanie vypočítaného CRC na koniec payloadu
        payload += pack('I', crc)

        # Odoslanie fragmentu
        print('Sending fragment No. '+ str(fragment_number) + ' [' + str(len(data)) + 'B]')
        self.socket.sendto(payload, self.address)

    def recieve_ack(self) -> bool:
        try :
            self.socket.settimeout(5)
            response = str(self.socket.recv(1500).decode())
                    
            if response[:1] == '6':
                failed_fragments = response[1:].split(',')
                for f in failed_fragments:
                    print('Sending failed fragments :')
                    self.send_fragment(int(f))
                return self.recieve_ack()
        
            if response[:1] == '5':
                return True
        except socket.timeout:
            return False

    def recieve_init(self) -> bool:
        try :
            self.socket.settimeout(5)
            response = str(self.socket.recv(1500).decode())
                  
            if response == '1':
                return True
            else:
                return False

        except socket.timeout:
            return False

class Reciever():
    def __init__(self, port:int):
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", self.port))

        self.initialized = self.recieve_init()

    def is_initialized(self) -> bool:
        return self.initialized

    def recieve_init(self) -> bool:
        try :
            self.socket.settimeout(60)
            message, address = self.socket.recvfrom(1500)
            if message.decode() == "1":
                self.address = address
                return True
            else:
                return False
        except socket.timeout:
            return False


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
        # port = int(input("Port: "))
        # address = (ip, port)
        # sender = Sender(address)
        sender:Sender = Sender(("127.0.0.1", 123))
        if not sender.is_open():
            print("Didn't recieve initial response")

    elif i == '2':
        PORT = int(input("Port: "))
        reciever()