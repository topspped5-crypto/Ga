import json, base64, hashlib, secrets, string, time, threading, random, datetime
import urllib.request, urllib.parse
from decimal import Decimal
from urllib.parse import quote
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from core import conn, dec, get_setting
from payments import mark_paid

# Paytm auto verification WITHOUT a Merchant Key.
# QR  = plain UPI link (shop name + UPI ID) carrying our unique order id in tr/tn.
# Check = Paytm public merchant-status lookup using only Merchant ID (MID) + order id.
# If an old gateway still has a Merchant Key saved, the signed API is tried first and keyless is the fallback.

IV = b"@@@@&&&&####$$$$"
_locks, _last = {}, {}
UA = {"User-Agent": "Mozilla/5.0"}

def _host():
    return "https://securegw-stage.paytm.in" if get_setting("paytm_env") == "stage" else "https://securegw.paytm.in"

# ---------- optional signed API (only used when a Merchant Key is saved) ----------
def _enc(text, key):
    p = padding.PKCS7(128).padder(); d = p.update(text.encode()) + p.finalize()
    e = Cipher(algorithms.AES(key.encode()), modes.CBC(IV)).encryptor()
    return base64.b64encode(e.update(d) + e.finalize()).decode()

def signature(body_str, key):
    salt = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))
    return _enc(hashlib.sha256((body_str + "|" + salt).encode()).hexdigest() + salt, key)

def _post(path, body, key):
    body_str = json.dumps(body, separators=(",", ":"))
    data = ('{"body":' + body_str + ',"head":{"signature":' + json.dumps(signature(body_str, key)) + '}}').encode()
    req = urllib.request.Request(_host() + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

# ---------- QR (local UPI link, no Paytm API call) ----------
def new_order_id():
    return "PTM" + datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S") + "".join(random.choice(string.digits) for _ in range(4))

def build_upi(upi, shop, amount, order_id):
    return (f"upi://pay?pa={quote(upi)}&pn={quote(shop or 'Shop')}&am={amount}&cu=INR"
            f"&tr={order_id}&tn={quote('Order ' + order_id)}")

# ---------- status ----------
_NOT_FOUND = {"334", "335", "400", "401", "402", "810", "501", "1"}   # order simply does not exist yet = not paid

def _state(st, code, has_txn):
    if st == "TXN_SUCCESS": return "SUCCESS"
    if st == "TXN_FAILURE" and has_txn and str(code) not in _NOT_FOUND: return "FAILED"
    return "PENDING"

def _paise(v):
    try: return int((Decimal(str(v)) * 100).to_integral_value())
    except Exception: return 0

def status_keyless(mid, order_id):
    q = json.dumps({"MID": mid, "ORDERID": order_id}, separators=(",", ":"))
    url = "https://securegw.paytm.in/merchant-status/getTxnStatus?" + urllib.parse.urlencode({"JsonData": q})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=10) as r:
        return json.loads(r.read().decode())

def fetch_status(mid, key, order_id):
    """Returns {state, order_id, amount (paise), txn_id}."""
    if key:
        try:
            b = _post("/v3/order/status", {"mid": mid, "orderId": order_id}, key).get("body", {})
            i = b.get("resultInfo", {})
            return {"state": _state(i.get("resultStatus", ""), i.get("resultCode", ""), bool(b.get("txnId"))),
                    "order_id": b.get("orderId"), "amount": _paise(b.get("txnAmount")),
                    "txn_id": str(b.get("bankTxnId") or b.get("txnId") or "")}
        except Exception:
            pass   # fall through to keyless
    b = status_keyless(mid, order_id)
    txn = str(b.get("BANKTXNID") or b.get("TXNID") or "")
    return {"state": _state(str(b.get("STATUS", "")), b.get("RESPCODE", ""), bool(txn)),
            "order_id": b.get("ORDERID"), "amount": _paise(b.get("TXNAMOUNT")), "txn_id": txn}

def test_creds(mid, key=None):
    """Setup check only. The Rs 1 test order proves payments really work."""
    if not mid: return False, "Merchant ID is required."
    try:
        b = status_keyless(mid, "TESTCONN" + secrets.token_hex(4))
    except Exception as e:
        return False, f"Could not reach Paytm: {str(e)[:100]}"
    return True, f"Connected to Paytm (reply: {b.get('RESPCODE', '')} {str(b.get('RESPMSG', ''))[:60]}). Create the Rs 1 test order to confirm."

# ---------- background check ----------
def check_gateway(gid, min_gap=2.0):
    lock = _locks.setdefault(gid, threading.Lock())
    if not lock.acquire(blocking=False): return
    try:
        if time.time() - _last.get(gid, 0) < min_gap: return
        _last[gid] = time.time()
        c = conn()
        g = c.execute("SELECT * FROM gateways WHERE id=? AND active=1 AND type='paytm'", (gid,)).fetchone()
        pend = c.execute("SELECT * FROM orders WHERE gateway_id=? AND status='pending' AND expires_ts>? ORDER BY created_ts DESC LIMIT 20",
                         (gid, time.time())).fetchall()
        if not g or not pend: c.close(); return
        key = None
        if g["key_enc"]:
            try: key = dec(g["key_enc"])
            except Exception: key = None
        err = None
        for o in pend:
            try:
                s = fetch_status(g["mid"], key, o["pt_order"])
                if s["state"] != "SUCCESS": continue
                if s["order_id"] and str(s["order_id"]) != o["pt_order"]: continue
                if s["amount"] == o["amount"]: mark_paid(o["id"], s["txn_id"] or None)
                else: err = f"Amount mismatch on {o['pt_order']}: paid {s['amount']/100:.2f}, expected {o['amount']/100:.2f}"
            except Exception as e:
                err = f"Paytm check error: {str(e)[:100]}"
        c.execute("UPDATE gateways SET last_check=?, last_error=? WHERE id=?", (time.time(), err, gid)); c.commit(); c.close()
    finally:
        lock.release()
