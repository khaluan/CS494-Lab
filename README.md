# Multithreaded socket to handle multiple 

Configuration in Config/config.py including PORT and #MAX_PLAYERS

## Start server
Start server python Server/main.py

The server accept MAX_PLAYERS connections then create each thread to handle each connection. Since each thread is run independently, but the I/O in each thread is blocking I/O, it still does not hang the main thread.

## Start client:
Usage: python3 Client/main.py <wait_time>

The client will create a connection to the server wait for <wait_time> seconds before sending message to server. 

Adjust the different <wait_time> to test whether the program is blocked while waiting for message from other clients.

## Documentation
Report link: https://docs.google.com/document/d/1HBP7p4Ep6lMnZ4VQKi7O1tZ5NkoQ4s5MxDcAX5PGXLQ/edit?usp=sharing
## Bug: 
- [x] Close connection for duplicate name, client cannot rename 
- [x] Game does not start when enough client. 
- [x] Send random message for client not in turn 
