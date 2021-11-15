import socket
import time

import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Config.config import *
import sys

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    time.sleep(int(sys.argv[1]))
    s.sendall(b'Hello, world')
    data = s.recv(1024)

print('Received', repr(data))