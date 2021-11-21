import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Model.player import Player
from Config.constant import *
from Config.config import *

def get_location(pos, margin = 0):
    x, y = pos
    H, W = WINDOW_SIZE
    return (int(H * x - margin), int(W * y - margin))

def center(screen, surface, y):
    rect = None
    if y > 1:
        rect = surface.get_rect(center=(WINDOW_SIZE[0] / 2, y))
    else:
        rect = surface.get_rect(center=(WINDOW_SIZE[0] / 2, WINDOW_SIZE[1] * y))
    screen.blit(surface, rect)


#TODO: Wrap text display