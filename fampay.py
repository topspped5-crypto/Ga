import imaplib, email, re, html, time, threading
from email.utils import parsedate_to_datetime
from email.header import decode_header, make_header
from core import conn, dec, get_setting
from payments import mark_paid

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
AMT = re.compile(r"(?:₹|Rs\.?|INR)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.I)
UTR = re.compile(r"\b(\d{12})\b")
_locks, _last = {}, {}

def test_login(gmail, app_pw):
    try:
        m = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=15)
        m.login(gmail, app_pw.replace(" ", "")); m.logout()
        return True, "Connected to Gmail."
    except imaplib.IMAP4.error:
        return False, "Gmail login failed. Check Gmail, the 16-digit app password, and that IMAP is enabled."
    except Exception as e:
        return False, f"Could not reach Gmail: {e}"

def _text(msg):
    out = []
    for p in msg.walk():
        ct = p.get_content_type()
        if ct not in ("text/plain", "text/html"): continue
        try: s = p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", "replace")
        except Exception: continue
        if ct == "text/html": s = html.unescape(re.sub(r"<[^>]+>", " ", s))
        out.append(s)
    return " ".join(out)

def _paise(s):
    s = s.replace(",", "")
    whole, _, frac = s.partition(".")
    return int(whole) * 100 + int((frac + "00")[:2]) if frac else int(whole) * 100

_conns, _fails = {}, {}

def _get(gid, gmail, pw):
    ent = _conns.get(gid)
    if ent:
        m, t = ent
        if time.time() - t < 20: return m          # fresh connection, no extra round trip
        if time.time() - t < 120:
            try: m.noop(); return m
            except Exception: pass
        try: m.logout()
        except Exception: pass
        _conns.pop(gid, None)
    m = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=12)
    m.login(gmail, pw)
    _conns[gid] = (m, time.time())
    return m

def check_gateway(gid, min_gap=2):
    lock = _locks.setdefault(gid, threading.Lock())
    if not lock.acquire(blocking=False): return
    try:
        gap = min_gap + min(120, _fails.get(gid, 0) * 10)      # back off after errors
        if time.time() - _last.get(gid, 0) < gap: return
        _last[gid] = time.time()
        c = conn()
        now = time.time()
        g = c.execute("SELECT * FROM gateways WHERE id=? AND active=1 AND type='fampay'", (gid,)).fetchone()
        pend = c.execute("SELECT * FROM orders WHERE gateway_id=? AND status='pending' AND expires_ts>?", (gid, now)).fetchall()
        if not g or not pend: c.close(); return
        err = None
        try:
            m = _get(gid, g["gmail"], dec(g["app_pw_enc"]))
            m.select("INBOX", readonly=True)
            since = time.gmtime(min(o["created_ts"] for o in pend) - 86400)
            crit = ["SINCE", f"{since.tm_mday:02d}-{MONTHS[since.tm_mon-1]}-{since.tm_year}"]
            sender = get_setting("fampay_sender").strip()
            if sender: crit += ["FROM", sender]
            last = g["last_uid"] or 0
            if last: crit += ["UID", f"{last+1}:*"]
            typ, data = m.uid("SEARCH", None, *crit)
            uids = sorted(int(x) for x in (data[0].split() if data and data[0] else []))
            uids = [u for u in uids if u > last][-40:]
            kws = [k.strip().lower() for k in get_setting("fampay_keywords").split(",") if k.strip()]
            for u in uids:
                typ, d = m.uid("FETCH", str(u), "(BODY.PEEK[])")
                msg = email.message_from_bytes(d[0][1])
                mid = (msg.get("Message-ID") or str(u)).strip()
                if c.execute("SELECT 1 FROM seen_mail WHERE gateway_id=? AND msgid=?", (gid, mid)).fetchone(): continue
                try: mts = parsedate_to_datetime(msg.get("Date")).timestamp()
                except Exception: mts = now
                subj = str(make_header(decode_header(msg.get("Subject", ""))))
                body = subj + " " + _text(msg)
                low = body.lower()
                if kws and not any(k in low for k in kws): continue
                amts = {_paise(a) for a in AMT.findall(body)[:2]}
                for o in pend:
                    if o["amount"] in amts and o["created_ts"] - 120 <= mts <= o["expires_ts"] + 300:
                        ut = UTR.search(body)
                        if mark_paid(o["id"], ut.group(1) if ut else None):
                            c.execute("INSERT OR IGNORE INTO seen_mail VALUES(?,?)", (gid, mid)); c.commit()
                        break
            if uids:
                c.execute("UPDATE gateways SET last_uid=? WHERE id=?", (max(uids), gid)); c.commit()
            _conns[gid] = (m, time.time()); _fails[gid] = 0
        except imaplib.IMAP4.abort:
            err = None; _conns.pop(gid, None)              # dropped connection: reconnect next tick
        except imaplib.IMAP4.error:
            err = "Gmail login failed (check Gmail / app password / IMAP)."
            _conns.pop(gid, None); _fails[gid] = _fails.get(gid, 0) + 1
        except Exception as e:
            err = f"Check error: {str(e)[:120]}"
            _conns.pop(gid, None); _fails[gid] = _fails.get(gid, 0) + 1
        c.execute("UPDATE gateways SET last_check=?, last_error=? WHERE id=?", (time.time(), err, gid))
        c.commit(); c.close()
    finally:
        lock.release()

def poll_loop():
    while True:
        try:
            c = conn()
            ids = [r[0] for r in c.execute("""SELECT DISTINCT g.id FROM gateways g JOIN orders o ON o.gateway_id=g.id
                   WHERE g.active=1 AND g.type='fampay' AND o.status='pending'""")]
            c.close()
            for gid in ids: check_gateway(gid, min_gap=10)
        except Exception:
            pass
        time.sleep(15)

def start():
    threading.Thread(target=poll_loop, daemon=True).start()
