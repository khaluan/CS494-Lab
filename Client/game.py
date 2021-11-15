import pygame
import socket
import os, sys
import re
import logging

from pygame.constants import K_ESCAPE, K_KP_ENTER, K_RETURN, KEYDOWN
import pygame_textinput

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Model.player import Player
from Config.constant import *
from Config.config import *
from Util.UIHelper import *

logging.basicConfig(format=LOGGING_FORMAT)

class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Who is the millionaire")
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.screen.fill(WHITE)
        pygame.display.flip()

        self.player = Player()
        self.logger = logging.getLogger('client')

    def run(self):

        running = True
        while running:
            self.initialze_connection()
            self.register_name()
            self.start_game()
            self.display_result()

    def initialize_connection(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((HOST, PORT))

    def check_name_format(self, player_name):
        regex = re.compile(NAME_REGEX)
        return regex.match(player_name)
    
    def validate_name(self, player_name):
        """"
            TODO: This function send player_name to server for validation
        """
        return True

    def register_name(self):
        background = pygame.image.load(LOGO_PATH)
        myfont = pygame.font.SysFont('Comic Sans MS', 30)
        name_title = myfont.render("Input your name", False, BLACK)
        
        while True:
            input_manager = pygame_textinput.TextInputManager(validator= lambda input: re.compile(NAME_REGEX).match(input))
            name_input = pygame_textinput.TextInputVisualizer(manager = input_manager)
            
            input = True
            while input:
                self.screen.fill(BACKGROUND)

                events = pygame.event.get()

                name_input.update(events)
                self.screen.blit(background, (0, 0))
                self.screen.blit(name_title, get_location(0.3, 0.8))
                self.screen.blit(name_input.surface, get_location(0.4, 0.9))
                pygame.display.update()
                for event in events:
                    if event.type == KEYDOWN and event.key == K_RETURN:
                        input = False
                    elif event.type == KEYDOWN and event.key == K_ESCAPE:
                        pygame.display.quit()
                        pygame.quit()
                        exit(0)

            player_name = name_input.value
            if self.validate_name(player_name):
                self.player.name = player_name
                break


    def start_game(self):
        pass

    def display_result(self):
        pass

    def notify_exit(self):
        pass

    def __del__(self):
        self.notify_exit()
        
        # self.socket.close()


g = Game()
g.register_name()