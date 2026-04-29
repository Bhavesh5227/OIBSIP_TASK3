# config/settings.py — central config for all versions of PyChat

# ── Network ────────────────────────────────────────────────────
HOST        = "localhost"
PORT_BASIC  = 9999   # server_basic.py / client_basic.py  (Tasks 1-2)
PORT_MAIN   = 9998   # server_main.py  / client_main.py   (Tasks 3+)
PORT_WS     = 8765   # WebSocket server                   (Task 7)
PORT_HTTP   = 8080   # HTTP server serving index.html     (Task 7)

# ── Chat ───────────────────────────────────────────────────────
MAX_CLIENTS     = 10
MAX_MSG_LENGTH  = 2000
MAX_HISTORY     = 100      # messages stored per room
RECV_BUFFER     = 4096     # bytes per recv() call

# ── Auth (Task 5) ──────────────────────────────────────────────
TOKEN_LENGTH      = 32     # bytes of randomness in session token
MIN_USERNAME_LEN  = 3
MAX_USERNAME_LEN  = 20
MIN_PASSWORD_LEN  = 6

# ── Rooms (Task 4) ─────────────────────────────────────────────
DEFAULT_ROOMS = {
    "general": "General chat",
    "tech":    "Tech talk",
    "random":  "Off-topic fun",
}

# ── Timeouts ───────────────────────────────────────────────────
PING_INTERVAL  = 25        # seconds between keepalive pings
TYPING_TIMEOUT = 2         # seconds before typing indicator clears