import socket
import threading
import json
import logging
import time
import random

import os
import sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Config.config import *
from Config.constant import *

class Player:
    def __init__(self, conn: socket.socket, add, name='', order=-1):
        self.conn = conn
        self.add = add
        self.name = name
        self.order = order


class Server:
    def __init__(self, num_player: int, num_questions: int, host: str, port: str) -> None:
        # Initialize game's parameters
        self.num_player = num_player
        self.num_questions = num_questions

        # Prepare list of players
        self.players: list[Player] = []
        self.players_lock: threading.Lock = threading.Lock()

        # Prepare list of questions
        self.questions: list[dict] = []
        self.questions_lock: threading.Lock = threading.Lock()

        # Innitialize host, port, and list of threads for connections of the game
        self.host = host
        self.port = port

        # Initialize connection variable
        # Each thread will control one connection from one player
        self.threads: list[threading.Thread] = []
        self.threads_lock: threading.Lock = threading.Lock()

        # Initialize connection variable
        # Each thread will control one connection from one player
        self.to_be_cancelled_threads: list[threading.Thread] = []
        self.to_be_cancelled_threads_lock: threading.Lock = threading.Lock()

        # Create socket and start listening
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))
        self.socket.listen()

        # Game status
        self.is_started = False
        self.is_started_lock: threading.Lock = threading.Lock()

    def _stop_new_connection(self, thread: threading.Thread):
        print("Stopping incomming connections...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            msg = json.dumps({"type": REQUEST_SLOT, "contents": "stop"})
            s.sendall(bytes(msg, 'utf-8'))
        thread.join()
        print("Incomming connections have been stopped.")

    def _send_message(self, conn: socket.socket, msg: str, type_resp: str) -> bool:
        try:
            conn.sendall(bytes(msg, 'utf-8'))
        except ConnectionError as ce:
            print(
                f"Connection error when trying to respone to {add} about {type_resp}:\n{e}\n")
            return False
        except Exception as e:
            print(
                f"Unknown error when trying to to respone to {add} about {type_resp}:\n{e}\n")
            return False
        else:
            return True

    def _close_connection(self, conn: socket.socket, add, debug: bool = True):
        if debug:
            print(f"Closing the connection from {add}.")
        conn.close()
        if debug:
            print(f"The connection from {add} is closed.")

    def _handle_unrecognized_message(self, conn: socket.socket, add, e: json.decoder.JSONDecodeError = None):
        """
        All json error will result in server closing the socket.
        """
        if e is not None:
            erm = "unknown type of message (not json)"
            sent = "error-not-json"
        else:
            erm = "wrong format json"
            sent = "error-wrong-format"
        print(
            f"{add} sent a(n) {erm}, server will close socket.")
        try:
            print(f"Try to inform client {add} about the {erm}.")
            msg = json.dumps(
                {"type": RESPONSE_NAME, "contents": f"{sent}"})
            conn.sendall(bytes(msg, 'utf-8'))
        except ConnectionError as ce:
            print(
                f"Connection error when trying to inform {add} about the {erm}:\n{ce}\n")
        except Exception as e:
            print(
                f"Unknown error when trying to inform {add} about the {erm}:\n{e}\n")
        finally:
            self._close_connection(conn, add)

    def _handle_cancelling_accepted_connection(self, condition_obj: threading.Condition):
        def game_started():
            with self.is_started_lock:
                return self.is_started
        with condition_obj:
            while not game_started():
                condition_obj.wait()
                with self.threads_lock:
                    time.sleep(0.1)
                    self.threads = list(
                        filter(lambda thread: thread.is_alive(), self.threads))
                    print(
                        f"Number of threads (connections/registering clients) is running: {len(self.threads)}")

    def _handle_registering_accepted_connection(self, conn: socket.socket, add, event: threading.Event, condition_obj: threading.Condition):
        print(f"Start asking for player's name from {add}.")
        while True:
            data = conn.recv(1024).decode('utf-8')
            print(f"{add} sent: {data}")
            try:
                data = json.loads(data)
            except json.decoder.JSONDecodeError as je:
                self._handle_unrecognized_message(conn, add, je)
                with condition_obj:
                    condition_obj.notify()
                return
            else:
                if data["type"] == REGISTER_NAME:
                    request_name = data["name"]
                    print(
                        f"Name received from {add}: {request_name}. Cheking availability.")
                    dup_name = False
                    with self.players_lock:
                        for player in self.players:
                            if player.name == request_name:
                                dup_name = True
                                break
                        if not dup_name:
                            print(
                                f"{request_name} from {add} is accepted. Adding to the player list. Sending response.")
                            if len(self.players):
                                order = self.players[-1].order + 1
                            else:
                                order = 1
                            player = Player(conn, add, request_name, order)
                            self.players.append(player)
                            msg = json.dumps(
                                {"type": RESPONSE_NAME, "status": OK, "order": order})
                        else:
                            print(
                                f"{request_name} from {add} is rejected. Sending response. Waiting for next attempt.")
                            msg = json.dumps(
                                {"type": RESPONSE_NAME, "status": NO})
                        succeeded = self._send_message(
                            conn, msg, f"the availability of the name \"{request_name}\"")
                        if not succeeded:
                            self.players.remove(player)
                            self._close_connection(conn, add)
                            with condition_obj:
                                condition_obj.notify()
                            return
                        else:
                            print(f"Response for {add} is sent.")
                            if not dup_name:
                                if len(self.players) == self.num_player:
                                    event.set()
                                with condition_obj:
                                    condition_obj.notify()
                                return
                else:
                    self._handle_unrecognized_message(conn, add)
                    with condition_obj:
                        condition_obj.notify()
                    return

    def _handle_new_connection(self, event: threading.Event, condition_obj: threading.Condition):
        while True:
            conn, add = self.socket.accept()
            data = conn.recv(1024).decode('utf-8')
            print(f"{add} sent: {data}")
            try:
                data = json.loads(data)
            except json.JSONDecodeError as je:
                self._handle_unrecognized_message(conn, add, je)
                continue
            else:
                # Check format of request
                if data["type"] == REQUEST_SLOT and (data["contents"] == REQUEST_SLOT or data["contents"] == "stop"):
                    # If request a slot
                    if data["contents"] == REQUEST_SLOT:

                        # If game has already been started
                        game_started = False
                        with self.is_started_lock:
                            game_started = self.is_started
                        if game_started:
                            msg = json.dumps(
                                {"type": RESPONSE_SLOT, "contents": "started"})
                            succeeded = self._send_message(
                                conn, msg, "game is started.")
                            # Close connection regardless of the state of the sent message.
                            # Because the game is already started.
                            self._close_connection(conn, add)
                            continue

                        # If the connection is full (max number of players)
                        is_full = False
                        with self.players_lock:
                            with self.threads_lock:
                                if len(self.players) == self.num_player:
                                    is_full = True
                                if len(self.players) + len(self.threads) == self.num_player:
                                    is_full = True
                        if is_full:
                            msg = json.dumps(
                                {"type": RESPONSE_SLOT, "contents": "full"})
                            succeeded = self._send_message(
                                conn, msg, "game is full.")
                            # Close connection regardless of the state of the sent message.
                            # Because the slot is full anyway.
                            self._close_connection(conn, add)
                            continue

                        # Accept new connection
                        msg = json.dumps(
                            {"type": RESPONSE_SLOT, "contents": "ok"})
                        succeeded = self._send_message(
                            conn, msg, "slot request acceptance.")
                        if succeeded:
                            # Establish new thread for registering player
                            thread_id = threading.Thread(
                                target=self._handle_registering_accepted_connection, args=(conn, add, event, condition_obj))
                            thread_id.name = thread_id.name + f" for {add}"
                            print(f"Thread {thread_id.name} is created.")
                            with self.threads_lock:
                                self.threads.append(thread_id)
                                print(f"Thread {thread_id.name} is started.")
                                print(
                                    f"Number of threads (connections/registering clients) is running: {len(self.threads)}")
                            thread_id.start()
                        else:
                            # Close due to error
                            self._close_connection(conn, add)

                    # If request to stop the receving incomming connection thread
                    else:
                        conn.close()
                        return
                # Unknown request
                else:
                    self._handle_unrecognized_message(conn, add)
                    continue

    def _load_questions(self, event: threading.Event):
        with self.questions_lock:
            with open(currentdir + '/questions.json') as file:
                db = json.load(file)
            questions = db["questions"]
            self.questions = random.sample(questions, MAX_QUESTIONS)
            event.set()

    def _send_config_recv_response(self, msg: str, conn: socket.socket):
        conn.sendall(bytes(msg, 'utf-8'))
        data = conn.recv(BUFFER_SIZE)

    def _get_current_player(self, playable_player: list[bool], cur: int = None):
        if cur is None:
            return 0
        else:
            for i in range(cur + 1, len(playable_player)):
                if playable_player[i]:
                    return i
            for i in range(len(playable_player)):
                if playable_player[i]:
                    return i

    def _question_message(self, cur_player, question_idx, question):
        return json.dumps({"questions": question, "playername": self.players[cur_player].name, "remain-question": MAX_QUESTIONS-1-question_idx})

    def _send_ques_to_cur(self, conn: socket.socket, msg: str, ans: str, result: list[str], condi: threading.Condition):
        # Send question
        conn.sendall(bytes(msg, 'utf-8'))

        # Receive answer
        data = conn.recv(BUFFER_SIZE).decode('utf-8')
        data = json.loads(data)

        if data["answer"] == ans:
            conn.sendall(bytes(json.dumps({"verdict": OK}), 'utf-8'))
            result[0] = OK
        elif data["answer"] == "Timeout":
            conn.sendall(bytes(json.dumps({"verdict": NO}), 'utf-8'))
            result[0] = NO
        elif data["answer"] == SKIP:
            conn.sendall(bytes(json.dumps({"verdict": SKIP}), 'utf-8'))
            result[0] = SKIP
        else:
            conn.sendall(bytes(json.dumps({"verdict": NO}), 'utf-8'))
            result[0] = NO

        time.sleep(1)
        with condi:
            condi.notify_all()


    def _send_ques_to_res(self, conn: socket.socket, msg: str, result: list[str], condi: threading.Condition):
        # Send question
        conn.sendall(bytes(msg, 'utf-8'))

        # Receive something
        data = conn.recv(BUFFER_SIZE).decode('utf-8')

        with condi:
            start = time.time()
            while True:
                condi.wait()
                break
            conn.sendall(bytes(json.dumps({"verdict": result[0]}), 'utf-8'))
            

    def _run_game(self):
        # Send config
        list_dict_players = []
        threads = []
        for player in self.players:
            list_dict_players.append(
                {"name": player.name, "order": player.order})
        msg = json.dumps({"players": list_dict_players,
                         "questions": MAX_QUESTIONS, "timeout": TIMEOUT})

        for player in self.players:
            thread_id = threading.Thread(
                target=self._send_config_recv_response, args=(msg, player.conn))
            threads.append(thread_id)
            thread_id.start()

        for thread in threads:
            thread.join()

        playable_player = [True] * len(self.players)

        # Start the game, begin to send questions
        threads = []
        cur_player = self._get_current_player(playable_player)

        for idx, question_ in enumerate(self.questions):
            question = question_.copy()
            ans = question.pop("answer")
            result = [""]
            msg = self._question_message(cur_player, idx, question)
            condi = threading.Condition()

            for idp, player in enumerate(self.players):
                if idp == cur_player:
                    thread_id = threading.Thread(
                        target=self._send_ques_to_cur, args=(player.conn, msg, ans, result, condi))
                else:
                    thread_id = threading.Thread(
                        target=self._send_ques_to_res, args=(player.conn, msg, result, condi))
                threads.append(thread_id)
                thread_id.start()

            for thread in threads:
                thread.join()

            threads = []

            if result[0] == NO:
                playable_player[cur_player] = False
                cur_player = self._get_current_player(playable_player, cur_player)

            if result[0] == SKIP:
                cur_player = self._get_current_player(playable_player, cur_player)

            if idx == len(self.questions) - 1:
                for idp, player in enumerate(self.players):
                    player.conn.sendall(bytes(json.dumps({"winner":self.players[cur_player].name}), 'utf-8'))            

    def run(self):
        """Start to receive incomming connection and to load question into memory.
        Each job will be allocated to a thread
        Main thread (function run()) will wait for the completion of two jobs before continuing with the game
        Receiving incomming connection will finished when there are enough players connected to the server or timeout (5 mins)
        Loading question will finished when the required number of questions loaded or timeout (1 mins)
        Waiting will use Event Object"""

        # Setup thread that handles cancelling accepted connections
        cancl_condi = threading.Condition()
        cancelling_connection_thread = threading.Thread(
            target=self._handle_cancelling_accepted_connection, args=(cancl_condi,))
        cancelling_connection_thread.start()

        # Setup thread handles incomming connections
        wait_connecting = threading.Event()
        new_connection_thread = threading.Thread(
            target=self._handle_new_connection, args=(wait_connecting, cancl_condi))
        new_connection_thread.start()

        # Set up thread handles loading questions
        wait_loading = threading.Event()
        load_question_thread = threading.Thread(
            target=self._load_questions, args=(wait_loading,))
        load_question_thread.start()

        ############################################################
        ## Waiting for players' connections and loading questions ##
        ############################################################

        # Wait for loading first as it tends to be faster
        loading_state = wait_loading.wait(60)
        if not loading_state:
            print(
                "FATAL: Database takes too much time to load questions, server will be forced to shutdown.")

        # Wait for players' connections
        connecting_state = wait_connecting.wait(120)
        if not connecting_state:
            print(
                "WARN: Waiting players for too long, server will closed all connections and start new game.")

        # Assume everything is good
        # Set the game status to started
        with self.is_started_lock:
            self.is_started = True

        # Notify and join the cancelling_connection_thread
        with cancl_condi:
            cancl_condi.notify()
        cancelling_connection_thread.join()
        print(f"{cancelling_connection_thread.name} ended.")

        # Join the cancelling_connection_thread
        load_question_thread.join()
        print(f"{load_question_thread.name} ended.")

        # We do not join new_connection_thread to let new connections comming in and then refuse them.

        ####################
        ## Begin the game ##
        ####################
        self._run_game()

        # Stop accepting new connection
        self._stop_new_connection(new_connection_thread)

        # Stop connections from players
        print("Stopping connections from players...")
        for player in self.players:
            player.conn.close()
        print("Connections from players have been stopped...")


def main():
    s = Server(MAX_PLAYERS, QUESTION_SIZE, HOST, PORT)
    s.run()


if __name__ == '__main__':
    main()
