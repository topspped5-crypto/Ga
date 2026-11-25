import json, hmac, hashlib, threading, time, socket, ipaddress, urllib.request
from urllib.parse import urlparse
from core import conn

def safe_url(u):
    try:
        p = urlparse(u)
        if p.scheme not in ("http", "https") or not p.hostname: return False
        for info in socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80)):
            a = ipaddress.ip_address(info[4][0])
            if a.is_private or a.is_loopback or a.is_link_local or a.is_reserved or a.is_multicast: return False
        return True
    except Exception:
        return False

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None

def _send(oid):
    c = conn()
    o = c.execute("SELECT o.*, g.api_key FROM orders o JOIN gateways g ON g.id=o.gateway_id WHERE o.id=?", (oid,)).fetchone()
    if not o or not o["webhook_url"]: c.close(); return
    body = json.dumps({"event": "payment.success", "order_id": o["id"], "ref": o["ref"],
                       "amount": f"{o['amount']/100:.2f}", "status": "paid", "utr": o["utr"],
                       "paid_at": int(o["paid_ts"] or time.time())}).encode()
    sig = hmac.new(o["api_key"].encode(), body, hashlib.sha256).hexdigest()
    status = "failed"
    for wait in (0, 2, 6, 15):
        time.sleep(wait)
        try:
            if not safe_url(o["webhook_url"]): status = "blocked"; break
            req = urllib.request.Request(o["webhook_url"], data=body, headers={
                "Content-Type": "application/json", "X-Signature": sig, "User-Agent": "PayGateway/1"})
            with urllib.request.build_opener(_NoRedirect).open(req, timeout=10) as r:
                if 200 <= r.status < 300: status = "sent"; break
        except Exception:
            continue
    c.execute("UPDATE orders SET webhook_status=? WHERE id=?", (status, oid)); c.commit(); c.close()

def mark_paid(oid, utr=None):
    c = conn()
    cur = c.execute("UPDATE orders SET status='paid', paid_ts=?, utr=? WHERE id=? AND status='pending'",
                    (time.time(), utr, oid))
    c.commit(); c.close()
    if cur.rowcount:
        threading.Thread(target=_send, args=(oid,), daemon=True).start()
        return True
    return False
