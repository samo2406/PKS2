from sender import Sender
from reciever import Reciever

def main_menu():
    return input("[1] Sender\n[2] Reciever\n[0] Exit\n")

def sender_init():
    ip = input("IP adress: ")
    port = int(input("Port: "))
    address = (ip, port)
    return Sender(address)

def sender_menu():
    return input("[1] Send a text message\n[2] Send a file\n[3] Switch roles\n[0] Exit\n")

def reciever_init():
    port = int(input("Port: "))
    return Reciever(port)

while True:
    sender = None
    reciever = None
    
    i = main_menu()
    # Exit
    if i == '0':
        break
    
    # Sender
    elif i == '1':
        sender = sender_init()
        if not sender.is_open():
            print("Didn't recieve initial response")
            continue

    # Reciever
    elif i == '2':
        reciever = reciever_init()
        if not reciever.is_initialized():
            print("Didn't recieve initial message")
            continue
    
    if i == '1' or i == '2':
        while True:
            if sender and sender.is_open():
                i = sender_menu()
                if i == '0':
                    break
                elif i == '3':
                    port = sender.switch_roles()
                    if port == -1:
                        print("Didn't recieve switch response")
                    else:
                        sender.close()
                        sender = None
                        reciever = Reciever(port)
                        print("----------------------------")
                elif i == '1':  # Sending a message
                    message = input("Enter a message : ")
                    fragment_size = int(input("Enter the fragment size : "))
                    if (fragment_size <= 0 or fragment_size > 65498):
                        print("Wrong fragment size, using 1500 B")
                        fragment_size = 1500
                    error = input("Simulate error ? [y/n]\n")
                    if error == "y" or error == "Y" or error == "1":
                        error = True
                    else:
                        error = False
                    sender.send_text(message, fragment_size, error)
                elif i == '2':  # Sending a file
                    file_path = input("Enter a filename : ")
                    fragment_size = int(input("Enter the fragment size : "))
                    if (fragment_size <= 0 or fragment_size > 65498):
                        print("Wrong fragment size, using 1500 B")
                        fragment_size = 1500
                    error = input("Simulate error ? [y/n]\n")
                    if error == "y" or error == "Y" or error == "1":
                        error = True
                    else:
                        error = False
                    sender.send_file(file_path, fragment_size, error)
                
            elif reciever and reciever.is_initialized():
                port = reciever.recieving_loop()
                if port == -1:
                    reciever.close()
                    reciever = None
                    break
                elif port:
                    reciever.close()
                    sender = Sender(reciever.address)
                    reciever = None
                    print("----------------------------")
        
            else:
                break
