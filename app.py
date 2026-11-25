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
import json, threading, logging
from decimal import Decimal, InvalidOperation
from urllib.parse import quote
from flask import jsonify

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
        if not session.get("uid"): return redirect("/login")
        u = db().execute("SELECT * FROM users WHERE id=?", (session["uid"],)).fetchone()
        if not u or u["banned"]:
            session.pop("uid", None); flash("Account unavailable.", "err"); return redirect("/login")
        g.user = u
        return f(*a, **k)
    return w

def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("admin"): return redirect("/admin/login")
        return f(*a, **k)
    return w

# ---------- user routes ----------
@app.route("/")
def index():
    return redirect("/dashboard" if session.get("uid") else "/login")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        un = request.form.get("username", "").strip()
        ph = re.sub(r"[^\d+]", "", request.form.get("phone", ""))
        em = request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "").strip()
        if un.lower() in [x[0] for x in ADMIN_ACCOUNTS] + ["admin"]:
            flash("This username is not available.", "err")
        elif not re.fullmatch(r"[A-Za-z0-9_.]{3,30}", un):
            flash("Username: 3-30 letters, numbers, _ or .", "err")
        elif len(ph) < 10: flash("Enter a valid phone number.", "err")
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", em): flash("Enter a valid Gmail.", "err")
        elif len(pw) < 6: flash("Password must be at least 6 characters.", "err")
        else:
            try:
                cur = db().execute("INSERT INTO users(username,password_hash,phone,email,created) VALUES(?,?,?,?,?)",
                                   (un, generate_password_hash(pw), ph, em, now()))
                db().commit()
                session.clear(); session["uid"] = cur.lastrowid; session["csrf"] = secrets.token_hex(16)
                flash("Welcome! Your account is ready.", "ok"); return redirect("/dashboard")
            except sqlite3.IntegrityError:
                db().rollback()
                flash("That username is already in use. Please choose another.", "err")
            except sqlite3.Error:
                db().rollback()
                app.logger.exception("Database error during account registration")
                flash("We could not create your account right now. Please try again shortly.", "err")
            except Exception:
                db().rollback()
                app.logger.exception("Unexpected error during account registration")
                flash("Account creation failed unexpectedly. Please try again or contact the administrator.", "err")
    return render_template("auth.html", mode="signup", csrf=session["csrf"])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        un = request.form.get("username", "").strip(); raw = request.form.get("password", "")
        k = "u:%s:%s" % (ip(), un.lower())
        if throttled(k, 10): flash("Too many attempts. Try again in a few minutes.", "err")
        else:
            if is_admin_cred(un, raw):
                session.clear(); session["admin"] = True; session["csrf"] = secrets.token_hex(16)
                return redirect("/admin")
            u = db().execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (un,)).fetchone()
            if u and (check_password_hash(u["password_hash"], raw) or check_password_hash(u["password_hash"], raw.strip())):
                if u["banned"]: flash("This account is banned.", "err")
                else:
                    _attempts.pop(k, None)
                    session.clear(); session["uid"] = u["id"]; session["csrf"] = secrets.token_hex(16)
                    return redirect("/dashboard")
            else:
                fail(k); flash("Wrong username or password.", "err")
    return render_template("auth.html", mode="login", csrf=session["csrf"])

@app.route("/logout")
def logout():
    session.pop("uid", None); return redirect("/login")

@app.route("/dashboard")
@login_required
def dashboard():
    uid = g.user["id"]
    gcount = db().execute("SELECT COUNT(*) FROM gateways WHERE user_id=?", (uid,)).fetchone()[0]
    r_ = db().execute("SELECT COUNT(*) n, SUM(status='paid') p, SUM(CASE WHEN status='paid' THEN amount ELSE 0 END) s FROM orders WHERE user_id=?", (uid,)).fetchone()
    st = {"total": r_["n"], "paid": r_["p"] or 0, "sum": money(r_["s"] or 0)}
    rows = db().execute("SELECT o.*, g.name gname FROM orders o JOIN gateways g ON g.id=o.gateway_id WHERE o.user_id=? ORDER BY o.created_ts DESC LIMIT 5", (uid,)).fetchall()
    return render_template("dash.html", u=g.user, gcount=gcount, st=st, rows=rows)

@app.route("/gateways")
@login_required
def gateways_page():
    gws = db().execute("SELECT * FROM gateways WHERE user_id=? ORDER BY id DESC", (g.user["id"],)).fetchall()
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
    if request.method == "POST":
        k = "a:" + ip()
        if throttled(k, 5): flash("Too many attempts. Wait a few minutes.", "err")
        elif is_admin_cred(request.form.get("username"), request.form.get("password")):
            session.clear()
            session["admin"] = True
            session["csrf"] = secrets.token_hex(16)
            _attempts.pop(k, None)
            return redirect("/admin")
        else:
            fail(k); flash("Wrong admin credentials.", "err")
    return render_template("admin_login.html", csrf=session["csrf"])

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None); return redirect("/admin/login")

@app.route("/admin/users")
@admin_required
def admin_users():
    q = request.args.get("q", "").strip()
    like = f"%{q}%"
    rows = db().execute("SELECT * FROM users WHERE username!='__platform_gateway_owner__' AND (username LIKE ? OR phone LIKE ? OR email LIKE ?) ORDER BY id DESC",
                        (like, like, like)).fetchall()
    t = db().execute("SELECT COUNT(*) c, SUM(banned) b FROM users WHERE username!='__platform_gateway_owner__'").fetchone()
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
    target = db().execute("SELECT username FROM users WHERE id=?", (uid,)).fetchone()
    if target and target["username"] == "__platform_gateway_owner__":
        abort(403)
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
    gw = db().execute("SELECT * FROM gateways WHERE id=? AND user_id=?", (gid, g.user["id"])).fetchone()
    if not gw: abort(404)
    return gw

def base_url():
    return (get_setting("base_url").strip().rstrip("/")) or request.url_root.rstrip("/")

@app.route("/gateway/add", methods=["POST"])
@login_required
def gateway_add():
    f = request.form; typ = f.get("type", "fampay")
    name = f.get("name", "").strip()[:40]; upi = f.get("upi_id", "").strip()
    n = db().execute("SELECT COUNT(*) FROM gateways WHERE user_id=?", (g.user["id"],)).fetchone()[0]
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
    cur = db().execute("INSERT INTO gateways(user_id,type,name,upi_id,gmail,app_pw_enc,mid,key_enc,api_key,created) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (g.user["id"], typ, name, upi, vals["gmail"], vals["pw"], vals["mid"], vals["key"], "gw_" + secrets.token_urlsafe(24), time.time()))
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

def api_gateway():
    auth = request.headers.get("Authorization", "")
    bearer = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    key = request.headers.get("X-API-Key") or bearer or request.values.get("api_key") or (request.get_json(silent=True) or {}).get("api_key", "")
    gw = db().execute("""SELECT g.* FROM gateways g JOIN users u ON u.id=g.user_id
                         WHERE g.api_key=? AND g.active=1 AND u.banned=0""", (key,)).fetchone() if key else None
    return gw

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

# ---------- compatibility endpoints for the payment/create + verify API format ----------
def compat_response(gw, oid, requested_order_id=None):
    o = db().execute("SELECT * FROM orders WHERE id=? AND gateway_id=?", (oid, gw["id"])).fetchone()
    if not o: return jsonify(success=False, error="order not found"), 404
    base = base_url(); payid = o["pt_order"] or o["id"]
    payment_url = f"{base}/pay/{o['id']}"
    upi = o["qr_data"] or paytm.build_upi(gw["upi_id"], gw["name"], money(o["amount"]), payid)
    expires = datetime.fromtimestamp(o["expires_ts"], timezone.utc).isoformat().replace("+00:00", "Z")
    return jsonify(success=True, order_id=requested_order_id or o["id"], pay_id=payid,
        status="SUCCESS" if o["status"]=="paid" else o["status"].upper(),
        amount=float(money(o["amount"])), currency="INR", gateway=gw["type"],
        transaction_id=o["utr"] or "", payment_url=payment_url,
        qr_url=payment_url+"/qr.svg", qr_png_url=payment_url+"/qr.png",
        upi_uri=upi, expires_at=expires)

@app.route("/api/v1/payment/create", methods=["GET", "POST"])
def api_payment_create():
    gw = api_gateway()
    if not gw: return jsonify(success=False, error="invalid or inactive API key"), 401
    if throttled("api:%s" % gw["id"], 60, 60): return jsonify(success=False, error="rate limit"), 429
    fail("api:%s" % gw["id"])
    d = request.get_json(silent=True) or request.values
    selected = str(d.get("gateway") or "").lower()
    if selected not in ("paytm", "fampay") or selected != gw["type"]:
        return jsonify(success=False, error="gateway must match this API token"), 400
    try: amount = Decimal(str(d.get("amount", ""))).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError): return jsonify(success=False, error="invalid amount"), 400
    if not (Decimal("1") <= amount <= Decimal("100000")):
        return jsonify(success=False, error="amount must be 1 to 100000"), 400
    ref = str(d.get("order_id") or "")[:80] or None
    wh = (d.get("webhook_url") or "").strip() or None
    rd = (d.get("redirect_url") or "").strip() or None
    if wh and not payments.safe_url(wh): return jsonify(success=False, error="webhook_url must be a public http(s) URL"), 400
    if rd and not re.match(r"https?://", rd): return jsonify(success=False, error="redirect_url must be http(s)"), 400
    oid, err = make_order(gw, amount, ref, wh, rd)
    if err: return jsonify(success=False, error=err), 429
    result = compat_response(gw, oid, ref)
    if request.method == "GET":
        return jsonify(status="success", data=result.get_json())
    return result

@app.route("/api/create_order.php", methods=["GET"])
def api_create_order_php():
    return api_payment_create()

@app.route("/api/verify.php", methods=["GET"])
def api_verify_php():
    gw = api_gateway()
    if not gw: return jsonify(status="error", error="invalid or inactive API key"), 401
    oid = str(request.args.get("order_id") or "")
    if not oid: return jsonify(status="error", error="order_id required"), 400
    o = db().execute("SELECT * FROM orders WHERE gateway_id=? AND (id=? OR pt_order=? OR ref=?) ORDER BY created_ts DESC LIMIT 1",
                     (gw["id"], oid, oid, oid)).fetchone()
    if not o: return jsonify(status="pending", data=None), 404
    if o["status"] == "paid":
        return jsonify(status="success", data={"order_id": o["ref"] or o["id"],
            "amount": float(money(o["amount"])), "utr": o["utr"] or "",
            "payment_time": datetime.fromtimestamp(o["paid_ts"], timezone.utc).isoformat() if o["paid_ts"] else None})
    st = "expired" if o["status"] == "pending" and o["expires_ts"] < time.time() else o["status"]
    return jsonify(status=st, data=None)

@app.route("/checkout.php", methods=["GET"])
def hosted_checkout_compat():
    gw = api_gateway()
    if not gw: abort(401)
    d = request.args
    if str(d.get("gateway") or "").lower() != gw["type"]: abort(400)
    try: amount = Decimal(str(d.get("amount", ""))).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError): abort(400)
    if not (Decimal("1") <= amount <= Decimal("100000")): abort(400)
    ref = str(d.get("order_id") or "")[:80] or None
    oid, err = make_order(gw, amount, ref, None, None)
    if err: abort(429)
    return redirect(f"{base_url()}/pay/{oid}")

@app.route("/api/v1/payment/status/<oid>", methods=["GET"])
def api_payment_status(oid):
    gw = api_gateway()
    if not gw: return jsonify(success=False, error="invalid or inactive API key"), 401
    o = db().execute("SELECT * FROM orders WHERE gateway_id=? AND (id=? OR pt_order=? OR ref=?) ORDER BY created_ts DESC LIMIT 1",
                     (gw["id"], oid, oid, oid)).fetchone()
    if not o: return jsonify(success=False, error="order not found"), 404
    st = "SUCCESS" if o["status"]=="paid" else ("EXPIRED" if o["status"]=="pending" and o["expires_ts"]<time.time() else o["status"].upper())
    return jsonify(success=True, order_id=o["ref"] or o["id"], pay_id=o["pt_order"] or o["id"],
        status=st, amount=float(money(o["amount"])), currency="INR",
        transaction_id=o["utr"] or "", gateway=gw["type"])

@app.route("/api/v1/payment/verify", methods=["POST"])
def api_payment_verify():
    gw = api_gateway()
    if not gw: return jsonify(success=False, error="invalid or inactive API key"), 401
    d = request.get_json(silent=True) or request.form; oid = str(d.get("order_id") or "")
    if not oid: return jsonify(success=False, error="order_id required"), 400
    o = db().execute("SELECT * FROM orders WHERE gateway_id=? AND (id=? OR pt_order=? OR ref=?) ORDER BY created_ts DESC LIMIT 1",
                     (gw["id"], oid, oid, oid)).fetchone()
    if not o: return jsonify(success=False, error="order not found"), 404
    st = "SUCCESS" if o["status"]=="paid" else ("EXPIRED" if o["status"]=="pending" and o["expires_ts"]<time.time() else o["status"].upper())
    return jsonify(success=True, order_id=o["ref"] or o["id"], status=st,
        amount=float(money(o["amount"])), transaction_id=o["utr"] or "", gateway=gw["type"])

@app.route("/pay/<oid>/qr.svg")
def payment_qr_svg(oid):
    o = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not o: abort(404)
    gw = db().execute("SELECT * FROM gateways WHERE id=?", (o["gateway_id"],)).fetchone()
    if not gw: abort(404)
    upi = o["qr_data"] or paytm.build_upi(gw["upi_id"], gw["name"], money(o["amount"]), o["pt_order"] or o["id"])
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage
        buf = __import__("io").BytesIO()
        qrcode.make(upi, image_factory=SvgPathImage).save(buf)
        buf.seek(0)
        return send_file(buf, mimetype="image/svg+xml", max_age=30)
    except Exception:
        abort(503, "QR image renderer unavailable")

@app.route("/pay/<oid>/qr.png")
def payment_qr_png(oid):
    o = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if not o: abort(404)
    gw = db().execute("SELECT * FROM gateways WHERE id=?", (o["gateway_id"],)).fetchone()
    if not gw: abort(404)
    upi = o["qr_data"] or paytm.build_upi(gw["upi_id"], gw["name"], money(o["amount"]), o["pt_order"] or o["id"])
    try:
        import qrcode
        buf = __import__("io").BytesIO()
        qrcode.make(upi).save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png", max_age=30)
    except Exception:
        abort(503, "QR image renderer unavailable")

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

# ---------- admin-owned platform gateway configuration ----------
def platform_user_id():
    """Private owner record reuses existing gateway storage and verifier pipeline."""
    row = db().execute("SELECT id FROM users WHERE username='__platform_gateway_owner__'").fetchone()
    if row: return row["id"]
    cur = db().execute("INSERT INTO users(username,password_hash,phone,email,banned,created) VALUES(?,?,?,?,0,?)",
        ("__platform_gateway_owner__", generate_password_hash(secrets.token_urlsafe(32)), "", "", now()))
    db().commit()
    return cur.lastrowid

@app.route("/admin/platform-gateways")
@admin_required
def admin_platform_gateways():
    owner = platform_user_id()
    rows = db().execute("SELECT * FROM gateways WHERE user_id=? ORDER BY id DESC", (owner,)).fetchall()
    return render_template("admin_platform_gw.html", gws=rows, csrf=session["csrf"])

@app.route("/admin/platform-gateway/add", methods=["POST"])
@admin_required
def admin_platform_gateway_add():
    f = request.form; typ = f.get("type", "")
    name = f.get("name", "").strip()[:40]; upi = f.get("upi_id", "").strip()
    vals = dict(gmail=None, pw=None, mid=None); err = None
    if typ not in ("paytm", "fampay"): err = "Choose a supported gateway."
    elif not name: err = "Enter a shop name."
    elif not re.fullmatch(r"[\w.\-]{2,}@[A-Za-z0-9]{2,}", upi): err = "Enter a valid UPI ID."
    elif typ == "fampay":
        gm = f.get("gmail", "").strip().lower(); pw = re.sub(r"\s", "", f.get("app_password", ""))
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", gm): err = "Enter a valid Gmail."
        elif not re.fullmatch(r"[A-Za-z0-9]{16}", pw): err = "Gmail App Password must contain 16 letters/digits."
        else:
            ok, msg = fampay.test_login(gm, pw)
            if not ok: err = msg
            vals.update(gmail=gm, pw=enc(pw))
    elif typ == "paytm":
        mid = f.get("mid", "").strip()
        if not re.fullmatch(r"[A-Za-z0-9@_.\-]{6,40}", mid): err = "Enter a valid Paytm MID."
        else:
            ok, msg = paytm.test_creds(mid)
            if not ok: err = msg
            vals.update(mid=mid)
    if err:
        flash(err, "err"); return redirect("/admin/platform-gateways")
    uid = platform_user_id()
    db().execute("""INSERT INTO gateways(user_id,type,name,upi_id,gmail,app_pw_enc,mid,key_enc,api_key,created)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (uid, typ, name, upi, vals["gmail"], vals["pw"], vals["mid"], None,
         "gw_" + secrets.token_urlsafe(24), time.time()))
    db().commit(); flash("Platform gateway saved. Copy its API token below.", "ok")
    return redirect("/admin/platform-gateways")

@app.route("/admin/platform-gateway/<int:gid>/<action>", methods=["POST"])
@admin_required
def admin_platform_gateway_action(gid, action):
    uid = platform_user_id()
    gw = db().execute("SELECT * FROM gateways WHERE id=? AND user_id=?", (gid, uid)).fetchone()
    if not gw: abort(404)
    if action == "toggle":
        db().execute("UPDATE gateways SET active=1-active WHERE id=?", (gid,))
    elif action == "regen":
        db().execute("UPDATE gateways SET api_key=? WHERE id=?", ("gw_" + secrets.token_urlsafe(24), gid))
        flash("New API token generated. Update your bot/server configuration.", "ok")
    elif action == "delete":
        db().execute("DELETE FROM orders WHERE gateway_id=?", (gid,))
        db().execute("DELETE FROM seen_mail WHERE gateway_id=?", (gid,))
        db().execute("DELETE FROM gateways WHERE id=?", (gid,))
        flash("Platform gateway deleted.", "ok")
    elif action == "test":
        try:
            if gw["type"] == "fampay": ok, msg = fampay.test_login(gw["gmail"], dec(gw["app_pw_enc"]))
            else: ok, msg = paytm.test_creds(gw["mid"])
        except Exception: ok, msg = False, "Could not read saved credentials. Check SECRET_KEY."
        flash(msg, "ok" if ok else "err")
    else: abort(404)
    db().commit()
    return redirect("/admin/platform-gateways")

# ---------- admin: gateways & settings ----------
@app.route("/admin")
@admin_required
def admin_home():
    c = db()
    us = c.execute("SELECT COUNT(*) n FROM users WHERE username!='__platform_gateway_owner__'").fetchone(); gw = c.execute("SELECT COUNT(*) n FROM gateways").fetchone()
    day = time.time() - (time.time() + 19800) % 86400
    ost = c.execute("""SELECT COUNT(*) n, SUM(status='paid') p, SUM(CASE WHEN status='paid' THEN amount END) s,
        SUM(CASE WHEN status='paid' AND paid_ts>=? THEN amount END) t FROM orders""", (day,)).fetchone()
    rows = c.execute("SELECT o.*, g.name gname FROM orders o JOIN gateways g ON g.id=o.gateway_id ORDER BY o.created_ts DESC LIMIT 8").fetchall()
    newu = c.execute("SELECT * FROM users WHERE username!='__platform_gateway_owner__' ORDER BY id DESC LIMIT 5").fetchall()
    return render_template("admin_home.html", us=us, gw=gw, ost=ost, rows=rows, newu=newu)

@app.route("/admin/gateways")
@admin_required
def admin_gateways():
    gws = db().execute("""SELECT g.*, u.username, (SELECT COUNT(*) FROM orders WHERE gateway_id=g.id) n,
        (SELECT COUNT(*) FROM orders WHERE gateway_id=g.id AND status='paid') p
        FROM gateways g JOIN users u ON u.id=g.user_id ORDER BY g.id DESC""").fetchall()
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
def health(): return "ok"

def _order_query(csv=False):
    gsel = request.args.get("gateway", type=int); ssel = request.args.get("status", "")
    q = "SELECT o.*, g.name gname FROM orders o JOIN gateways g ON g.id=o.gateway_id WHERE o.user_id=?"; p = [g.user["id"]]
    if gsel: q += " AND o.gateway_id=?"; p.append(gsel)
    if ssel in ("paid", "pending", "expired"): q += " AND o.status=?"; p.append(ssel)
    return q + " ORDER BY o.created_ts DESC", p, gsel, ssel

@app.route("/orders")
@login_required
def orders_page():
    q, p, gsel, ssel = _order_query(); page = max(1, request.args.get("page", 1, type=int))
    rows = db().execute(q + " LIMIT 51 OFFSET ?", p + [(page - 1) * 50]).fetchall()
    gws = db().execute("SELECT id,name FROM gateways WHERE user_id=?", (g.user["id"],)).fetchall()
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
