import socket
import threading
import pygame

import os, sys

from pygame.constants import USEREVENT
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Model.player import Player
from Config.constant import *
from Config.config import *

def waiting(conn):
    data = conn.recv(1024)
    print(data)
    event = pygame.event.Event(USEREVENT)
    pygame.event.post(event)


pygame.init()
pygame.display.set_caption("Hello")
pygame.display.set_mode((100, 100))
pygame.display.flip()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
data = s.recv(1024)
print(data)

thread = threading.Thread(target=waiting, args = (s,))
thread.start()
running = True
while running:
    
    events = pygame.event.get()

    for event in events:
        if event.type == USEREVENT:
            running = False
            break
        else:
            print(event)
