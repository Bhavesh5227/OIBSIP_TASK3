# PyChat 💬

A real-time chat application built from scratch in Python — starting from raw TCP sockets all the way up to a full WebSocket server with a browser-based GUI, authentication, encryption, and emoji support.

> Built as part of the OIBSIP Internship Program — Task 3

---

## 📁 Project Structure

```
TASK3/
├── client/
│   ├── client_basic.py      # Task 1 & 2 — raw TCP socket client
│   └── client_main.py       # Task 3+ — JSON protocol client with threading
├── server/
│   ├── server_basic.py      # Task 1 & 2 — raw TCP socket server
│   └── server_main.py       # Task 3+ — JSON protocol server with auth & rooms
├── interface/
│   └── index.html           # Task 7 — browser-based chat GUI
├── main.py                  # Project launcher — menu to start any version
└── requirements.txt         # Python dependencies
```

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/your-username/pychat.git
cd pychat
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run via launcher

```bash
python main.py
```

Pick option `1` in one terminal (server), then option `2` in another (client).

---

## 🏗️ How It Was Built — Task by Task

This project was built progressively. Each task solves a limitation of the previous one.

### Task 1 — Raw TCP Echo Server
**Files:** `server_basic.py`, `client_basic.py`

The foundation. One server, one client. Client sends a message, server echoes it back.

**Concepts learned:**
- `socket()`, `bind()`, `listen()`, `accept()`, `send()`, `recv()`
- How TCP connections work at the byte level
- Blocking I/O — why `recv()` freezes the program

```bash
# Terminal 1
python server/server_basic.py

# Terminal 2
python client/client_basic.py
```

---

### Task 2 — Multi-Client with Threads
**Files:** `server_basic.py`, `client_basic.py` (updated)

Multiple clients connect simultaneously. Each gets its own thread on the server. The client also gets a background receive thread so it can type and receive at the same time.

**Concepts learned:**
- `threading.Thread` — one thread per connected client
- Why you need two threads on the client (send vs receive)
- `threading.Lock` — protecting shared state (`clients` dict)
- Direct messaging with `@username message` format

```
Client sends:  @bob hey
Server routes: only to bob's socket
Carol:         sees nothing
```

---

### Task 3 — JSON Message Protocol
**Files:** `server_main.py`, `client_main.py`

Raw bytes replaced with structured JSON envelopes. Every message now has a `type`, `sender`, `text`, and `timestamp`.

**Concepts learned:**
- Protocol design — why structured messages matter
- `json.dumps()` / `json.loads()` over sockets
- Message types: `chat`, `system`, `disconnect`
- Using `type` to render messages differently on the client

```python
# Every message looks like this
{
    "type": "chat",
    "sender": "alice",
    "text": "hello!",
    "timestamp": 1700000000000
}
```

**Server commands:**
```
/stop   → shut down server, notify all clients
/list   → show connected usernames
/help   → show available commands
```

**Client commands:**
```
/quit   → disconnect cleanly from server
```

---

## ⚙️ Running Each Version

### Basic version (Tasks 1–2)

```bash
# Terminal 1 — server
python server/server_basic.py

# Terminal 2 — client 1
python client/client_basic.py

# Terminal 3 — client 2
python client/client_basic.py
```

### Main version (Tasks 3+)

```bash
# Terminal 1 — server
python server/server_main.py

# Terminal 2 — client 1
python client/client_main.py

# Terminal 3 — client 2
python client/client_main.py
```

### Via launcher

```bash
python main.py
```

```
=== PyChat ===
─── Basic (Tasks 1-2) ───
1. Start basic server
2. Start basic client
─── Main (Tasks 3+) ─────
3. Start main server
4. Start main client
─────────────────────────
5. Exit
```

---

## 📡 Message Protocol

All messages between client and server are JSON objects.

| Field | Type | Description |
|---|---|---|
| `type` | string | `chat`, `system`, `disconnect` |
| `sender` | string | Username of sender |
| `text` | string | Message content |
| `timestamp` | int | Unix time in milliseconds |

### Client → Server

| Type | Meaning |
|---|---|
| `chat` | Regular message |
| `disconnect` | Client is leaving cleanly |

### Server → Client

| Type | Meaning |
|---|---|
| `chat` | Message from another user |
| `system` | Join/leave notification |
| `disconnect` | Server shutting down |

---

## 📦 Dependencies

```
websockets>=12.0
bcrypt>=4.0
cryptography>=41.0
```

Install with:
```bash
pip install -r requirements.txt
```

Standard library used (no install needed): `socket`, `threading`, `json`, `time`, `signal`, `sys`

---

## 🗺️ Roadmap

| Task | Feature | Status |
|---|---|---|
| 1 | Raw TCP echo server | ✅ Done |
| 2 | Multi-client threading + DMs | ✅ Done |
| 3 | JSON message protocol + /quit /stop | ✅ Done |
| 4 | Chat rooms (scoped broadcast) | ✅ Done  |
| 5 | User authentication (bcrypt + tokens) | ✅ Done  |
| 6 | Message encryption (AES via Fernet) | ⏳ Planned |
| 7 | WebSocket server + browser GUI | ✅ Done  |

---

## 🧠 Key Concepts Covered

- **TCP socket programming** — raw socket API from scratch
- **Concurrency** — threading model, one thread per client
- **Race conditions** — why `threading.Lock` is needed on shared dicts
- **Protocol design** — structured JSON over raw bytes
- **Clean disconnection** — `/quit` vs abrupt socket close
- **Server lifecycle** — graceful shutdown with `signal.SIGINT`

---

## 👤 Author

**Bhavesh** — [GitHub](https://github.com/Bhavesh5227)

Built as part of OIBSIP (Oasis Infobyte Internship Program) — Task 3

---

## 📄 License

MIT License — free to use, modify, and distribute.