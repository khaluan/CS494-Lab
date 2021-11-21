import socket
import threading

import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Config.config import *

def handle_connection(conn, add):
    try:
        print(f"Waiting from {add}")
        data = conn.recv(1024)
        print(f"Data received: {data}")
        conn.sendall(b"Ack")
        conn.close()
    except:
        pass

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()

    thread_list = []
    for i in range(10):
        conn, add = s.accept()
        thread_id = threading.Thread(target=handle_connection, args=(conn, add))
        thread_list.append(thread_id)
        thread_id.start()
    
    for _ in range(10):
        print("Waitinggggggggggg..........")
    for thread in thread_list:
        thread.join()
    
    s.close()


if __name__ == '__main__':
    main()