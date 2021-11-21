import socket
import threading

import os, sys
import time

from pygame.constants import USEREVENT
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Model.player import Player
from Config.constant import *
from Config.config import *

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
time.sleep(1)
data = s.recv(1024)
print(data)
