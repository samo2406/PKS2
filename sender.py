import socket
from os import stat
from math import ceil
from binascii import crc32
from struct import pack
from random import randint

class Sender():
    def __init__(self, address):
        import keep_alive
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = address
        
        # Odošleme správu na inicializáciu komunikácie
        self.socket.sendto(str.encode('1'), address)
        
        # Čakáme na inicializačnú odpoveď
        self.opened = self.recieve_init()
        if self.opened:
            # Ak dostaneme inicializačnú odpoveď, spustíme keep alive thread
            self.keep_alive = keep_alive.KA(self)
        else:
            # Ak nedostaneme inicializačnú odpoveď zavrieme socket
            self.socket.close()
        
    def is_open(self) -> bool:
        return self.opened

    def send_file(self, file_path:str, fragment_size:int=1500, error:bool=False) -> bool: 
        # Typ správy - 4 - odosielanie súboru
        self.message_type = '4'    
        file_size = stat(file_path).st_size
        self.fragment_size = fragment_size
        self.number_of_fragments = ceil(file_size / fragment_size)
        self.error = error

        with open(file_path,'rb') as f:
            self.message = f.read()
        
        return self.send_init()

    def send_text(self, message:str, fragment_size:int=1500, error:bool=False) -> bool:
        # Typ správy - 3 - odosielanie textovej správy  
        self.message_type = '3'
        self.message = message
        self.fragment_size = fragment_size                   
        self.number_of_fragments = ceil(len(message) / fragment_size)
        self.error = error
      
        return self.send_init()
       
    def send_init(self) -> bool:
        # Pozastavenie KA
        self.keep_alive.active = False
        # Odoslanie inicializačnej správy
        init_message = self.message_type + str(self.number_of_fragments)
        self.socket.sendto(str.encode(init_message), self.address)

        error_fragment = None
        if self.error:
            error_fragment = randint(0,self.number_of_fragments-1)

        # Odosielanie fragmentov
        for fragment_number in range(self.number_of_fragments):
            if fragment_number == error_fragment:
                self.send_fragment(fragment_number, True)
            else:
                self.send_fragment(fragment_number, False)

        return self.recieve_ack()

    def send_fragment(self, fragment_number:int, insert_error:bool=False):
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

        # Ak máme simulovať chybu prenosu, znížime crc o 1
        if insert_error:
            crc -= 1

        # Pridanie vypočítaného CRC na koniec payloadu
        payload += pack('I', crc)

        # Odoslanie fragmentu
        if insert_error:
            print('Sending packet No. '+ str(fragment_number) + ' [' + str(len(data)) + ' B] - with error')
        else:
            print('Sending packet No. '+ str(fragment_number) + ' [' + str(len(data)) + ' B]')
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
                # Znovu spustenie keep alive po úspešnom prijatí správy
                self.keep_alive.active = True
                return True
        except socket.timeout:
            # Znovu spustenie keep alive po neúspešnom prijatí správy
            self.keep_alive.active = True
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

    def switch_roles(self):
        self.socket.sendto(str.encode('2'), self.address)

        try :
            self.socket.settimeout(5)
            response = str(self.socket.recv(1500).decode())
                  
            if response[:1] == '2':
                # Vrátime port
                return int(response[1:])
            else:
                return -1

        except socket.timeout:
            return -1

    def close(self):
        self.socket.close()
        self.opened = False
        self.keep_alive.stop = True