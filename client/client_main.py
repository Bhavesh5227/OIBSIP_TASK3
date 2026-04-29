import socket
import threading
import json
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.settings import HOST, PORT_MAIN, RECV_BUFFER, MAX_MSG_LENGTH

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT_MAIN))


# ── Message builder ────────────────────────────────────────────

def make_msg(type_, sender, text):
    return json.dumps({
        "type": type_,
        "sender": sender,
        "text": text,
        "timestamp": int(time.time() * 1000)
    }).encode()


# ── Background receiver ────────────────────────────────────────

def receive():
    while True:
        try:
            data = s.recv(RECV_BUFFER)
            if not data:
                print("\n[Server closed the connection]")
                break
            msg = json.loads(data.decode())
            if msg["type"] == "system":
                print(f"\n*** {msg['text']} ***")
            elif msg["type"] == "disconnect":
                print(f"\n*** {msg['text']} ***")
                break
            else:
                print(f"\n[{msg['sender']}]: {msg['text']}")
            print("You: ", end="", flush=True)
        except:
            break


# ── Login ──────────────────────────────────────────────────────

prompt = json.loads(s.recv(RECV_BUFFER).decode())
print(f"Server: {prompt['text']}")
username = input("You: ").strip()
s.send(make_msg("chat", username, username))

threading.Thread(target=receive, daemon=True).start()

print("Commands: /quit to disconnect\n")

# ── Send loop ──────────────────────────────────────────────────

try:
    while True:
        text = input("You: ")
        if not text:
            continue

        if text.strip() == "/quit":
            s.send(make_msg("disconnect", username, "leaving"))
            print("Disconnecting...")
            break

        if len(text) > MAX_MSG_LENGTH:
            print(f"[Message too long — max {MAX_MSG_LENGTH} characters]")
            continue

        s.send(make_msg("chat", username, text))

except KeyboardInterrupt:
    pass

finally:
    s.close()
    print("Disconnected.")