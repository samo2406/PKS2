import sender
import socket
from threading import Thread
from time import sleep

class KA():
    def __init__(self, sender:sender.Sender):
        self.sender = sender
        self.address = sender.address
        self.active = True
        self.stop = False
        self.thread = Thread(target=self.KA_thread)
        self.thread.daemon = True
        self.thread.start()


    def KA_thread(self):
        while True:
            # Ak ho chceme zastaviť, opustíme nekonečný while loop
            if self.stop:
                return
            # Správy odosielame len keď je aktívny
            elif self.active:
                self.sender.socket.sendto(str.encode('7'), self.address)
                try:
                    self.sender.socket.settimeout(20)
                    response = str(self.sender.socket.recv(1500).decode())

                    if response != '7':
                        print("Keep alive - wrong response")
                except socket.timeout:
                    if KA :
                        print("Keep alive - no response")
                        self.sender.close()
                    return
                except ConnectionResetError:
                    print("Connection closed by the host")
                    self.sender.close()
                    return
            
                for _ in range(5):
                    if self.active:
                        sleep(1)