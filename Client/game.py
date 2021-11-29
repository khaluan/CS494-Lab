import pygame
import socket
import os, sys
import re
import logging
import json
import threading, time

from pygame.constants import K_ESCAPE, K_KP_ENTER, K_RETURN, KEYDOWN, MOUSEBUTTONDOWN, USEREVENT
from pygame.version import ver
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
        self.players = []
         
        #################### DEBUG SESSION ###########################
        # self.remain_players = 3
        # self.timeout = 10
        
        # self.current_player_name = 'b3luga'
        # self.player.name = 'b3luga'
        
        # self.remain_questions = 2

    """
        Event listeners
    """
    def listen_to_response(self):
        data = self.socket.recv(BUFFER_SIZE)
        self.logger.warning(f'Async receiver: {data}')
        data_dict = json.loads(data)

        if 'verdict' in data_dict.keys():
            # Response for question answering
            self.handle_question_verdict(data_dict)
        elif 'name' in data_dict.keys():
            self.handle_new_player()
        elif 'players' in data_dict.keys():
            self.handle_config_response(data_dict)
        else:
            # TODO: Other kinds of response here (a new player come to waiting room)
            pass

    def handle_config_response(self, data_dict):
        event = pygame.event.Event(SERVER_RESPONSE, message=data_dict)
        pygame.event.post(event)          
    
    def handle_question_verdict(self, data_dict):
        event = pygame.event.Event(SERVER_RESPONSE, message=data_dict['verdict'])
        pygame.event.post(event)

    def setup_listener(self):
        thread = threading.Thread(target=self.listen_to_response)
        thread.start()

    """
        Menu for the game:
    """

    def menu(self):
        self.screen.fill(WHITE)
 
        logo = pygame.image.load(LOGO_PATH)
        center(self.screen, logo, 0.4)

        font = pygame.font.SysFont(FONT, OPTION_SIZE)
        
        start_option = font.render('START', True, BLACK)
        start_layout = start_option.get_rect(topleft=(WINDOW_SIZE[0] / 6, WINDOW_SIZE[1] * 0.85))

        exit_option = font.render("EXIT", True, BLACK)
        exit_layout = start_option.get_rect(topleft=(WINDOW_SIZE[0] * (1/6 + 1/2), WINDOW_SIZE[1] * 0.85))

        self.screen.blit(start_option, start_layout)
        self.screen.blit(exit_option, exit_layout)

        while True:
            events = pygame.event.get()
            for event in events:
                if event.type ==  MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    if start_layout.collidepoint(pos):
                        return 1
                    elif exit_layout.collidepoint(pos):
                        return 0
            pygame.display.update()

    """
        Main loop of the game
    """
    # def run(self):
    #     running = True
    #     while running:
    #         status = self.initialize_connection()
    #         if status: 
                
    #             self.register_name()
    #             self.waiting_screen()
    #             self.start_game()
    #             self.display_result()
    #             self.cleanup()
    #         else:
    #             self.cleanup()
    #             time.sleep(10)

    def run(self):
        while True:
            opt = self.menu()
            if opt == 0:
                return
            elif opt == 1:
                status = self.initialize_connection()
                if status: 
                    self.register_name()
                    self.waiting_screen()
                    self.start_game()
                    self.display_result()
                    self.cleanup()
                else:
                    self.cleanup()
                    time.sleep(10)
                    
    """
        Connecting stage
    """
    def initialize_connection(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((HOST, PORT))  
       
        data = {"type": REQUEST_SLOT, "contents": REQUEST_SLOT}
        data_str = json.dumps(data).encode()
        self.socket.sendall(data_str)
        
        data_str = self.socket.recv(BUFFER_SIZE)
        self.logger.warning(f"Receiving from server {data_str}")
        data = json.loads(data_str)
        game_status = data['contents']
        self.logger.warning(f"Return status {game_status == OK}")
        if game_status == FULL:
            return False
        elif game_status == OK:
            return True

    """"
        Resgister screen
    """
    def check_name_format(self, player_name):
        regex = re.compile(NAME_REGEX)
        return regex.match(player_name)
    
    def validate_name(self, player_name):
        data = {"type": REGISTER_NAME, "name": player_name}
        data_str = json.dumps(data)
        self.socket.sendall(data_str.encode())
        self.logger.warning(f"Sending name to server: {data_str}")

        response_str = self.socket.recv(BUFFER_SIZE)
        self.logger.warning(f'Checking name, received {response_str}')
        response = json.loads(response_str)
        if response['status'] == OK:
            self.player.order = response['order']
            return OK
        elif response['status'] == NO:
            return NO
        elif response['status'] == FULL:
            return FULL

        self.logger.warning("Checking name: Unknown status")

    def register_name(self):
        background = pygame.image.load(LOGO_PATH)
        myfont = pygame.font.SysFont('Comic Sans MS', 25)
        name_title = myfont.render("Input your name", True, BLACK)
        is_full = False
        def activate():
            pygame.event.post(pygame.event.Event(USEREVENT))
            
        self.logger.warning("Start register name")

        while True:

            input_manager = pygame_textinput.TextInputManager(validator= lambda input: re.compile(NAME_REGEX).match(input))
            name_input = pygame_textinput.TextInputVisualizer(manager = input_manager)
            
            input = True

            while input:
                self.screen.fill(BACKGROUND)

                events = pygame.event.get()
                for event in events:
                    if event.type == KEYDOWN and event.key == K_RETURN:
                        input = False
                        break
                    elif event.type == USEREVENT:
                        is_full = False

                name_input.update(events)
                self.screen.blit(background, (0, 0))
                center(self.screen, name_title, 0.82)
                center(self.screen, name_input.surface, 0.89)
                if is_full:
                    announcement = myfont.render('Sorry the game is full', True, BLACK) 
                    center(self.screen, announcement, 0.95)
                    timer = threading.Timer(1.5, activate)
                    timer.start()
                pygame.display.update()

            player_name = name_input.value
            if self.validate_name(player_name) == OK:
                self.player.name = player_name
                break
            else:
                is_full = True
        self.logger.warning(f"Register complete, player name: {self.player.name}, order: {self.player.order}")

    def waiting_screen(self):
        self.logger.warning("Entering waiting screen")
        font = pygame.font.SysFont(FONT, QUESTION_SIZE)
        waiting_title = font.render("Waiting for other players", True, BLACK)
        waiting = True
 
        player_img = pygame.image.load(PLAYER_PATH)
        #TODO: Setup async an async listener to listen to other player to join and display
        self.setup_listener()

        self.screen.fill(WHITE)
        while waiting:
            center(self.screen, waiting_title, 0.1)

            events = pygame.event.get()
            for event in events:
                if event.type == SERVER_RESPONSE:
                    self.logger.warning(f"Receive message from server {event.message}")
                    data = event.message
                    if 'players' in data.keys(): # config response
                        self.setup_config(data)
                        waiting = False
                    else: # New player added response
                        self.remain_players += 1
                        self.display_remaining_players(player_img)

            pygame.display.update()


    """
        Gameplay screen
    """
    def setup_config(self, config):
        self.timeout = config['timeout']
        self.remain_questions = config['questions']

        players = config['players']
        self.remain_players = len(players)
        for player in players:
            self.players.append(Player(player['name'], player['order']))
        
        response = {"type": RESPONSE_CONFIG, 'content':"ack"}
        response = json.dumps(response).encode()
        self.socket.sendall(response)

    def recv_config(self):
        config_str = self.socket.recv(BUFFER_SIZE)
        self.logger.warning(f"Receive config: {config_str}")
        config = json.loads(config_str)

        return config

    def get_question(self):
        # question = Question("Just a short question: 1 + 1 = ?" , ["A. 1", "B. 2", "C. 3", "D. 4"])
        response_str = self.socket.recv(BUFFER_SIZE)
        self.logger.warning(f"Get question: {response_str}")
        response = json.loads(response_str)

        self.current_player_name = response['playername']
        self.remain_questions = response['remain-question']

        question_json = response['questions']
        question = Question(question_json['question'], question_json['choices'])
        return question

    def display_question(self, question):
        player_img = pygame.image.load(PLAYER_PATH)

        question_font = pygame.font.SysFont(FONT, QUESTION_SIZE)
        question_title = question_font.render(question.question, True, WHITE)
        question_layout = question_title.get_rect(center=(WINDOW_SIZE[0] / 2, 100))

        choice_font = pygame.font.SysFont(FONT, CHOICE_SIZE)
        choices_text = [choice_font.render(choice, True, WHITE) for choice in question.choices]        
        choice_location = [(OFFSET, 0.3), (0.5 + OFFSET, 0.3), (OFFSET, 0.4), (0.5 + OFFSET, 0.4)]
        choices_layout = [layout.get_rect(topleft=get_location(pos, MARGIN), width=WINDOW_SIZE[0] * 0.4, height=layout.get_rect().size[0])
                        for layout, pos in zip(choices_text, choice_location)]
        
        pygame.time.set_timer(pygame.USEREVENT, 1000)
        remain_time = self.timeout + 1
        timer_font = pygame.font.SysFont(FONT, TIMER_SIZE)

        skip_turn_font = pygame.font.SysFont(FONT, CHOICE_SIZE)
        skip_turn_text = skip_turn_font.render("SKIP", True, BLACK)
        skip_turn_layout = skip_turn_text.get_rect(topleft=get_location((0.075, 0.6)))
        
        if self.current_player_name != self.player.name:
            self.socket.sendall(b'ack')
            self.setup_listener()

        waiting = True
        verdict = ""

        while waiting:
            self.screen.fill(BACKGROUND)

            events = pygame.event.get()

            pygame.draw.rect(self.screen, BLUE, question_layout)
            self.screen.blit(question_title, question_layout)

            for text, layout, pos in zip(choices_text, choices_layout, choice_location):
                pygame.draw.rect(self.screen, BLUE, layout)
                self.screen.blit(text, get_location(pos))
            
            timer_layout = timer_font.render(str(remain_time), True, BLACK)
            self.screen.blit(timer_layout, get_location((0.8, 0.6)))
            self.display_remaining_players(player_img)

            if self.current_player_name == self.player.name and self.player.skip_turn:
                self.screen.blit(skip_turn_text, get_location((0.075, 0.6)))        
            
            for event in events:
                if event.type == KEYDOWN and event.key == K_RETURN:
                    # Emergency escape
                    waiting = False
                    self.logger.warning("Escaping")
                    break

                elif event.type == MOUSEBUTTONDOWN and self.current_player_name == self.player.name:
                    # Mouse click for player in turn
                    pos = pygame.mouse.get_pos()
                    if skip_turn_layout.collidepoint(pos) and self.player.skip_turn:
                        self.logger.warning("Handling skip")
                        verdict = self.send_answer(question, "Skip")

                        self.player.skip_turn = 0
                        waiting = False
                    else:
                        for i, layout in enumerate(choices_layout):
                            if layout.collidepoint(pos):
                                self.logger.warning(f"Accept answer {chr(0x41 + i)}")
                                verdict = self.send_answer(question, question.choices[i])

                                waiting = False
                                break

                elif event.type == USEREVENT:
                    # Clock ticking after 1 second
                    remain_time -= 1
                    if remain_time == 0:
                        waiting = False

                elif event.type == SERVER_RESPONSE:
                    verdict = event.message
                    waiting = False

            pygame.display.update()
        
        self.socket.sendall(b'ack')
        self.handle_verdict(verdict)
        self.display_remaining_players(player_img)
        pygame.display.update()
        time.sleep(1.5)

    def send_answer(self, question, answer):
        data = {"answer": answer, "question": {"question": question.question, "choices": question.choices}}
        data_str = json.dumps(data)
        self.logger.warning(f"Sending answer: {data_str}")
        self.socket.sendall(data_str.encode())
        
        verdict_str = self.socket.recv(BUFFER_SIZE)
        self.logger.warning(f'Receive verdict: {verdict_str}')
        verdict = json.loads(verdict_str)
        return verdict['verdict']

    def handle_verdict(self, verdict):
        font = pygame.font.SysFont(FONT, 25)
        self.logger.warning(f"Handling verdict of {verdict}")
        verdict_text = ''
        if verdict == OK:
            verdict_text = font.render(f'Player {self.current_player_name} correct', True, BLACK)
        elif verdict == NO:
            verdict_text = font.render(f'Player {self.current_player_name} eliminated', True, BLACK)
        elif verdict == SKIP:
            verdict_text = font.render(f'Player {self.current_player_name} skip turn', True, BLACK)
            self.remain_players -= 1
        center(self.screen, verdict_text, 0.1)

    def display_remaining_players(self, image):
        left = (WINDOW_SIZE[0] - self.remain_players * 100) // 2
        for i in range(self.remain_players):
            self.screen.blit(image, (left + i * 100, 500 * 0.7))

    def start_game(self):
        while self.remain_questions > 1:
            question = self.get_question()
            self.display_question(question)

    """"
        This is for result screen
    """

    def display_result(self):
        winner_str = self.socket.recv(BUFFER_SIZE)
        self.logger.warning(f"Recv final result: {winner_str}")

        winner = json.loads(winner_str)
        winner_player = winner['winner']

        self.screen.fill(WHITE)

        firework_img = pygame.image.load(FIREWORK_PATH)
        player_img = pygame.image.load(PLAYER_PATH)

        font = pygame.font.SysFont(FONT, CHOICE_SIZE)
        winner_name = font.render(winner_player, True, BLACK)

        displaying = True
        while displaying:
            
            self.screen.blit(firework_img, get_location((0, 0)))
            self.screen.blit(player_img, get_location((0.4, 0.6)))
            self.screen.blit(winner_name, get_location((0.43, 0.5)))
            events = pygame.event.get()
            for event in events:
                if event.type == KEYDOWN and event.key == K_RETURN:
                    displaying = False
                    break

            pygame.display.update()

    """
        Helping function
    """
    def in_turn(self):
        return self.player.name == self.current_player_name

    def cleanup(self):
        self.socket.close() 

    def __del__(self):
        pygame.display.quit()
        pygame.quit()
  
        self.socket.close()

        exit(0)

