import socket
import threading
import json
import time
import signal
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import (
    HOST, PORT_MAIN, MAX_CLIENTS, RECV_BUFFER, MAX_MSG_LENGTH
)

clients = {}
lock = threading.Lock()
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


# ── Message builder ────────────────────────────────────────────

def make_msg(type_, sender, text):
    return json.dumps({
        "type": type_,
        "sender": sender,
        "text": text,
        "timestamp": int(time.time() * 1000)
    }).encode()


# ── Broadcast ─────────────────────────────────────────────────

def broadcast(message_bytes, exclude_username=None):
    with lock:
        for username, conn in clients.items():
            if username != exclude_username:
                try:
                    conn.send(message_bytes)
                except:
                    pass


# ── Client cleanup ────────────────────────────────────────────

def disconnect_client(username, conn):
    with lock:
        clients.pop(username, None)
    conn.close()
    broadcast(make_msg("system", "server", f"{username} left the chat."))
    print(f"[-] {username} disconnected")


# ── Per-client thread ─────────────────────────────────────────

def handle(conn, username):
    broadcast(make_msg("system", "server", f"{username} joined the chat!"))

    while True:
        try:
            data = conn.recv(RECV_BUFFER)
            if not data:
                break

            msg = json.loads(data.decode())

            if msg["type"] == "disconnect":
                print(f"[{username}] requested disconnect")
                break

            # Enforce message length limit
            if len(msg.get("text", "")) > MAX_MSG_LENGTH:
                conn.send(make_msg("system", "server", "Message too long."))
                continue

            print(f"[{msg['sender']}]: {msg['text']}")
            broadcast(data, exclude_username=username)

        except:
            break

    disconnect_client(username, conn)


# ── Graceful shutdown ─────────────────────────────────────────

def stop_server(sig=None, frame=None):
    print("\n[Stopping server...]")
    shutdown_msg = make_msg("disconnect", "server", "Server is shutting down.")
    with lock:
        for username, conn in clients.items():
            try:
                conn.send(shutdown_msg)
                conn.close()
            except:
                pass
    server.close()
    print("[Server stopped]")
    sys.exit(0)


signal.signal(signal.SIGINT, stop_server)


# ── Server command thread ─────────────────────────────────────

def server_commands():
    while True:
        cmd = input()
        if cmd.strip() == "/stop":
            stop_server()
        elif cmd.strip() == "/list":
            with lock:
                if clients:
                    print(f"Online ({len(clients)}): {', '.join(clients.keys())}")
                else:
                    print("No clients connected")
        elif cmd.strip() == "/help":
            print("/stop  → shut down server")
            print("/list  → show connected users")


threading.Thread(target=server_commands, daemon=True).start()

# ── Main accept loop ──────────────────────────────────────────

server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT_MAIN))
server.listen(MAX_CLIENTS)
print(f"Server running on {HOST}:{PORT_MAIN}")
print("Press Ctrl+C or type /stop to shut down\n")

while True:
    try:
        conn, addr = server.accept()
        conn.send(make_msg("system", "server", "Enter your username:"))
        username_data = conn.recv(RECV_BUFFER)
        username = json.loads(username_data.decode())["text"].strip()

        with lock:
            clients[username] = conn

        print(f"[+] {username} connected from {addr}")
        threading.Thread(target=handle, args=(conn, username), daemon=True).start()

    except OSError:
        break