import time, threading
from concurrent.futures import ThreadPoolExecutor
from core import conn
import fampay, paytm, backup

POOL = ThreadPoolExecutor(max_workers=6)   # at most 6 mailbox/Paytm checks at the same time
_inflight, _lk, _wake = set(), threading.Lock(), threading.Event()

def nudge():
    _wake.set()

def _run(gid, typ):
    try:
        (fampay if typ == "fampay" else paytm).check_gateway(gid)
    except Exception:
        pass
    finally:
        with _lk: _inflight.discard(gid)

def loop():
    n = 0
    while True:
        try:
            c = conn()
            c.execute("UPDATE orders SET status='expired' WHERE status='pending' AND expires_ts<?", (time.time(),)); c.commit()
            rows = c.execute("""SELECT DISTINCT g.id, g.type FROM gateways g JOIN orders o ON o.gateway_id=g.id
                                WHERE g.active=1 AND o.status='pending'""").fetchall()
            c.close()
            for r in rows:
                with _lk:
                    if r["id"] in _inflight: continue
                    _inflight.add(r["id"])
                POOL.submit(_run, r["id"], r["type"])
        except Exception:
            pass
        try:
            if n % 60 == 0: backup.maybe_auto()
        except Exception:
            pass
        n += 1
        _wake.wait(1); _wake.clear()

def start():
    threading.Thread(target=loop, daemon=True).start()
