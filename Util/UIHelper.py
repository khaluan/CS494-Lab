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


#TODO: Wrap text display