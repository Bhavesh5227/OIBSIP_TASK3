"""
server_ws.py — Task 7
WebSocket server (asyncio) + HTTP server serving interface/index.html
Same auth/room/history logic as server_main.py, just different transport.
"""
import asyncio
import websockets
import json
import time
import threading
import signal
import sys
import os
import base64
import bcrypt
from http.server import HTTPServer, SimpleHTTPRequestHandler

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import (
    HOST, PORT_MAIN, PORT_HTTP,
    MAX_CLIENTS, RECV_BUFFER, MAX_MSG_LENGTH, MAX_HISTORY,
    DEFAULT_ROOMS, TOKEN_LENGTH,
    MIN_USERNAME_LEN, MAX_USERNAME_LEN, MIN_PASSWORD_LEN
)

# ── Storage (same as server_main.py) ──────────────────────────
users       = {}
sessions    = {}
rooms       = {
    name: {"description": desc, "members": set(), "history": []}
    for name, desc in DEFAULT_ROOMS.items()
}
connections = {}   # username → {"ws": websocket, "room": str|None}


# ── Message builder ────────────────────────────────────────────
# Returns str (not bytes) — websockets.send() takes str

def make_msg(type_, sender, text, **kwargs):
    return json.dumps({
        "type":      type_,
        "sender":    sender,
        "text":      text,
        "timestamp": int(time.time() * 1000),
        **kwargs
    })


# ── Auth ───────────────────────────────────────────────────────

def generate_token():
    return base64.b64encode(os.urandom(TOKEN_LENGTH)).decode()

def register_user(username, password):
    if len(username) < MIN_USERNAME_LEN or len(username) > MAX_USERNAME_LEN:
        return False, f"Username must be {MIN_USERNAME_LEN}–{MAX_USERNAME_LEN} characters"
    if not username.isalnum():
        return False, "Letters and numbers only"
    if len(password) < MIN_PASSWORD_LEN:
        return False, f"Password must be at least {MIN_PASSWORD_LEN} characters"
    if username in users:
        return False, "Username already taken"
    users[username] = {
        "password_hash": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
        "created_at":    int(time.time())
    }
    return True, "registered"

def login_user(username, password):
    user = users.get(username)
    if not user:
        return False, "Invalid username or password"
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return False, "Invalid username or password"
    token = generate_token()
    sessions[token] = username
    return True, token

def validate_token(token):
    return sessions.get(token)

def logout_user(token):
    sessions.pop(token, None)


# ── Room helpers ───────────────────────────────────────────────

def get_room_list():
    return [{"name": n, "description": r["description"]} for n, r in rooms.items()]

def add_to_history(room_name, entry):
    rooms[room_name]["history"].append(entry)
    if len(rooms[room_name]["history"]) > MAX_HISTORY:
        rooms[room_name]["history"] = rooms[room_name]["history"][-MAX_HISTORY:]

async def broadcast_to_room(room_name, message, exclude=None):
    members = set(rooms[room_name]["members"])
    for uname in members:
        if uname == exclude:
            continue
        info = connections.get(uname)
        if info:
            try:
                await info["ws"].send(message)
            except Exception:
                pass

async def send_user_list(room_name):
    members = list(rooms[room_name]["members"])
    await broadcast_to_room(room_name,
        make_msg("room_users", "server", "", room=room_name, users=members))

async def do_join_room(username, room_name):
    old_room = connections[username].get("room")
    if old_room and old_room in rooms:
        rooms[old_room]["members"].discard(username)
        await broadcast_to_room(old_room,
            make_msg("system", "server", f"{username} left #{old_room}"))
        await send_user_list(old_room)
    rooms[room_name]["members"].add(username)
    connections[username]["room"] = room_name
    return list(rooms[room_name]["history"])


# ── Disconnect ─────────────────────────────────────────────────

async def disconnect_client(username, token):
    room_name = connections.get(username, {}).get("room")
    if room_name and room_name in rooms:
        rooms[room_name]["members"].discard(username)
    connections.pop(username, None)
    logout_user(token)
    if room_name and room_name in rooms:
        await broadcast_to_room(room_name,
            make_msg("system", "server", f"{username} disconnected"))
        await send_user_list(room_name)
    print(f"[-] {username} disconnected")


# ── Auth handshake ─────────────────────────────────────────────

async def auth_handshake(ws):
    await ws.send(make_msg("auth_required", "server",
        "Welcome to PyChat! Please register or login.",
        actions=["register", "login"]
    ))

    for _ in range(5):
        try:
            raw      = await ws.recv()
            msg      = json.loads(raw)
            msg_type = msg.get("type")
            username = msg.get("username", "").strip()
            password = msg.get("password", "")

            if msg_type == "register":
                ok, result = register_user(username, password)
                if ok:
                    await ws.send(make_msg("registered", "server",
                        f"Account created! Now login as {username}."))
                    print(f"[+] Registered: {username}")
                else:
                    await ws.send(make_msg("error", "server", result))

            elif msg_type == "login":
                ok, result = login_user(username, password)
                if ok:
                    token = result
                    # Kick old session
                    if username in connections:
                        try:
                            await connections[username]["ws"].send(
                                make_msg("error", "server",
                                    "Logged in from another location."))
                        except Exception:
                            pass
                    connections[username] = {"ws": ws, "room": None}
                    await ws.send(make_msg("logged_in", "server",
                        f"Welcome back, {username}!",
                        token=token, username=username))
                    print(f"[+] {username} logged in")
                    return username, token
                else:
                    await ws.send(make_msg("error", "server", result))
            else:
                await ws.send(make_msg("error", "server",
                    "Send type 'register' or 'login'"))
        except Exception:
            return None, None

    return None, None


# ── Main WebSocket handler ─────────────────────────────────────

async def handler(ws):
    username, token = await auth_handshake(ws)
    if not username:
        return

    # Send room list right after login
    await ws.send(make_msg("room_list", "server", "", rooms=get_room_list()))

    try:
        async for raw in ws:
            msg = json.loads(raw)

            # Validate token on every message
            if validate_token(msg.get("token", "")) != username:
                await ws.send(make_msg("error", "server", "Invalid session."))
                break

            t = msg.get("type")

            if t == "disconnect":
                break

            elif t == "list_rooms":
                await ws.send(make_msg("room_list", "server", "",
                    rooms=get_room_list()))

            elif t == "join_room":
                room = msg.get("room", "").strip()
                if room not in rooms:
                    await ws.send(make_msg("error", "server",
                        f"Room '{room}' not found"))
                    continue
                history = await do_join_room(username, room)
                await ws.send(make_msg("room_joined", "server", "",
                    room=room,
                    description=rooms[room]["description"],
                    history=history))
                await broadcast_to_room(room,
                    make_msg("system", "server", f"{username} joined #{room}"),
                    exclude=username)
                await send_user_list(room)

            elif t == "chat":
                room = connections[username].get("room")
                if not room:
                    await ws.send(make_msg("error", "server",
                        "Join a room first."))
                    continue
                text = msg.get("text", "").strip()
                if not text or len(text) > MAX_MSG_LENGTH:
                    continue
                print(f"[#{room}] {username}: {text}")
                out = make_msg("chat", username, text, room=room)
                add_to_history(room, json.loads(out))
                await broadcast_to_room(room, out)

            elif t == "typing":
                room = connections[username].get("room")
                if room:
                    await broadcast_to_room(room,
                        make_msg("typing", username, "",
                            typing=msg.get("typing", False)),
                        exclude=username)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        await disconnect_client(username, token)


# ── HTTP server — serves interface/index.html ──────────────────

INTERFACE_DIR = os.path.join(os.path.dirname(__file__), '..', 'interface')

class FrontendHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=INTERFACE_DIR, **kwargs)
    def log_message(self, *args):
        pass  # silence HTTP access logs

def run_http():
    httpd = HTTPServer((HOST, PORT_HTTP), FrontendHandler)
    print(f"Frontend     →  http://{HOST}:{PORT_HTTP}")
    httpd.serve_forever()


# ── Entry point ───────────────────────────────────────────────

async def main():
    threading.Thread(target=run_http, daemon=True).start()
    print(f"WebSocket    →  ws://{HOST}:{PORT_MAIN}")
    print(f"Rooms: {', '.join('#' + n for n in rooms)}")
    print("\nOpen your browser at http://localhost:8080\n")

    async with websockets.serve(handler, HOST, PORT_MAIN):
        await asyncio.Future()   # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Server stopped]")