import socket
import threading
import json
import time
import signal
import sys
import os
import base64
import bcrypt

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import (
    HOST, PORT_MAIN, MAX_CLIENTS, RECV_BUFFER,
    MAX_MSG_LENGTH, MAX_HISTORY, DEFAULT_ROOMS,
    TOKEN_LENGTH, MIN_USERNAME_LEN, MAX_USERNAME_LEN, MIN_PASSWORD_LEN
)

# ── Storage ────────────────────────────────────────────────────
users = {}           # username → { "password_hash": str, "created_at": int }
sessions = {}        # token → username
rooms = {
    name: {"description": desc, "members": set(), "history": []}
    for name, desc in DEFAULT_ROOMS.items()
}
connections = {}     # username → { "conn": socket, "room": str|None }
lock = threading.Lock()
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


# ── Message builder ────────────────────────────────────────────

def make_msg(type_, sender, text, **kwargs):
    return json.dumps({
        "type": type_,
        "sender": sender,
        "text": text,
        "timestamp": int(time.time() * 1000),
        **kwargs
    }).encode()


# ── Task 5: Auth ───────────────────────────────────────────────

def generate_token():
    return base64.b64encode(os.urandom(TOKEN_LENGTH)).decode()

def register_user(username, password):
    if len(username) < MIN_USERNAME_LEN or len(username) > MAX_USERNAME_LEN:
        return False, f"Username must be {MIN_USERNAME_LEN}–{MAX_USERNAME_LEN} characters"
    if not username.isalnum():
        return False, "Username must be letters and numbers only"
    if len(password) < MIN_PASSWORD_LEN:
        return False, f"Password must be at least {MIN_PASSWORD_LEN} characters"
    with lock:
        if username in users:
            return False, "Username already taken"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        users[username] = {"password_hash": hashed, "created_at": int(time.time())}
    return True, "registered"

def login_user(username, password):
    with lock:
        user = users.get(username)
    if not user:
        return False, "Invalid username or password"
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return False, "Invalid username or password"
    token = generate_token()
    with lock:
        sessions[token] = username
    return True, token

def validate_token(token):
    with lock:
        return sessions.get(token)

def logout_user(token):
    with lock:
        sessions.pop(token, None)


# ── Task 4: Room helpers ───────────────────────────────────────

def get_room_list():
    return [{"name": n, "description": r["description"]} for n, r in rooms.items()]

def add_to_history(room_name, entry):
    rooms[room_name]["history"].append(entry)
    if len(rooms[room_name]["history"]) > MAX_HISTORY:
        rooms[room_name]["history"] = rooms[room_name]["history"][-MAX_HISTORY:]

def broadcast_to_room(room_name, message_bytes, exclude=None):
    with lock:
        members = set(rooms[room_name]["members"])
    for uname in members:
        if uname == exclude:
            continue
        info = connections.get(uname)
        if info:
            try:
                info["conn"].send(message_bytes)
            except Exception:
                pass

def send_user_list(room_name):
    with lock:
        members = list(rooms[room_name]["members"])
    broadcast_to_room(room_name,
        make_msg("room_users", "server", "", room=room_name, users=members))

def do_join_room(username, room_name):
    with lock:
        old_room = connections[username].get("room")

    if old_room and old_room in rooms:
        with lock:
            rooms[old_room]["members"].discard(username)
        broadcast_to_room(old_room,
            make_msg("system", "server", f"{username} left #{old_room}"))
        send_user_list(old_room)

    with lock:
        rooms[room_name]["members"].add(username)
        connections[username]["room"] = room_name
        history = list(rooms[room_name]["history"])

    return history


# ── Disconnect ─────────────────────────────────────────────────

def disconnect_client(username, token):
    with lock:
        room_name = connections.get(username, {}).get("room")
        if room_name and room_name in rooms:
            rooms[room_name]["members"].discard(username)
        connections.pop(username, None)
    logout_user(token)
    if room_name and room_name in rooms:
        broadcast_to_room(room_name,
            make_msg("system", "server", f"{username} disconnected"))
        send_user_list(room_name)
    print(f"[-] {username} disconnected")


# ── Per-client handler ─────────────────────────────────────────

def handle(conn, username, token):
    conn.send(make_msg("room_list", "server", "", rooms=get_room_list()))

    while True:
        try:
            data = conn.recv(RECV_BUFFER)
            if not data:
                break

            msg = json.loads(data.decode())

            # Task 5: validate token on every single message
            if validate_token(msg.get("token", "")) != username:
                conn.send(make_msg("error", "server", "Invalid session. Please login again."))
                break

            msg_type = msg.get("type")

            if msg_type == "disconnect":
                print(f"[{username}] requested disconnect")
                break

            elif msg_type == "list_rooms":
                conn.send(make_msg("room_list", "server", "", rooms=get_room_list()))

            elif msg_type == "join_room":
                room_name = msg.get("room", "").strip()
                if room_name not in rooms:
                    conn.send(make_msg("error", "server",
                        f"Room '{room_name}' not found. Use /rooms"))
                    continue
                history = do_join_room(username, room_name)
                conn.send(make_msg("room_joined", "server", "",
                    room=room_name,
                    description=rooms[room_name]["description"],
                    history=history
                ))
                broadcast_to_room(room_name,
                    make_msg("system", "server", f"{username} joined #{room_name}"),
                    exclude=username)
                send_user_list(room_name)

            elif msg_type == "chat":
                with lock:
                    room_name = connections[username].get("room")
                if not room_name:
                    conn.send(make_msg("error", "server",
                        "You are not in a room. Use /join <roomname>"))
                    continue
                text = msg.get("text", "").strip()
                if not text:
                    continue
                if len(text) > MAX_MSG_LENGTH:
                    conn.send(make_msg("error", "server",
                        f"Message too long (max {MAX_MSG_LENGTH} chars)"))
                    continue
                print(f"[#{room_name}] {username}: {text}")
                out = make_msg("chat", username, text, room=room_name)
                add_to_history(room_name, json.loads(out.decode()))
                broadcast_to_room(room_name, out)

            else:
                conn.send(make_msg("error", "server", f"Unknown type: {msg_type}"))

        except (json.JSONDecodeError, KeyError):
            conn.send(make_msg("error", "server", "Malformed message"))
        except Exception:
            break

    disconnect_client(username, token)


# ── Auth handshake ─────────────────────────────────────────────

def auth_handshake(conn, addr):
    conn.send(make_msg("auth_required", "server",
        "Welcome to PyChat! Please register or login.",
        actions=["register", "login"]
    ))

    for _ in range(5):
        try:
            data = conn.recv(RECV_BUFFER)
            if not data:
                return None, None
            msg = json.loads(data.decode())
            msg_type = msg.get("type")
            username = msg.get("username", "").strip()
            password = msg.get("password", "")

            if msg_type == "register":
                ok, result = register_user(username, password)
                if ok:
                    conn.send(make_msg("registered", "server",
                        f"Account created! Now login as {username}."))
                    print(f"[+] Registered: {username}")
                else:
                    conn.send(make_msg("error", "server", result))

            elif msg_type == "login":
                ok, result = login_user(username, password)
                if ok:
                    token = result
                    with lock:
                        if username in connections:
                            try:
                                connections[username]["conn"].send(
                                    make_msg("error", "server",
                                        "Logged in from another location."))
                                connections[username]["conn"].close()
                            except Exception:
                                pass
                        connections[username] = {"conn": conn, "room": None}
                    conn.send(make_msg("logged_in", "server",
                        f"Welcome back, {username}!",
                        token=token, username=username))
                    print(f"[+] {username} logged in from {addr}")
                    return username, token
                else:
                    conn.send(make_msg("error", "server", result))
            else:
                conn.send(make_msg("error", "server",
                    "Send type 'register' or 'login'"))
        except Exception:
            return None, None

    return None, None


# ── Shutdown ───────────────────────────────────────────────────

def stop_server(sig=None, frame=None):
    print("\n[Stopping server...]")
    msg = make_msg("disconnect", "server", "Server is shutting down.")
    with lock:
        snapshot = list(connections.items())
    for uname, info in snapshot:
        try:
            info["conn"].send(msg)
            info["conn"].close()
        except Exception:
            pass
    server.close()
    print("[Server stopped]")
    sys.exit(0)

signal.signal(signal.SIGINT, stop_server)


# ── Server command thread ──────────────────────────────────────

def server_commands():
    while True:
        try:
            cmd = input().strip()
        except EOFError:
            break
        if cmd == "/stop":
            stop_server()
        elif cmd == "/list":
            with lock:
                if connections:
                    for uname, info in connections.items():
                        print(f"  {uname} → #{info.get('room') or 'no room'}")
                else:
                    print("  No clients connected")
        elif cmd == "/rooms":
            for name, r in rooms.items():
                with lock:
                    count = len(r["members"])
                print(f"  #{name} ({count} online) — {r['description']}")
        elif cmd == "/users":
            with lock:
                print(f"  Registered: {len(users)}")
                for uname in users:
                    print(f"    {uname}")
        elif cmd == "/help":
            print("  /stop   shut down server")
            print("  /list   connected clients and rooms")
            print("  /rooms  room stats")
            print("  /users  all registered users")
        else:
            print(f"  Unknown: {cmd}. Type /help")

threading.Thread(target=server_commands, daemon=True).start()


# ── Main accept loop ───────────────────────────────────────────

server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT_MAIN))
server.listen(MAX_CLIENTS)
print(f"PyChat server running on {HOST}:{PORT_MAIN}")
print(f"Rooms: {', '.join('#' + n for n in rooms)}")
print("Type /help for commands\n")

while True:
    try:
        conn, addr = server.accept()
        print(f"[~] Connection from {addr}")

        def client_entry(c, a):
            username, token = auth_handshake(c, a)
            if username:
                handle(c, username, token)
            else:
                print(f"[~] Auth failed from {a}")
                try:
                    c.send(make_msg("error", "server",
                        "Too many failed attempts. Disconnecting."))
                    c.close()
                except Exception:
                    pass

        threading.Thread(target=client_entry, args=(conn, addr), daemon=True).start()

    except OSError:
        break