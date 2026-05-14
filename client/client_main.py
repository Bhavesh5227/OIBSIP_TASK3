import socket
import threading
import json
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import HOST, PORT_MAIN, RECV_BUFFER, MAX_MSG_LENGTH

# ── Connection ─────────────────────────────────────────────────
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect((HOST, PORT_MAIN))
except ConnectionRefusedError:
    print(f"Could not connect to {HOST}:{PORT_MAIN}")
    print("Make sure the server is running first.")
    sys.exit(1)

# ── State ──────────────────────────────────────────────────────
state = {
    "token":    None,
    "username": None,
    "room":     None,
}


# ── Message builder ────────────────────────────────────────────

def make_msg(type_, text, **kwargs):
    return json.dumps({
        "type": type_,
        "sender": state["username"] or "",
        "text": text,
        "token": state["token"] or "",
        "timestamp": int(time.time() * 1000),
        **kwargs
    }).encode()


# ── Background receiver ────────────────────────────────────────

def receive():
    while True:
        try:
            data = s.recv(RECV_BUFFER)
            if not data:
                print("\n[Server closed the connection]")
                os._exit(0)

            msg = json.loads(data.decode())
            msg_type = msg.get("type")

            # Task 5: auth responses
            if msg_type == "auth_required":
                print(f"\n{msg['text']}")
                print("Commands: /register <username> <password>  or  /login <username> <password>\n")

            elif msg_type == "registered":
                print(f"\n[OK] {msg['text']}")

            elif msg_type == "logged_in":
                state["token"]    = msg["token"]
                state["username"] = msg["username"]
                print(f"\n[OK] {msg['text']}")
                print("Commands: /rooms  /join <name>  /quit\n")

            elif msg_type == "error":
                print(f"\n[ERROR] {msg['text']}")

            # Task 4: room responses
            elif msg_type == "room_list":
                print("\n  Available rooms:")
                for r in msg.get("rooms", []):
                    print(f"    #{r['name']} — {r['description']}")
                print("  Use /join <name> to enter a room")

            elif msg_type == "room_joined":
                state["room"] = msg.get("room")
                print(f"\n  Joined #{state['room']} — {msg.get('description', '')}")
                history = msg.get("history", [])
                if history:
                    print(f"  ── last {len(history)} messages ──")
                    for m in history:
                        ts = time.strftime("%H:%M", time.localtime(m.get("timestamp", 0) / 1000))
                        print(f"  [{ts}] {m['sender']}: {m['text']}")
                    print("  ─────────────────────────")

            elif msg_type == "room_users":
                users = msg.get("users", [])
                print(f"\n  Online in #{msg.get('room')}: {', '.join(users)}")

            elif msg_type == "system":
                print(f"\n  *** {msg['text']} ***")

            elif msg_type == "chat":
                ts = time.strftime("%H:%M", time.localtime(msg.get("timestamp", 0) / 1000))
                room = msg.get("room", state["room"] or "")
                print(f"\n  [{ts}] #{room} | {msg['sender']}: {msg['text']}")

            elif msg_type == "disconnect":
                print(f"\n  *** {msg['text']} ***")
                os._exit(0)

            # Reprint prompt after any message
            if state["token"]:
                room_label = f"#{state['room']}" if state["room"] else "no room"
                print(f"{state['username']}@{room_label}> ", end="", flush=True)
            else:
                print("> ", end="", flush=True)

        except json.JSONDecodeError:
            print("\n[Received malformed data from server]")
        except Exception:
            break

threading.Thread(target=receive, daemon=True).start()


# ── Send loop ──────────────────────────────────────────────────

def print_help():
    print("\n  Before login:")
    print("    /register <username> <password>  create account")
    print("    /login <username> <password>     sign in")
    print("\n  After login:")
    print("    /rooms               list available rooms")
    print("    /join <name>         join a room")
    print("    /quit                disconnect cleanly")
    print("    <message>            send to current room\n")

print_help()

try:
    while True:
        # Dynamic prompt
        if state["token"]:
            room_label = f"#{state['room']}" if state["room"] else "no room"
            prompt = f"{state['username']}@{room_label}> "
        else:
            prompt = "> "

        text = input(prompt).strip()
        if not text:
            continue

        # ── Pre-auth commands ──────────────────────────────────
        if text.startswith("/register "):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                print("  Usage: /register <username> <password>")
                continue
            s.send(json.dumps({
                "type": "register",
                "username": parts[1],
                "password": parts[2],
                "timestamp": int(time.time() * 1000)
            }).encode())

        elif text.startswith("/login "):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                print("  Usage: /login <username> <password>")
                continue
            s.send(json.dumps({
                "type": "login",
                "username": parts[1],
                "password": parts[2],
                "timestamp": int(time.time() * 1000)
            }).encode())

        elif text == "/help":
            print_help()

        # ── Post-auth commands (require token) ─────────────────
        elif not state["token"]:
            print("  Please /register or /login first")

        elif text == "/quit":
            s.send(make_msg("disconnect", "leaving"))
            print("Disconnecting...")
            break

        elif text == "/rooms":
            s.send(make_msg("list_rooms", ""))

        elif text.startswith("/join "):
            parts = text.split(" ", 1)
            if len(parts) < 2 or not parts[1].strip():
                print("  Usage: /join <roomname>")
                continue
            s.send(make_msg("join_room", "", room=parts[1].strip()))

        # ── Chat message ───────────────────────────────────────
        else:
            if not state["room"]:
                print("  You are not in a room. Use /join <name>")
                continue
            if len(text) > MAX_MSG_LENGTH:
                print(f"  Too long (max {MAX_MSG_LENGTH} chars)")
                continue
            s.send(make_msg("chat", text))

except KeyboardInterrupt:
    pass
finally:
    if state["token"]:
        try:
            s.send(make_msg("disconnect", "leaving"))
        except Exception:
            pass
    s.close()
    print("\nDisconnected.")