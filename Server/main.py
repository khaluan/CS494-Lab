import socket
import threading
import json

import os, sys
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

from Config.config import *

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

        # Create socket and start listening
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))
        self.socket.listen()

        # Game status
        self.is_started = False

    def _register_player(self, conn: socket.socket, add, thread_id: int):
        player_accpeted = False
        order = 0
        player = None
        while not player_accpeted:
            try:
                print(f"Waiting for player\'s name from {add}")
                data = conn.recv(1024).decode('utf-8')
                print(f"Received player\'s name from {add}: {data}")
                data = json.loads(data)
                if data["type"] == "request-name":
                    request_name = data["contents"]
                    dup_name = False
                    with self.players_lock:
                        for player in self.players:
                            if player.name == request_name:
                                dup_name = True
                                break
                    if not dup_name:
                        print(f"Received player\'s name from {add} is accepted.")
                        with self.players_lock:
                            if len(self.players):
                                order = self.players[-1].order + 1
                            else:
                                order = 1
                            player = Player(conn, add, request_name, order)
                            self.players.append(player)
                        player_accpeted = True
                        msg = json.dumps({"type":"response-name", "status":"OK", "order":order})
                        conn.sendall(bytes(msg, 'utf-8'))
                    else:
                        msg = json.dumps({"type":"response-name", "status":"NO"})
                        conn.sendall(bytes(msg, 'utf-8'))
                else:
                    conn.sendall(bytes(json.dumps({"type":"response-name", "contents":"error-wrong-format"}), 'utf-8'))
                    conn.close()
            except json.JSONDecodeError as e:
                msg = json.dumps({"type":"response-name", "contents":"error-not-json"})
                print(f"Player from {add} sent wrong format message, waiting for new request.")
                try:
                    conn.sendall(bytes(msg, 'utf-8'))
                except ConnectionError as ce:
                    print(f"Cannot send message to player from {add}.")
                    if player_accpeted:
                        print("Attempting to remove the player from the list.")
                        with self.players_lock:
                            self.players.remove(player)
                        print("Removed player from the list.")
            except ConnectionError as e:
                print(f"Error when registering player with connection {add}:\n{e}\n")
                conn.close()
                return
            except Exception as e:
                print(f"Unhanled error when registering player with connection {add}:\n{e}\n")
                conn.close()
                return
    
    def _receive_new_connection(self):
        while True:
            conn, add = self.socket.accept()

            data = conn.recv(1024).decode('utf-8')

            data = json.loads(data)

            if data["type"] == "request":
                if data["contents"] == "join":
                    if len(self.players) == self.num_player:
                        msg = json.dumps({"type":"response", "contents":"full"})
                        conn.sendall(bytes(msg), 'utf-8')
                        conn.close()
                    elif self.is_started:
                        msg = json.dumps({"type":"response", "contents":"started"})
                        conn.sendall(bytes(msg, 'utf-8'))
                        conn.close()
                    else:
                        msg = json.dumps({"type":"response", "contents":"ok"})
                        conn.sendall(bytes(msg, 'utf-8'))
                        thread_id = threading.Thread(target=self._register_player, args=(conn, add, len(self.threads)))
                        self.threads.append(thread_id)
                        print("Number of threads running: ", len(self.threads))
                        thread_id.start()
                elif data["contents"] == "stop":
                    conn.close()
                    break
                else:
                    conn.sendall(bytes(json.dumps({"type":"response", "contents":"error-unknown-type"}), 'utf-8'))
                    conn.close()
            else:
                conn.sendall(bytes(json.dumps({"type":"response", "contents":"error-unknown-content"}), 'utf-8'))
                conn.close()
                

    def _stop_new_connection(self, thread: threading.Thread):
        print("Stopping incomming connections...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            msg = json.dumps({"type": "request", "contents":"stop"})
            s.sendall(bytes(msg, 'utf-8'))
        thread.join()
        print("Incomming connections have been stopped.")

    def game(self):
        new_connection_thread = threading.Thread(target=self._receive_new_connection)
        new_connection_thread.start()
        
        delay_count = 0
        while len(self.players) != self.num_player:
            if len(self.players) > self.num_player:
                print("Error: More connected players than specified.")
                # return
            # if delay_count == 5:
            #     if len(self.threads):
            #         for thread in self.threads:
            #             print(thread.name, thread.is_alive())
            #     else:
            #         print("No connections.")
            #     delay_count = 0
            # time.sleep(1)
            # delay_count += 1

        for thread in self.threads:
            thread.join()

        # create new threads


        # Stop accepting new connection
        self._stop_new_connection(new_connection_thread)

        # Stop connections from players
        print("Stopping connections from players...")
        for thread in self.threads:
            thread.join()
        print("Connections from players have been stopped...")



if __name__ == '__main__':
    main()