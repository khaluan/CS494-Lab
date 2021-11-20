import pygame
import socket
import os, sys
import re
import logging
import json
import threading

from pygame.constants import K_ESCAPE, K_KP_ENTER, K_RETURN, KEYDOWN, MOUSEBUTTONDOWN, USEREVENT
import pygame_textinput

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Model.question import Question
from Model.player import Player
from Config.constant import *
from Config.config import *
from Util.UIHelper import *

logging.basicConfig(format=CLIENT_FORMAT)

class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption('Who is the millionaire')
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.screen.fill(WHITE)
        pygame.display.flip()

        self.player = Player()
        self.logger = logging.getLogger('client')
        self.async_listener = []
        # TODO: REMOVE
        self.remain_players = 3
        self.timeout = 10
        self.current_player_name = 'b3luga'
        self.player.name = 'b3luga'
        self.remain_questions = 2

    """
        Event listeners
    """
    def listen_to_response(self):
        data = self.socket.recv(1024)
        data_dict = json.loads(data)

        if 'verdict' in data_dict.keys():
            # Response for question answering
            event = pygame.event.Event(SERVER_RESPONSE, message=data_dict['verdict'])
            pygame.event.post(event)
        else:
            # TODO: Other kinds of response here
            pass

    def setup_listener(self):
        thread = threading.Thread(target=self.listen_to_response)
        thread.start()

    """
        Main loop of the game
    """
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

    """"
        Resgister screen
    """
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
                self.screen.blit(name_title, get_location((0.3, 0.8)))
                self.screen.blit(name_input.surface, get_location((0.4, 0.9)))
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

    """
        Gameplay screen
    """
    def setup_config(self):
        # TODO: read config from server
        config = self.recv_config()

        self.current_order = config['order']
        self.timeout = config['timeout']
        self.remain_questions = config['questions']
        self.remain_players = config['remaining']

    def get_question(self):
        # TODO: get question
        question = Question("Just a short question: 1 + 1 = ?" , ["A. 1", "B. 2", "C. 3", "D. 4"])
        return question

    def display_question(self, question):
        player_img = pygame.image.load(PLAYER_PATH)

        question_font = pygame.font.SysFont(FONT, QUESTION_SIZE)
        question_title = question_font.render(question.question, False, WHITE)
        question_layout = question_title.get_rect(center=(WINDOW_SIZE[0] / 2, 100))

        choice_font = pygame.font.SysFont(FONT, CHOICE_SIZE)
        choices_text = [choice_font.render(choice, False, WHITE) for choice in question.choices]        
        choice_location = [(OFFSET, 0.3), (0.5 + OFFSET, 0.3), (OFFSET, 0.4), (0.5 + OFFSET, 0.4)]
        choices_layout = [layout.get_rect(topleft=get_location(pos, MARGIN), width=WINDOW_SIZE[0] * 0.4, height=layout.get_rect().size[0])
                        for layout, pos in zip(choices_text, choice_location)]
        
        pygame.time.set_timer(pygame.USEREVENT, 1000)
        remain_time = self.timeout + 1
        timer_font = pygame.font.SysFont(FONT, TIMER_SIZE)

        skip_turn_font = pygame.font.SysFont(FONT, CHOICE_SIZE)
        skip_turn_text = skip_turn_font.render("SKIP", False, BLACK)
        skip_turn_layout = skip_turn_text.get_rect(topleft=get_location((0.075, 0.6)))
        
        self.setup_listener()

        waiting = True
        while waiting:
            self.screen.fill(BACKGROUND)

            events = pygame.event.get()

            pygame.draw.rect(self.screen, BLUE, question_layout)
            self.screen.blit(question_title, question_layout)

            for text, layout, pos in zip(choices_text, choices_layout, choice_location):
                pygame.draw.rect(self.screen, BLUE, layout)
                self.screen.blit(text, get_location(pos))
            
            timer_layout = timer_font.render(str(remain_time), False, BLACK)
            self.screen.blit(timer_layout, get_location((0.8, 0.6)))
            self.display_remaining_players(player_img)
            self.screen.blit(skip_turn_text, get_location((0.075, 0.6)))        
            
            for event in events:
                if event.type == KEYDOWN and event.key == K_RETURN:
                    waiting = False
                    self.logger.warning("Escaping")
                    break

                elif event.type == MOUSEBUTTONDOWN and self.current_player_name == self.player.name:
                    pos = pygame.mouse.get_pos()
                    self.logger.warning(f"Click on {pos}")
                    if skip_turn_layout.collidepoint(pos):
                        self.logger.warning("Handling skip")
                        waiting = False
                    else:
                        for i, layout in enumerate(choices_layout):
                            if layout.collidepoint(pos):
                                self.logger.warning(f"Accept answer {chr(0x41 + i)}")
                                waiting = False

                elif event.type == USEREVENT:                    
                    remain_time -= 1
                    if remain_time == 0:
                        waiting = False

                elif event.type == SERVER_RESPONSE:
                    verdict = event.message
                    # TODO: Something with the verdict

            pygame.display.update()

        self.logger.warning("Kaboom")
            
    def display_remaining_players(self, image):
        left = (WINDOW_SIZE[0] - self.remain_players * 100) // 2
        for i in range(self.remain_players):
            self.screen.blit(image, (left + i * 100, 500 * 0.7))

    def start_game(self):
        # self.setup_config()
        while self.remain_questions:
            question = self.get_question()
            self.display_question(question)
            self.setup_config()

    """"
        This is for result screen
    """

    def display_result(self):
        pass

    def notify_exit(self):
        pass

    def __del__(self):
        self.notify_exit() 
        # self.socket.close()

game = Game()
game.start_game()