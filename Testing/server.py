import socket
import threading
import time

import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Model.player import Player
from Config.constant import *
from Config.config import *

def handle_connection(conn, add):
    conn.sendall(b"This is a question")
    time.sleep(10)
    conn.sendall(b'I wake up')

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()

conn_list = []
thread_list = []

for i in range(MAX_PLAYERS):
    conn, add = s.accept()
    thread_id = threading.Thread(target=handle_connection, args=(conn, add))
    thread_list.append(thread_id)
    thread_id.start()

for thread in thread_list:
    thread.join()