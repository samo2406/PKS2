import socket
from binascii import crc32
from struct import pack, unpack
from os import path
from typing import Any

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
                # Inicializačná odpoveď
                self.socket.sendto(str.encode("1"), self.address)
                return True
            else:
                return False
        except socket.timeout:
            return False

    def recieving_loop(self):
        while True:
            try:
                # Keep alive casovac
                self.socket.settimeout(20)
                message = str(self.socket.recv(1500).decode())
                message_type = message[:1]

                if message_type == '7':
                    # KEEP ALIVE odpoveď
                    self.socket.sendto(str.encode('7'), self.address)

                elif message_type == '2':
                    # Výmena rolí
                    port = self.address[1]
                    self.socket.sendto(str.encode('2'+str(port)), self.address)
                    return port

                elif message_type == '3' or message_type == '4':
                    number_of_fragments = message[1:]
                    self.messages = [""] * int(number_of_fragments)
                    
                    if self.recieve_message(number_of_fragments, message_type):                    
                        recieved_message = ""
                        recieved_file = bytearray()
                        
                        if message_type == '3':
                            for m in self.messages:
                                recieved_message += m
                            print("Recieved message :\n" + recieved_message)
                        
                        elif message_type == '4':
                            for m in self.messages:
                                recieved_file += m    
                            file_path = input("Enter a file path for the recieved file : ")                            
                            with open(file_path,'wb') as f:
                                f.write(recieved_file)
                                f.close()
                            print("Recieved file :\n", file_path)  
            
            except socket.timeout:
                print("KEEP ALIVE - timeout - socket closed")
                self.socket.close()
                return -1

    def recieve_message(self, number_of_fragments, message_type) -> bool:      
        failed_fragments = ""
        number_of_failed_fragments = 0
        self.socket.settimeout(5)       
        try:
            for _ in range(int(number_of_fragments)):
                message = self.socket.recv(65498)
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
                    print("Recieved packet No. "+ str(fragment_number), " [" +  str(len(data)) + " B]")
                    if message_type == '3':
                        # decode() využívam len v prípade textovej správy
                        self.messages[fragment_number] = data.decode()
                    else:
                        self.messages[fragment_number] = data
                else:
                    # Ak sa CRC nerovnajú, zapíšem nesprávny paket
                    number_of_failed_fragments += 1
                    print("Recieved wrong packet - ", fragment_number)
                    failed_fragments += str(fragment_number) + ","
        
        except socket.timeout:
            print("KEEP ALIVE - timeout - socket closed")
            self.socket.close()
            return False

        # Pokial je zoznam nesprávnych paketov prázdny, odošlem odpoveď o úspešnej komunikácií
        if not failed_fragments:
            self.socket.sendto(str.encode('5'), self.address)
            return True
        else:
            failed_fragments = failed_fragments[:-1]    # Odstránenie poslednej "trailing" čiarky
            # Odoslanie odpovede o neúspešnej komunikácií
            print("Asking for packets No.", failed_fragments)
            self.socket.sendto(pack("c", str.encode('6')) + failed_fragments.encode(), self.address)
            return self.recieve_message(number_of_failed_fragments, message_type)

    def close(self):
        self.initialized = False
        self.socket.close()