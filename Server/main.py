import socket
import threading

import time
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
        self.players = []

        # Innitialize host, port, and list of threads for connections of the game
        self.host = host
        self.port = port

        # Initialize connection variable
        # Each thread will control one connection from one player
        self.threads = []

        # Create socket and start listening
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))
        self.socket.listen()

        # Game status
        self.is_started = False

    def _handle_connection(self, conn, add):
        print(f"Waiting from {add}")
        data = conn.recv(1024)
        print(f"Data received: {data}")
        conn.sendall(b"Ack")
        conn.close()
    
    def _receive_new_connection(self):
        while True:
            conn, add = self.socket.accept()

            data = conn.recv(1024).decode('utf-8')

            data = json.loads(data)

            if data["type"] == "request":
                if data["contents"] == "join":
                    if len(self.threads) == self.num_player:
                        msg = json.dumps({"type":"response", "contents":"full"})
                        conn.sendall(bytes(msg))
                        conn.close()
                    elif self.is_started:
                        msg = json.dumps({"type":"response", "contents":"started"})
                        conn.sendall(bytes(msg))
                        conn.close()
                    else:
                        thread_id = threading.Thread(target=self._handle_connection, args=(conn, add))
                        self.threads.append(thread_id)
                        thread_id.start()
                elif data["contents"] == "stop":
                    conn.close()
                    break
                else:
                    conn.sendall(bytes(f'Contents of received message are \"{data["contents"]}\". Unknown contents of message for requesting new connection.'))
                    conn.close()
            else:
                conn.sendall(bytes(f'Type of received message is \"{data["type"]}\". Unknown type of message for requesting new connection.'))
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

        time.sleep(60)


        # Stopping accepting new connection
        self._stop_new_connection(new_connection_thread)

        # Stopping connection from player
        print("Stopping connections from players...")
        for thread in self.threads:
            thread.join()
        print("Connections from players have been stopped...")

        self.socket.close()

def main():
    s = Server(MAX_PLAYERS, 1, HOST, PORT)
    s.game()

if __name__ == '__main__':
    main()