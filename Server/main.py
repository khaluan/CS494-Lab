import socket
import threading
import json
import logging
import time

import os
import sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Config.config import *
from Config.constant import *


class Player:
    def __init__(self, conn, add, name='', order=-1):
        self.conn = conn
        self.add = add
        self.name = name
        self.order = order


class Server:
    def __init__(self, num_player: int, num_questions: int, host: str, port: str) -> None:
        # Initialize game's parameters
        self.num_player = num_player
        self.num_questions = num_questions
        self.players: list[Player] = []
        self.players_lock: threading.Lock = threading.Lock()

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

    # All json error will result in server closing the socket.
    def _handle_unrecognized_message(self, conn: socket.socket, add, e: json.decoder.JSONDecodeError = None):
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

    def _handle_registering_accepted_connection(self, conn: socket.socket, add, condition_obj: threading.Condition):
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
                            conn, msg, f"the availability of the name {request_name}")
                        if not succeeded:
                            self.players.remove(player)
                            self._close_connection(conn, add)
                            with condition_obj:
                                condition_obj.notify()
                            return
                        else:
                            print(f"Response for {add} is sent.")
                            with condition_obj:
                                condition_obj.notify()
                            return
                else:
                    self._handle_unrecognized_message(conn, add)
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
                                    event.set()
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
                                target=self._handle_registering_accepted_connection, args=(conn, add, condition_obj))
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

    def _load_question(self, event: threading.Event):
        pass

    def run(self):
        # Start to receive incomming connection and to load question into memory.
        # Each job will be allocated to a thread
        # Main thread (function run()) will wait for the completion of two jobs before continuing with the game
        # Receiving incomming connection will finished when there are enough players connected to the server or timeout (5 mins)
        # Loading question will finished when the required number of questions loaded or timeout (1 mins)
        # Waiting will use Event Object

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
        # wait_loading = threading.Event()
        # load_question_thread = threading.Thread(
        #     target=self._load_question, args=(wait_loading))
        # load_question_thread.start()

        ############################################################
        ## Waiting for players' connections and loading questions ##
        ############################################################

        # Wait for loading first as it tends to be faster
        # loading_state = wait_loading.wait(60)
        # if not loading_state:
        #     # TODO: Handle loading questions timeout
        #     pass

        # Wait for players' connections
        connecting_state = wait_connecting.wait(10)
        if not connecting_state:
            # TODO: Handle connection timeout (not enough players)
            pass

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
        # load_question_thread.join()

        # And then clear the event
        wait_connecting.clear()
        # wait_loading.clear()

        # We do not join new_connection_thread to let new connections comming in and then refuse them.

        ####################
        ## Begin the game ##
        ####################

        # Stop accepting new connection
        self._stop_new_connection(new_connection_thread)

        # Stop connections from players
        print("Stopping connections from players...")
        # for thread in self.threads:
        #     thread.join()
        print("Connections from players have been stopped...")


def main():
    s = Server(MAX_PLAYERS, QUESTION_SIZE, HOST, PORT)
    s.run()


if __name__ == '__main__':
    main()
