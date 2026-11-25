import os, time, sqlite3, secrets, json, urllib.request
from datetime import datetime
from core import DATA_DIR, conn, get_setting, set_setting

BK = os.path.join(DATA_DIR, "backups")

def make_backup():
    os.makedirs(BK, exist_ok=True)
    p = os.path.join(BK, f"gateway-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db")
    src = conn(); dst = sqlite3.connect(p); src.backup(dst); dst.close(); src.close()
    for f in sorted(x for x in os.listdir(BK) if x.endswith(".db"))[:-10]:
        os.remove(os.path.join(BK, f))
    return p

def send_telegram(path):
    tok, chat = get_setting("tg_token").strip(), get_setting("tg_chat").strip()
    if not tok or not chat: return False, "Telegram not set"
    b = "----gw" + secrets.token_hex(8)
    def part(name, val): return f'--{b}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{val}\r\n'.encode()
    body = part("chat_id", chat) + part("caption", "Gateway backup " + datetime.now().strftime("%d %b %Y %H:%M"))
    body += (f'--{b}\r\nContent-Disposition: form-data; name="document"; filename="{os.path.basename(path)}"\r\n'
             f'Content-Type: application/octet-stream\r\n\r\n').encode() + open(path, "rb").read() + f"\r\n--{b}--\r\n".encode()
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendDocument", data=body,
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
        r = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
        return bool(r.get("ok")), "Sent to Telegram" if r.get("ok") else str(r.get("description"))
    except Exception as e:
        return False, f"Telegram error: {str(e)[:100]}"

def run_backup():
    p = make_backup(); ok, msg = send_telegram(p)
    set_setting("last_backup", str(time.time()))
    set_setting("last_backup_msg", ("Saved locally. " + msg))
    return ok, msg

def maybe_auto():
    c = conn()
    has_users = c.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    c.execute("DELETE FROM orders WHERE status='expired' AND expires_ts<?", (time.time() - 14 * 86400,)); c.commit(); c.close()
    if not has_users: return
    if time.time() - float(get_setting("last_backup") or 0) >= 12 * 3600:
        run_backup()
