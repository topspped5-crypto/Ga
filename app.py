import os, re, sqlite3, secrets, time, tempfile
from functools import wraps
from datetime import datetime, timezone
from flask import (Flask, request, session, redirect, render_template, g, flash,
                   send_file, abort)
from jinja2 import DictLoader
from werkzeug.security import generate_password_hash, check_password_hash
from templates_ui import TEMPLATES

from werkzeug.middleware.proxy_fix import ProxyFix
from core import (dec, DATA_DIR, DB_PATH, SECRET, conn, init_db, get_setting, set_setting, enc, DEFAULTS, ist, money)
from templates_gw import TEMPLATES_GW
import fampay, payments, paytm, worker, backup
import json, threading, logging, urllib.request, urllib.error, io
from decimal import Decimal, InvalidOperation
from urllib.parse import quote
from flask import jsonify, Response

ADMIN_ACCOUNTS = [("rgcheat", "909090")]
if os.environ.get("ADMIN_USERNAME") and os.environ.get("ADMIN_PASSWORD"):
    ADMIN_ACCOUNTS.append((os.environ["ADMIN_USERNAME"].strip().lower(), os.environ["ADMIN_PASSWORD"]))

def is_admin_cred(u, p):
    u = (u or "").strip().lower().encode(); p = (p or "").strip().encode(); ok = False
    for au, ap in ADMIN_ACCOUNTS:
        if secrets.compare_digest(u, au.encode()) and secrets.compare_digest(p, ap.strip().encode()): ok = True
    return ok

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.jinja_loader = DictLoader({**TEMPLATES, **TEMPLATES_GW})
app.jinja_env.globals.update(money=money, ist=ist)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
                  MAX_CONTENT_LENGTH=50 * 1024 * 1024)
app.secret_key = SECRET

# Single-owner mode: one protected account controls every merchant feature.
def ensure_owner():
    c = conn()
    row = c.execute("SELECT * FROM users WHERE username='__owner__' COLLATE NOCASE").fetchone()
    if not row:
        c.execute("INSERT INTO users(username,password_hash,phone,email,banned,created) VALUES(?,?,?,?,0,?)",
                  ('__owner__', generate_password_hash(secrets.token_urlsafe(32)), '0000000000', 'owner@localhost', datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')))
        c.commit()
        row = c.execute("SELECT * FROM users WHERE username='__owner__' COLLATE NOCASE").fetchone()
    c.close()
    return row['id']

OWNER_ID = ensure_owner()

def db():
    if "db" not in g:
        g.db = conn()
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

# ---------- security helpers ----------
@app.before_request
def csrf_guard():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    if request.method == "POST" and not request.path.startswith("/api/"):
        if not secrets.compare_digest(request.form.get("csrf", ""), session["csrf"]):
            if request.path in ("/login", "/signup", "/admin/login"):
                flash("Session expired. Please try again.", "warn"); return redirect(request.path)
            abort(400, "Bad CSRF token. Reload the page.")

@app.after_request
def headers(r):
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["X-Content-Type-Options"] = "nosniff"
    if r.mimetype == "text/html": r.headers["Cache-Control"] = "no-store"
    return r

@app.errorhandler(500)
def internal_server_error(error):
    app.logger.exception("Unhandled server error", exc_info=error)
    return render_template("error.html"), 500

_attempts = {}
def throttled(key, limit=8, window=300):
    t = time.time()
    a = [x for x in _attempts.get(key, []) if t - x < window]
    _attempts[key] = a
    return len(a) >= limit
def fail(key): _attempts.setdefault(key, []).append(time.time())

def ip(): return request.remote_addr or ""

def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("admin"):
            return redirect("/login")
        u = db().execute("SELECT * FROM users WHERE id=?", (OWNER_ID,)).fetchone()
        if not u:
            abort(503, "Owner account is not initialized")
        g.user = u
        return f(*a, **k)
    return w

def admin_required(f):
    return login_required(f)

# ---------- user routes ----------
@app.route("/")
def index():
    return redirect("/admin" if session.get("admin") else "/login")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin"):
        return redirect("/admin")
    if request.method == "POST":
        un = request.form.get("username", "").strip()
        raw = request.form.get("password", "")
        k = "owner:%s" % ip()
        if throttled(k, 5):
            flash("Too many attempts. Try again in a few minutes.", "err")
        elif is_admin_cred(un, raw):
            _attempts.pop(k, None)
            session.clear(); session["admin"] = True; session["csrf"] = secrets.token_hex(16)
            return redirect("/admin")
        else:
            fail(k); flash("Wrong owner username or password.", "err")
    return render_template("auth.html", mode="login", csrf=session["csrf"])

@app.route("/logout")
def logout():
    session.clear(); return redirect("/login")

@app.route("/dashboard")
@login_required
def dashboard():
    return redirect("/admin")

@app.route("/gateways")
@login_required
def gateways_page():
    gws = db().execute("SELECT * FROM gateways ORDER BY id DESC").fetchall()
    return render_template("gateways.html", gws=gws)

@app.route("/gateway/new")
@login_required
def gateway_new():
    return render_template("gateway_new.html", csrf=session["csrf"])

@app.route("/account")
@login_required
def account():
    return render_template("account.html", u=g.user, csrf=session["csrf"])

@app.route("/change-password", methods=["POST"])
@login_required
def change_password():
    if not check_password_hash(g.user["password_hash"], request.form.get("old", "")):
        flash("Current password is wrong.", "err")
    elif len(request.form.get("new", "")) < 6: flash("New password too short.", "err")
    else:
        db().execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(request.form["new"]), g.user["id"]))
        db().commit(); flash("Password updated.", "ok")
    return redirect("/account")

# ---------- admin routes ----------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    return redirect("/login")

@app.route("/admin/logout")
def admin_logout():
    session.clear(); return redirect("/login")

@app.route("/admin/users")
@admin_required
def admin_users():
    q = request.args.get("q", "").strip()
    like = f"%{q}%"
    rows = db().execute("SELECT * FROM users WHERE username LIKE ? OR phone LIKE ? OR email LIKE ? ORDER BY id DESC",
                        (like, like, like)).fetchall()
    t = db().execute("SELECT COUNT(*) c, SUM(banned) b FROM users").fetchone()
    stats = {"total": t["c"], "banned": t["b"] or 0, "active": t["c"] - (t["b"] or 0)}
    return render_template("admin_users.html", users=rows, q=q, stats=stats, csrf=session["csrf"])

@app.route("/admin/user/<int:uid>/update", methods=["POST"])
@admin_required
def admin_update(uid):
    ph = re.sub(r"[^\d+]", "", request.form.get("phone", "")); em = request.form.get("email", "").strip().lower()
    db().execute("UPDATE users SET phone=?, email=? WHERE id=?", (ph, em, uid)); db().commit()
    flash("User updated.", "ok"); return redirect("/admin/users")

@app.route("/admin/user/<int:uid>/password", methods=["POST"])
@admin_required
def admin_password(uid):
    pw = request.form.get("password", "").strip() or secrets.token_urlsafe(7)
    if len(pw) < 6: flash("Password must be at least 6 characters.", "err"); return redirect("/admin/users")
    db().execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(pw), uid)); db().commit()
    flash(f"New password for user #{uid}: {pw}  (shown once, give it to the user)", "ok"); return redirect("/admin/users")

@app.route("/admin/user/<int:uid>/toggle", methods=["POST"])
@admin_required
def admin_toggle(uid):
    db().execute("UPDATE users SET banned=1-banned WHERE id=?", (uid,)); db().commit(); return redirect("/admin/users")

@app.route("/admin/user/<int:uid>/delete", methods=["POST"])
@admin_required
def admin_delete(uid):
    db().execute("DELETE FROM users WHERE id=?", (uid,)); db().commit()
    flash("User deleted.", "ok"); return redirect("/admin/users")

@app.route("/admin/backup")
@admin_required
def backup_download():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db"); tmp.close()
    dst = sqlite3.connect(tmp.name); db().backup(dst); dst.close()
    return send_file(tmp.name, as_attachment=True, download_name=f"gateway-backup-{datetime.now().strftime('%Y%m%d-%H%M')}.db")

@app.route("/admin/restore", methods=["POST"])
@admin_required
def restore():
    f = request.files.get("file")
    if not f: flash("Choose a backup file.", "err"); return redirect("/admin/settings")
    tmp = os.path.join(DATA_DIR, "restore.tmp"); f.save(tmp)
    try:
        s = sqlite3.connect(tmp); s.execute("SELECT id,username,password_hash FROM users LIMIT 1"); 
        d = sqlite3.connect(DB_PATH); s.backup(d); d.close(); s.close()
        init_db(); flash("Backup restored.", "ok")
    except Exception:
        flash("Invalid backup file.", "err")
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    return redirect("/admin/settings")


# ---------- gateways (user) ----------
def own_gateway(gid):
    gw = db().execute("SELECT * FROM gateways WHERE id=?", (gid,)).fetchone()
    if not gw: abort(404)
    return gw

def base_url():
    return (get_setting("base_url").strip().rstrip("/")) or request.url_root.rstrip("/")

@app.route("/gateway/add", methods=["POST"])
@login_required
def gateway_add():
    f = request.form; typ = f.get("type", "fampay")
    name = f.get("name", "").strip()[:40]; upi = f.get("upi_id", "").strip()
    n = db().execute("SELECT COUNT(*) FROM gateways").fetchone()[0]
    vals = dict(gmail=None, pw=None, mid=None, key=None)
    err = None
    if not name: err = "Enter a gateway name."
    elif not re.fullmatch(r"[\w.\-]{2,}@[A-Za-z0-9]{2,}", upi): err = "Enter a valid UPI ID."
    elif n >= 5: err = "Gateway limit reached (5)."
    elif typ == "fampay":
        gm = f.get("gmail", "").strip().lower(); pw = re.sub(r"\s", "", f.get("app_password", ""))
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", gm): err = "Enter a valid Gmail."
        elif not re.fullmatch(r"[A-Za-z0-9]{16}", pw): err = "The app password must be 16 letters/digits."
        else:
            ok, msg = fampay.test_login(gm, pw)
            if not ok: err = msg
            vals.update(gmail=gm, pw=enc(pw))
    elif typ == "paytm":
        mid = f.get("mid", "").strip()
        if not re.fullmatch(r"[A-Za-z0-9@_.\-]{6,40}", mid): err = "Enter a valid Merchant ID."
        else:
            ok, msg = paytm.test_creds(mid)
            if not ok: err = msg
            vals.update(mid=mid)
    else: err = "Unknown gateway type."
    if err:
        flash(err, "err"); return redirect("/gateway/new")
    cur = db().execute("INSERT INTO gateways(user_id,type,name,upi_id,gmail,app_pw_enc,mid,key_enc,api_key,webhook_secret,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (g.user["id"], typ, name, upi, vals["gmail"], vals["pw"], vals["mid"], vals["key"], "gw_" + secrets.token_urlsafe(24), secrets.token_urlsafe(32), time.time()))
    db().commit(); flash("Gateway created and verified.", "ok")
    return redirect(f"/gateway/{cur.lastrowid}")

@app.route("/gateway/<int:gid>")
@login_required
def gateway_view(gid):
    gw = own_gateway(gid)
    orders = db().execute("SELECT * FROM orders WHERE gateway_id=? ORDER BY created_ts DESC LIMIT 30", (gid,)).fetchall()
    return render_template("gateway.html", gw=gw, orders=orders, last=ist(gw["last_check"]), base=base_url(), csrf=session["csrf"])

@app.route("/gateway/<int:gid>/<action>", methods=["POST"])
@login_required
def gateway_action(gid, action):
    gw = own_gateway(gid)
    if action == "test":
        try:
            if gw["type"] == "fampay": ok, msg = fampay.test_login(gw["gmail"], dec(gw["app_pw_enc"]))
            else: ok, msg = paytm.test_creds(gw["mid"], dec(gw["key_enc"]) if gw["key_enc"] else None)
        except Exception: ok, msg = False, "Stored secret cannot be read (SECRET_KEY changed?). Delete and re-add the gateway."
        flash(msg, "ok" if ok else "err")
    elif action == "toggle":
        db().execute("UPDATE gateways SET active=1-active WHERE id=?", (gid,)); db().commit()
    elif action == "regen":
        db().execute("UPDATE gateways SET api_key=? WHERE id=?", ("gw_" + secrets.token_urlsafe(24), gid)); db().commit()
        flash("New API key generated. Update it in your bot/site.", "ok")
    elif action == "delete":
        db().execute("DELETE FROM orders WHERE gateway_id=?", (gid,)); db().execute("DELETE FROM seen_mail WHERE gateway_id=?", (gid,))
        db().execute("DELETE FROM gateways WHERE id=?", (gid,)); db().commit()
        flash("Gateway deleted.", "ok"); return redirect("/gateways")
    elif action == "test-order":
        if not gw["active"]: flash("Turn the gateway on first.", "err")
        else:
            o, err = make_order(gw, Decimal("1"), "test", None, None)
            if err: flash(err, "err")
            else: return redirect("/pay/" + o)
    return redirect(f"/gateway/{gid}")

# ---------- orders / API ----------
def make_order(gw, amount, ref, webhook, redirect_url, cancel_url=None):
    c = db()
    base = int((amount * 100).to_integral_value())
    pend = {r[0] for r in c.execute("SELECT amount FROM orders WHERE gateway_id=? AND status='pending' AND expires_ts>?", (gw["id"], time.time()))}
    if len(pend) >= 300: return None, "Too many pending orders"
    oid = secrets.token_hex(12); t = time.time(); qr = pt = None
    if gw["type"] == "paytm":
        amt = base; pt = paytm.new_order_id()
        qr = paytm.build_upi(gw["upi_id"], gw["name"], money(amt), pt)
    else:
        amt = next((base + i for i in range(60) if base + i not in pend), None)
        if amt is None: return None, "Too many pending orders for this amount"
    exp = int(get_setting("order_expiry_min") or 5) * 60
    c.execute("INSERT INTO orders(id,gateway_id,user_id,amount,base_amount,ref,webhook_url,redirect_url,status,created_ts,expires_ts,qr_data,pt_order,cancel_url) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
              (oid, gw["id"], gw["user_id"], amt, base, ref, webhook, redirect_url, "pending", t, t + exp, qr, pt, cancel_url))
    c.commit()
    worker.nudge()
    return oid, None

def api_gateway(gateway_type=None):
    data = request.get_json(silent=True) or {}
    auth = request.headers.get("Authorization", "")
    bearer = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    key = request.headers.get("X-API-Key") or bearer or request.values.get("api_key") or data.get("api_key", "")
    sql = "SELECT g.* FROM gateways g JOIN users u ON u.id=g.user_id WHERE g.api_key=? AND g.active=1 AND u.banned=0"
    args = [key]
    if gateway_type in ("paytm", "fampay"):
        sql += " AND g.type=?"; args.append(gateway_type)
    return db().execute(sql, args).fetchone() if key else None


def _api_error(message, status):
    return jsonify(success=False, error=message), status


def _api_qr(oid, png=True):
    o = db().execute("SELECT o.*,g.name,g.upi_id FROM orders o JOIN gateways g ON g.id=o.gateway_id WHERE o.id=?", (oid,)).fetchone()
    if not o: abort(404)
    upi = o["qr_data"] or f"upi://pay?pa={quote(o['upi_id'])}&pn={quote(o['name'])}&am={money(o['amount'])}&cu=INR&tn={quote('Order '+oid[:8])}"
    try:
        import qrcode
        if png:
            img = qrcode.make(upi); b = io.BytesIO(); img.save(b, format="PNG")
            return Response(b.getvalue(), mimetype="image/png", headers={"Cache-Control":"no-store"})
        import qrcode.image.svg
        img = qrcode.make(upi, image_factory=qrcode.image.svg.SvgPathImage)
        b = io.BytesIO(); img.save(b)
        return Response(b.getvalue(), mimetype="image/svg+xml", headers={"Cache-Control":"no-store"})
    except Exception:
        return jsonify(success=False, error="QR image support unavailable; use upi_uri"), 503


@app.route("/api/v1/payment/create", methods=["POST"])
def api_v1_payment_create():
    d = request.get_json(silent=True) or request.form
    gateway_type = str(d.get("gateway", "")).strip().lower()
    if gateway_type not in ("paytm", "fampay"):
        return _api_error("gateway must be paytm or fampay", 400)
    gw = api_gateway(gateway_type)
    if not gw: return _api_error("invalid API key, inactive gateway, or gateway not configured", 401)
    if throttled("apiv1:%s" % gw["id"], 60, 60): return _api_error("rate limit (60/min)", 429)
    fail("apiv1:%s" % gw["id"])
    try: amount = Decimal(str(d.get("amount", ""))).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError): return _api_error("invalid amount", 400)
    if not (Decimal("1") <= amount <= Decimal("100000")): return _api_error("amount must be 1 to 100000", 400)
    client_oid = str(d.get("order_id") or "").strip()[:100]
    if client_oid and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", client_oid): return _api_error("invalid order_id", 400)
    # Idempotency: retrying the same merchant order_id returns the original payment.
    if client_oid:
        old = db().execute("SELECT id FROM orders WHERE gateway_id=? AND client_order_id=?", (gw["id"], client_oid)).fetchone()
        if old:
            o = db().execute("SELECT * FROM orders WHERE id=?", (old["id"],)).fetchone()
            if o:
                return _api_payment_payload(o, gw, client_oid)
    wh = (d.get("webhook_url") or "").strip() or None
    if wh and not payments.safe_url(wh): return _api_error("webhook_url must be a public http(s) URL", 400)
    oid, err = make_order(gw, amount, client_oid or None, wh, None)
    if err: return _api_error(err, 502 if str(err).lower().startswith("paytm") else 429)
    db().execute("UPDATE orders SET api_v1=1, client_order_id=? WHERE id=?", (client_oid or oid, oid)); db().commit()
    o = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    return _api_payment_payload(o, gw, client_oid or oid)


def _api_payment_payload(o, gw, client_oid):
    oid = o["id"]
    upi = o["qr_data"] or f"upi://pay?pa={quote(gw['upi_id'])}&pn={quote(gw['name'])}&am={money(o['amount'])}&cu=INR&tr={quote(o['pt_order'] or oid)}&tn={quote('Order '+str(client_oid))}"
    root = base_url()
    payid = o["pt_order"] or oid
    return jsonify(success=True, order_id=client_oid, pay_id=payid,
        status="SUCCESS" if o["status"] == "paid" else o["status"].upper(), amount=float(Decimal(o["amount"])/100), currency="INR",
        gateway=gw["type"], transaction_id=o["utr"] or "", payment_url=f"{root}/pay/{oid}",
        qr_url=f"{root}/pay/{oid}/qr.svg", qr_png_url=f"{root}/pay/{oid}/qr.png", upi_uri=upi,
        expires_at=datetime.fromtimestamp(o["expires_ts"], timezone.utc).isoformat().replace("+00:00", "Z"), webhook_secret=gw["webhook_secret"])


@app.route("/api/v1/payment/status/<order_id>", methods=["GET"])
def api_v1_payment_status(order_id):
    gw = api_gateway()
    if not gw: return _api_error("invalid API key", 401)
    o = db().execute("SELECT * FROM orders WHERE gateway_id=? AND (id=? OR client_order_id=? OR pt_order=?) ORDER BY created_ts DESC LIMIT 1", (gw["id"], order_id, order_id, order_id)).fetchone()
    if not o: return _api_error("order not found", 404)
    st = "EXPIRED" if o["status"] == "pending" and o["expires_ts"] < time.time() else ("SUCCESS" if o["status"] == "paid" else o["status"].upper())
    return jsonify(success=True, order_id=o["client_order_id"] or o["id"], pay_id=o["pt_order"] or o["id"], status=st,
                   amount=float(Decimal(o["amount"])/100), currency="INR", transaction_id=o["utr"] or "")


@app.route("/api/v1/payment/verify", methods=["POST"])
def api_v1_payment_verify():
    d = request.get_json(silent=True) or request.form
    oid = str(d.get("order_id") or "").strip()
    gw = api_gateway()
    if not gw: return _api_error("invalid API key", 401)
    o = db().execute("SELECT * FROM orders WHERE gateway_id=? AND (id=? OR client_order_id=? OR pt_order=?) ORDER BY created_ts DESC LIMIT 1", (gw["id"], oid, oid, oid)).fetchone()
    if not o: return _api_error("order not found", 404)
    st = "EXPIRED" if o["status"] == "pending" and o["expires_ts"] < time.time() else ("SUCCESS" if o["status"] == "paid" else o["status"].upper())
    if st == "PENDING": worker.nudge()
    return jsonify(success=(st == "SUCCESS"), data=({"order_id":o["client_order_id"] or o["id"], "amount":float(Decimal(o["amount"])/100), "utr":o["utr"], "payment_time":datetime.fromtimestamp(o["paid_ts"], timezone.utc).isoformat() if o["paid_ts"] else None} if st == "SUCCESS" else None), status=st)


@app.route("/api/create_order.php", methods=["GET"])
def api_legacy_create():
    # Legacy GET adapter. API keys remain server-side; POST JSON is preferred.
    d = request.args
    gt = str(d.get("gateway", "")).strip().lower()
    if gt not in ("paytm", "fampay"): return _api_error("gateway must be paytm or fampay", 400)
    gw = api_gateway(gt)
    if not gw: return _api_error("invalid API key or gateway", 401)
    try: amount = Decimal(str(d.get("amount", ""))).quantize(Decimal("0.01"))
    except Exception: return _api_error("invalid amount", 400)
    if not (Decimal("1") <= amount <= Decimal("100000")): return _api_error("amount must be 1 to 100000", 400)
    oid = d.get("order_id", "").strip()[:100]
    if oid:
        old = db().execute("SELECT id FROM orders WHERE gateway_id=? AND client_order_id=?", (gw["id"], oid)).fetchone()
        if old:
            o=db().execute("SELECT * FROM orders WHERE id=?", (old["id"],)).fetchone()
            return jsonify(status="success", data=_api_payment_payload(o,gw,oid).json)
    new_id, err = make_order(gw, amount, oid or None, None, None)
    if err: return _api_error(err, 502)
    db().execute("UPDATE orders SET api_v1=1,client_order_id=? WHERE id=?", (oid or new_id,new_id)); db().commit()
    o=db().execute("SELECT * FROM orders WHERE id=?", (new_id,)).fetchone()
    return jsonify(status="success", data=_api_payment_payload(o,gw,oid or new_id).json)


@app.route("/api/verify.php", methods=["GET"])
def api_legacy_verify():
    oid=request.args.get("order_id", "").strip(); gw=api_gateway()
    if not gw: return _api_error("invalid API key",401)
    o=db().execute("SELECT * FROM orders WHERE gateway_id=? AND (id=? OR client_order_id=? OR pt_order=?) ORDER BY created_ts DESC LIMIT 1",(gw["id"],oid,oid,oid)).fetchone()
    if not o: return jsonify(status="pending",data=None)
    paid=o["status"]=="paid"
    return jsonify(status="success" if paid else ("expired" if o["expires_ts"]<time.time() else "pending"), data=({"order_id":o["client_order_id"] or o["id"],"amount":money(o["amount"]),"utr":o["utr"],"payment_time":ist(o["paid_ts"])} if paid else None))

@app.route("/pay/<oid>/qr.png")
def api_qr_png(oid): return _api_qr(oid, True)

@app.route("/pay/<oid>/qr.svg")
def api_qr_svg(oid): return _api_qr(oid, False)

@app.route("/api/v1/orders", methods=["POST"])
def api_create():
    gw = api_gateway()
    if not gw: return jsonify(error="invalid or inactive api key"), 401
    if throttled("api:%s" % gw["id"], 40, 60): return jsonify(error="rate limit, slow down"), 429
    fail("api:%s" % gw["id"])
    d = request.get_json(silent=True) or request.form
    try: amount = Decimal(str(d.get("amount", ""))).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError): return jsonify(error="invalid amount"), 400
    if not (Decimal("1") <= amount <= Decimal("100000")): return jsonify(error="amount must be 1 to 100000"), 400
    wh = (d.get("webhook_url") or "").strip() or None; rd = (d.get("redirect_url") or "").strip() or None
    if wh and not payments.safe_url(wh): return jsonify(error="webhook_url must be a public http(s) URL"), 400
    if rd and not re.match(r"https?://", rd): return jsonify(error="redirect_url must be http(s)"), 400
    cu = (d.get("cancel_url") or "").strip() or None
    if cu and not re.match(r"https?://", cu): return jsonify(error="cancel_url must be http(s)"), 400
    oid, err = make_order(gw, amount, (str(d.get("ref") or ""))[:80] or None, wh, rd, cu)
    if err: return jsonify(error=err), (502 if err.startswith("Paytm") else 429)
    o = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    return jsonify(order_id=oid, payment_url=f"{base_url()}/pay/{oid}", amount=money(o["amount"]),
                   expires_in=int(o["expires_ts"] - time.time()))

@app.route("/api/v1/orders/<oid>")
def api_status(oid):
    gw = api_gateway()
    if not gw: return jsonify(error="invalid or inactive api key"), 401
    o = db().execute("SELECT * FROM orders WHERE id=? AND gateway_id=?", (oid, gw["id"])).fetchone()
    if not o: return jsonify(error="not found"), 404
    st = "expired" if o["status"] == "pending" and o["expires_ts"] < time.time() else o["status"]
    return jsonify(order_id=o["id"], ref=o["ref"], amount=money(o["amount"]), status=st, utr=o["utr"],
                   paid_at=int(o["paid_ts"]) if o["paid_ts"] else None)

@app.route("/pay/<oid>")
def pay(oid):
    o = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not o: abort(404)
    gw = db().execute("SELECT * FROM gateways WHERE id=?", (o["gateway_id"],)).fetchone()
    amt = money(o["amount"])
    upi = o["qr_data"] or f"upi://pay?pa={quote(gw['upi_id'])}&pn={quote(gw['name'])}&am={amt}&cu=INR&tn={quote('Order ' + o['id'][:8])}"
    if o["status"] == "pending" and o["expires_ts"] < time.time():
        db().execute("UPDATE orders SET status='expired' WHERE id=?", (oid,)); db().commit()
        o = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    return render_template("checkout.html", o=o, gw=gw, amt=amt, upi=upi, remaining=max(0, int(o["expires_ts"] - time.time())))

@app.route("/pay/<oid>/status")
def pay_status(oid):
    o = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not o: abort(404)
    st = "expired" if o["status"] == "pending" and o["expires_ts"] < time.time() else o["status"]
    return jsonify(status=st, remaining=max(0, int(o["expires_ts"] - time.time())))

@app.route("/docs")
@login_required
def docs():
    return render_template("docs.html", base=base_url())

@app.route("/admin/docs")
@admin_required
def admin_docs():
    return render_template("docs.html", base=base_url())

# ---------- admin: gateways & settings ----------
@app.route("/admin")
@admin_required
def admin_home():
    c = db()
    us = c.execute("SELECT 1 n").fetchone(); gw = c.execute("SELECT COUNT(*) n FROM gateways").fetchone()
    day = time.time() - (time.time() + 19800) % 86400
    ost = c.execute("""SELECT COUNT(*) n, SUM(status='paid') p, SUM(CASE WHEN status='paid' THEN amount END) s,
        SUM(CASE WHEN status='paid' AND paid_ts>=? THEN amount END) t FROM orders""", (day,)).fetchone()
    rows = c.execute("SELECT o.*, g.name gname FROM orders o JOIN gateways g ON g.id=o.gateway_id ORDER BY o.created_ts DESC LIMIT 8").fetchall()
    newu = []
    return render_template("admin_home.html", us=us, gw=gw, ost=ost, rows=rows, newu=newu)

@app.route("/admin/gateways")
@admin_required
def admin_gateways():
    gws = db().execute("""SELECT g.*, '__owner__' username, (SELECT COUNT(*) FROM orders WHERE gateway_id=g.id) n,
        (SELECT COUNT(*) FROM orders WHERE gateway_id=g.id AND status='paid') p
        FROM gateways g ORDER BY g.id DESC""").fetchall()
    orders = db().execute("SELECT * FROM orders ORDER BY created_ts DESC LIMIT 50").fetchall()
    day = time.time() - (time.time() + 19800) % 86400
    ost = db().execute("""SELECT COUNT(*) n, SUM(status='paid') p, SUM(CASE WHEN status='paid' THEN amount END) s,
        SUM(CASE WHEN status='paid' AND paid_ts>=? THEN amount END) t FROM orders""", (day,)).fetchone()
    return render_template("admin_gw.html", gws=gws, orders=orders, ost=ost, csrf=session["csrf"])

@app.route("/admin/gateway/<int:gid>/<action>", methods=["POST"])
@admin_required
def admin_gateway_action(gid, action):
    if action == "toggle": db().execute("UPDATE gateways SET active=1-active WHERE id=?", (gid,))
    elif action == "delete":
        db().execute("DELETE FROM orders WHERE gateway_id=?", (gid,)); db().execute("DELETE FROM gateways WHERE id=?", (gid,))
    db().commit(); return redirect("/admin/gateways")

@app.route("/admin/settings", methods=["GET", "POST"])
@admin_required
def admin_settings():
    if request.method == "POST":
        for k in ("base_url", "fampay_sender", "fampay_keywords", "order_expiry_min", "paytm_env", "tg_chat", "tg_token"):
            v = request.form.get(k, "").strip()
            if k == "tg_token" and not v: continue
            if k == "order_expiry_min" and not (v.isdigit() and 3 <= int(v) <= 120): v = DEFAULTS[k]
            if k == "base_url" and v and not re.match(r"https?://", v): v = ""
            if k == "paytm_env" and v not in ("prod", "stage"): v = "prod"
            set_setting(k, v)
        flash("Settings saved.", "ok")
    s_ = {k: get_setting(k) for k in DEFAULTS}
    lb = float(s_["last_backup"] or 0)
    return render_template("admin_set.html", s=s_, last_backup=ist(lb) if lb else "never", csrf=session["csrf"])

@app.route("/health")
def health():
    return jsonify(status="ok", service="payment-gateway", time=int(time.time()))

# Optional outbound keepalive. Set KEEPALIVE_URL to the public /health URL and
# KEEPALIVE_INTERVAL=240. This is best-effort only; Render may still spin down
# Free services and an external uptime monitor is more reliable.
_keepalive_started = False

def _keepalive_loop():
    url = (os.environ.get("KEEPALIVE_URL", "").strip() or (os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/") + "/health" if os.environ.get("RENDER_EXTERNAL_URL") else ""))
    interval = max(120, int(os.environ.get("KEEPALIVE_INTERVAL", "240")))
    while True:
        try:
            if url:
                req = urllib.request.Request(url, headers={"User-Agent": "RG-Gateway-KeepAlive/1.0"})
                with urllib.request.urlopen(req, timeout=15) as response:
                    app.logger.info("Keepalive ping: HTTP %s", response.status)
        except Exception as exc:
            app.logger.warning("Keepalive ping failed: %s", str(exc)[:160])
        time.sleep(interval)

def start_keepalive():
    global _keepalive_started
    if _keepalive_started: return
    _keepalive_started = True
    if os.environ.get("KEEPALIVE_URL", "").strip() or os.environ.get("RENDER_EXTERNAL_URL", "").strip():
        threading.Thread(target=_keepalive_loop, daemon=True, name="keepalive").start()

def _order_query(csv=False):
    gsel = request.args.get("gateway", type=int); ssel = request.args.get("status", "")
    q = "SELECT o.*, g.name gname FROM orders o JOIN gateways g ON g.id=o.gateway_id WHERE 1=1"; p = []
    if gsel: q += " AND o.gateway_id=?"; p.append(gsel)
    if ssel in ("paid", "pending", "expired"): q += " AND o.status=?"; p.append(ssel)
    return q + " ORDER BY o.created_ts DESC", p, gsel, ssel

@app.route("/orders")
@login_required
def orders_page():
    q, p, gsel, ssel = _order_query(); page = max(1, request.args.get("page", 1, type=int))
    rows = db().execute(q + " LIMIT 51 OFFSET ?", p + [(page - 1) * 50]).fetchall()
    gws = db().execute("SELECT id,name FROM gateways ORDER BY id DESC").fetchall()
    return render_template("orders.html", orders=rows[:50], more=len(rows) > 50, page=page, gws=gws, gsel=gsel, ssel=ssel)

@app.route("/orders.csv")
@login_required
def orders_csv():
    import csv, io
    q, p, _, _ = _order_query()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["order_id", "gateway", "ref", "amount", "status", "utr", "created_ist", "paid_ist"])
    for o in db().execute(q + " LIMIT 5000", p):
        w.writerow([o["id"], o["gname"], o["ref"], money(o["amount"]), o["status"], o["utr"], ist(o["created_ts"]), ist(o["paid_ts"])])
    from flask import Response
    return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=orders.csv"})

@app.route("/admin/order/<oid>/paid", methods=["POST"])
@admin_required
def admin_order_paid(oid):
    db().execute("UPDATE orders SET status='pending' WHERE id=? AND status='expired'", (oid,)); db().commit()
    flash("Order marked paid." if payments.mark_paid(oid, "manual") else "Could not mark paid.", "ok"); return redirect("/admin/gateways")

@app.route("/admin/backup-now", methods=["POST"])
@admin_required
def admin_backup_now():
    ok, msg = backup.run_backup(); flash(msg, "ok" if ok else "warn"); return redirect("/admin/settings")

worker.start()
start_keepalive()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
