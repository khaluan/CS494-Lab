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

    def _register_player(self, conn: socket.socket, add):
        player_accpeted = False
        order = 0
        player = None
        while not player_accpeted:
            try:
                print(f"Waiting for player\'s name from {add}")
                data = conn.recv(1024).decode('utf-8')
                print(f"Received player\'s name from {add}: {data}")
                data = json.loads(data)
                if data["type"] == REGISTER_NAME:
                    request_name = data["name"]
                    dup_name = False
                    with self.players_lock:
                        for player in self.players:
                            if player.name == request_name:
                                dup_name = True
                                break
                    if not dup_name:
                        print(f"Received player\'s name from {add} is accepted.")
                        try:
                            with self.players_lock:
                                if len(self.players):
                                    order = self.players[-1].order + 1
                                else:
                                    order = 1
                                player = Player(conn, add, request_name, order)
                                self.players.append(player)
                            msg = json.dumps({"type":RESPONSE_NAME, "status":OK, "order":order})
                            conn.sendall(bytes(msg, 'utf-8'))
                        except ConnectionError as ce:
                            print(f"Connection error when trying to inform client {add} about available name:\n{e}\n")
                            print("Continue to close socket.")
                            conn.close()
                            print(f"Socket from {add} is closed.")
                            return
                        except Exception as e:
                            print(f"Unknown error when trying to inform client {add} about available name:\n{e}\n")
                            print("Continue to close socket.")
                            conn.close()
                            print(f"Socket from {add} is closed.")
                            return
                        else:
                            player_accpeted = True
                            print(f"Player from {add} accepted with name \"{request_name}\" and order \"{order}\" ")
                    else:
                        try:
                            msg = json.dumps({"type":RESPONSE_NAME, "status":NO})
                            conn.sendall(bytes(msg, 'utf-8'))
                        except ConnectionError as ce:
                            print(f"Connection error when trying to inform client {add} about duplicate name:\n{e}\n")
                            print("Continue to close socket.")
                            conn.close()
                            print(f"Socket from {add} is closed.")
                            return
                        except Exception as e:
                            print(f"Unknown error when trying to inform client {add} about duplicate name:\n{e}\n")
                            print("Continue to close socket.")
                            conn.close()
                            print(f"Socket from {add} is closed.")
                            return
                else:
                    try:
                        print(f"Try to inform client {add} about the error.")
                        msg = json.dumps({"type":RESPONSE_NAME, "contents":"error-wrong-format"})
                        conn.sendall(bytes(msg, 'utf-8'))
                    except ConnectionError as ce:
                        print(f"Connection error when trying to inform client {add} about wrong format message:\n{e}\n")
                        print("Continue to close socket.")
                    except Exception as e:
                        print(f"Unknown error when trying to inform client {add} about wrong format message:\n{e}\n")
                        print("Continue to close socket.")
                    finally:
                        conn.close()
                        print(f"Socket from {add} is closed.")
                        return
            except json.JSONDecodeError as e:
                print(f"Client from {add} sent did not sent a json, server will close socket.")
                try:
                    print(f"Try to inform client {add} about the wrong json.")
                    msg = json.dumps({"type":RESPONSE_NAME, "contents":"error-not-json"})
                    conn.sendall(bytes(msg, 'utf-8'))
                except ConnectionError as ce:
                    print(f"Connection error when trying to inform client {add} about the wrong json:\n{e}\n")
                    print("Continue to close socket.")
                except Exception as e:
                    print(f"Unknown error when trying to inform client {add} about the wrong json:\n{e}\n")
                    print("Continue to close socket.")
                finally:
                    conn.close()
                    print(f"Socket from {add} is closed.")
                    return
            except ConnectionError as e:
                print(f"Error when registering client with connection {add}:\n{e}\n")
                print("Server will close socket.")
                conn.close()
                print(f"Socket from {add} is closed.")
                return
            except Exception as e:
                print(f"Unknown error when registering client with connection {add}:\n{e}\n")
                print("Server will close socket.")
                conn.close()
                print(f"Socket from {add} is closed.")
                return
    
    def _receive_new_connection(self):
        while True:
            conn, add = self.socket.accept()

            data = conn.recv(1024).decode('utf-8')

            data = json.loads(data)

            if data["type"] == REQUEST_SLOT:
                if data["contents"] == REQUEST_SLOT:
                    with self.players_lock:
                        if len(self.players) == self.num_player:
                            msg = json.dumps({"type":RESPONSE_SLOT, "contents":"full"})
                            conn.sendall(bytes(msg), 'utf-8')
                            conn.close()
                    if self.is_started:
                        msg = json.dumps({"type":RESPONSE_SLOT, "contents":"started"})
                        conn.sendall(bytes(msg, 'utf-8'))
                        conn.close()
                    else:
                        msg = json.dumps({"type":RESPONSE_SLOT, "contents":"ok"})
                        conn.sendall(bytes(msg, 'utf-8'))
                        thread_id = threading.Thread(target=self._register_player, args=(conn, add))
                        self.threads.append(thread_id)
                        print("Number of threads running: ", len(self.threads))
                        thread_id.start()
                elif data["contents"] == "stop":
                    conn.close()
                    break
                else:
                    conn.sendall(bytes(json.dumps({"type":RESPONSE_SLOT, "contents":"error-unknown-type"}), 'utf-8'))
                    conn.close()
            else:
                conn.sendall(bytes(json.dumps({"type":RESPONSE_SLOT, "contents":"error-unknown-content"}), 'utf-8'))
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

        for thread in self.threads:
            thread.join()

        self.threads = []

        # create new threads


        # Stop accepting new connection
        self._stop_new_connection(new_connection_thread)

        # Stop connections from players
        print("Stopping connections from players...")
        for thread in self.threads:
            thread.join()
        print("Connections from players have been stopped...")

def main():
    s = Server(MAX_PLAYERS, QUESTION_SIZE, HOST, PORT)
    s.game()

if __name__ == '__main__':
    main()