import socket
import threading
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import HOST, PORT_BASIC, MAX_CLIENTS, RECV_BUFFER

clients = []

def handle(conn, addr):
    while True:
        try:
            data = conn.recv(RECV_BUFFER)
            if not data:
                break

            msg = data.decode()
            print(f"[{addr}]: {msg}")

            for c in clients:
                if c != conn:
                    try:
                        c.send(data)
                    except:
                        pass
        except:
            break

    clients.remove(conn)
    conn.close()
    print("Client disconnected.")


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT_BASIC))
server.listen(MAX_CLIENTS)
print(f"Waiting for connections on {HOST}:{PORT_BASIC}...")

while True:
    conn, addr = server.accept()
    print(f"Connected by {addr}")
    clients.append(conn)
    threading.Thread(target=handle, args=(conn, addr), daemon=True).start()