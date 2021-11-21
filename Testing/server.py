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


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()

conn, ad = s.accept()
conn.sendall(b'Hello')
conn.sendall(b'Bye')