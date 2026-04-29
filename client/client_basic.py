import socket
import threading
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import HOST, PORT_BASIC, RECV_BUFFER

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT_BASIC))
print(f"Connected to {HOST}:{PORT_BASIC}! Type messages. Press Ctrl+C to quit.\n")


def receive():
    while True:
        try:
            data = s.recv(RECV_BUFFER)
            if not data:
                break
            print(f"\n[message]: {data.decode()}")
            print("You: ", end="", flush=True)
        except:
            break


threading.Thread(target=receive, daemon=True).start()

try:
    while True:
        msg = input("You: ")
        if msg:
            s.send(msg.encode())
except KeyboardInterrupt:
    s.close()