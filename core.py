import os, sqlite3, secrets, hmac, hashlib, base64
from datetime import datetime, timezone, timedelta

DATA_DIR = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "gateway.db")

def _secret():
    s = os.environ.get("SECRET_KEY")
    if s: return s
    import time
    p = os.path.join(DATA_DIR, ".secret")
    if not os.path.exists(p):
        try:   # atomic create: several workers starting together must end up with the SAME key
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.write(fd, secrets.token_hex(32).encode()); os.close(fd)
        except FileExistsError:
            pass
    for _ in range(30):
        v = open(p).read().strip()
        if v: return v
        time.sleep(0.1)
    return secrets.token_hex(32)
SECRET = _secret()

DEFAULTS = {"fampay_sender": "famapp.in", "fampay_keywords": "received,credited",
            "order_expiry_min": "5", "base_url": "", "paytm_env": "prod",
            "tg_token": "", "tg_chat": "", "last_backup": "0", "last_backup_msg": ""}

def conn():
    c = sqlite3.connect(DB_PATH, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=5000")
    c.execute("PRAGMA synchronous=NORMAL")
    return c

def init_db():
    c = conn()
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL, phone TEXT NOT NULL, email TEXT NOT NULL,
        banned INTEGER DEFAULT 0, created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS gateways(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, type TEXT NOT NULL,
        name TEXT NOT NULL, upi_id TEXT NOT NULL, gmail TEXT, app_pw_enc TEXT,
        api_key TEXT UNIQUE NOT NULL, active INTEGER DEFAULT 1,
        last_check REAL, last_error TEXT, created REAL NOT NULL);
    CREATE TABLE IF NOT EXISTS orders(
        id TEXT PRIMARY KEY, gateway_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL, base_amount INTEGER NOT NULL, ref TEXT, webhook_url TEXT,
        redirect_url TEXT, status TEXT NOT NULL, created_ts REAL NOT NULL, expires_ts REAL NOT NULL,
        paid_ts REAL, utr TEXT, webhook_status TEXT);
    CREATE INDEX IF NOT EXISTS ix_orders_gw ON orders(gateway_id, status);
    CREATE INDEX IF NOT EXISTS ix_orders_created ON orders(created_ts DESC);
    CREATE INDEX IF NOT EXISTS ix_orders_user_created ON orders(user_id, created_ts DESC);
    CREATE INDEX IF NOT EXISTS ix_gateways_user ON gateways(user_id, id DESC);
    CREATE TABLE IF NOT EXISTS seen_mail(gateway_id INTEGER, msgid TEXT, PRIMARY KEY(gateway_id,msgid));
    CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
    """)
    def addcol(t, col, typ):
        if col not in [r[1] for r in c.execute(f"PRAGMA table_info({t})")]:
            c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {typ}")
    addcol("gateways", "mid", "TEXT"); addcol("gateways", "key_enc", "TEXT")
    addcol("gateways", "last_uid", "INTEGER DEFAULT 0"); addcol("orders", "cancel_url", "TEXT"); addcol("orders", "qr_data", "TEXT"); addcol("orders", "pt_order", "TEXT")
    # one-time: force the 5-minute QR expiry even if an older value was saved
    if not c.execute("SELECT 1 FROM settings WHERE k='mig_expiry5'").fetchone():
        c.execute("INSERT OR REPLACE INTO settings(k,v) VALUES('order_expiry_min','5')")
        c.execute("INSERT OR REPLACE INTO settings(k,v) VALUES('mig_expiry5','1')")
    c.commit(); c.close()
init_db()

def get_setting(k):
    c = conn(); r = c.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone(); c.close()
    return r["v"] if r else DEFAULTS.get(k, "")

def set_setting(k, v):
    c = conn(); c.execute("INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)", (k, v)); c.commit(); c.close()

# --- encryption for stored Gmail app passwords (stdlib only) ---
def _key(): return hashlib.sha256(b"gw-enc|" + SECRET.encode()).digest()
def _stream(nonce, n):
    out = b""; i = 0
    while len(out) < n:
        out += hashlib.sha256(_key() + nonce + i.to_bytes(4, "big")).digest(); i += 1
    return out[:n]
def enc(text):
    nonce = os.urandom(16); data = text.encode()
    ct = bytes(a ^ b for a, b in zip(data, _stream(nonce, len(data))))
    tag = hmac.new(_key(), nonce + ct, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + ct + tag).decode()
def dec(token):
    raw = base64.urlsafe_b64decode(token.encode())
    nonce, ct, tag = raw[:16], raw[16:-32], raw[-32:]
    if not hmac.compare_digest(tag, hmac.new(_key(), nonce + ct, hashlib.sha256).digest()):
        raise ValueError("bad key")
    return bytes(a ^ b for a, b in zip(ct, _stream(nonce, len(ct)))).decode()

IST = timezone(timedelta(hours=5, minutes=30))
def ist(ts):
    return datetime.fromtimestamp(ts, IST).strftime("%d %b %H:%M") if ts else "-"
def money(p): return f"{p / 100:.2f}"
