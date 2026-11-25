FLASH = """{% with m=get_flashed_messages(with_categories=true) %}{% for c,t in m %}<div class="flash {{c}}">{{t}}</div>{% endfor %}{% endwith %}"""

BASE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#07080d">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%237c5cff'/%3E%3Cpath d='M11 24V8h6.5a4.5 4.5 0 0 1 0 9H11' stroke='white' stroke-width='3' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">

<title>{% block title %}Pay Gateway{% endblock %}</title>
<style>
:root{--bg:#06070c;--card:#0e1119;--card2:#131726;--line:#1c2133;--line2:#2a3150;--txt:#eef0f7;--mut:#8b92ab;--a:#7c5cff;--a2:#4f8cff;--b:#22d3ee;--ok:#22c55e;--bad:#ef4444;--warn:#f59e0b}
*{box-sizing:border-box}html{-webkit-tap-highlight-color:transparent;scroll-behavior:smooth}
body{margin:0;background:radial-gradient(900px 520px at 12% -10%,#1b1550 0,transparent 60%),radial-gradient(700px 420px at 100% 0,#06344a 0,transparent 55%),var(--bg);color:var(--txt);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-size:15px;line-height:1.5;min-height:100vh;background-attachment:fixed;-webkit-font-smoothing:antialiased}
body.open{overflow:hidden}
a{color:var(--b);text-decoration:none}a:hover{text-decoration:underline}
::selection{background:#7c5cff66}
.logo{font-weight:800;letter-spacing:.2px;background:linear-gradient(90deg,#b9a8ff,var(--b));-webkit-background-clip:text;background-clip:text;color:transparent;font-size:19px}
.brand{display:flex;align-items:center;gap:10px}.brand.c{justify-content:center}
.mark{width:34px;height:34px;border-radius:10px;flex:none;display:grid;place-items:center;background:linear-gradient(135deg,var(--a),var(--b));box-shadow:0 6px 22px #7c5cff55}
.mark svg{width:19px;height:19px}
.topbar{position:sticky;top:0;display:flex;align-items:center;gap:12px;padding:10px 16px;background:#07080dd9;backdrop-filter:blur(14px);border-bottom:1px solid var(--line);z-index:20}
.menu-btn{width:42px;height:42px;display:grid;place-items:center;border-radius:12px;border:1px solid var(--line);background:#11141f;color:var(--txt);cursor:pointer}
.menu-btn svg{width:22px;height:22px}.grow{flex:1}
.overlay{position:fixed;inset:0;background:#000a;backdrop-filter:blur(2px);opacity:0;pointer-events:none;transition:opacity .25s;z-index:30}
body.open .overlay{opacity:1;pointer-events:auto}
.drawer{position:fixed;top:0;left:0;bottom:0;width:272px;max-width:84vw;background:linear-gradient(180deg,#0e1019,#090a11);border-right:1px solid var(--line);transform:translateX(-103%);transition:transform .28s cubic-bezier(.3,.8,.3,1);z-index:40;padding:20px 14px;display:flex;flex-direction:column;gap:4px;overflow-y:auto}
body.open .drawer{transform:none;box-shadow:0 0 60px #7c5cff30}
.drawer .brand{padding:2px 8px 18px}.drawer .brand .logo{font-size:21px}
.who{display:flex;align-items:center;gap:12px;padding:12px;border:1px solid var(--line);border-radius:14px;background:#0b0d15;margin-bottom:14px}
.who b{display:block;font-size:14px;word-break:break-all}.who small{color:var(--mut);font-size:12px}
.av{width:38px;height:38px;border-radius:50%;flex:none;display:grid;place-items:center;font-weight:800;color:#fff;background:linear-gradient(135deg,var(--a),var(--a2))}
.drawer a{display:flex;align-items:center;gap:13px;padding:11px 14px;border-radius:12px;color:#a7aec6;font-weight:600;font-size:14.5px;position:relative;transition:.15s}
.drawer a:hover{background:#ffffff08;color:#fff;text-decoration:none}
.drawer a.active{background:linear-gradient(90deg,#7c5cff30,#22d3ee12);color:#fff}
.drawer a.active:before{content:"";position:absolute;left:-14px;top:9px;bottom:9px;width:3px;border-radius:0 3px 3px 0;background:linear-gradient(var(--a),var(--b))}
.drawer a.active .ic{color:var(--b)}.drawer a.out{color:#f2a0a0}
.drawer .sp{flex:1}
.ic{width:20px;height:20px;flex:none}
.page{max-width:1000px;margin:0 auto;padding:22px 16px 70px}
.pagehead{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:2px 0 20px;flex-wrap:wrap}
.pagehead h1{margin:0;font-size:25px;letter-spacing:-.3px}
@media(min-width:980px){.menu-btn,.overlay,.topbar{display:none}.drawer{transform:none}main.page{margin-left:272px;max-width:none;padding:34px 44px 80px}main.page>*{max-width:1080px}}
.card{background:linear-gradient(180deg,#131626cc,#0d1018);border:1px solid var(--line);border-radius:18px;padding:22px;box-shadow:0 10px 40px #00000040;margin-bottom:18px}

.auth-shell{min-height:100svh;display:grid;place-items:center;padding:28px 16px;position:relative;overflow:hidden}
.auth-shell:before,.auth-shell:after{content:"";position:absolute;width:360px;height:360px;border-radius:50%;filter:blur(75px);opacity:.22;pointer-events:none}
.auth-shell:before{background:#7655ff;top:-170px;left:-130px}.auth-shell:after{background:#06b6d4;right:-160px;bottom:-190px}
.auth{width:100%;max-width:470px;margin:0 auto;position:relative;z-index:1;padding:clamp(22px,5vw,36px);background:linear-gradient(155deg,#151a2bfa,#0b0e17fa);border:1px solid #303653;border-radius:24px;box-shadow:0 28px 90px #0009}
.auth-brand{display:flex;align-items:center;justify-content:center;gap:12px;margin-bottom:30px}
.auth-brand .mark{width:44px;height:44px;border-radius:14px}
.auth-brand .logo{font-size:25px}
.auth-kicker{font-size:11px;letter-spacing:1.8px;text-transform:uppercase;color:#8d9ab9;font-weight:800;margin-bottom:9px}
.auth h1{font-size:clamp(25px,6vw,30px);line-height:1.2;margin:0 0 9px;letter-spacing:-.8px}
.auth-sub{color:#9ba4bd;font-size:13.5px;margin:0 0 23px;line-height:1.65}
.auth label{margin:16px 0 7px;color:#b6bfd5;font-size:11px}
.auth input{min-height:49px;background:#090c15;border-color:#303956;border-radius:13px}
.auth input::placeholder{color:#626d88}
.auth .btn.full{min-height:51px;margin-top:24px;border-radius:13px;font-size:15px;background:linear-gradient(105deg,#7657f6,#397fe8);box-shadow:0 10px 28px #644de944}
.auth-foot{border-top:1px solid #252c40;margin-top:24px;padding-top:20px;text-align:center;color:#929bb2;font-size:13px}
.auth-foot a{color:#a99aff;font-weight:800}
.auth-trust{display:flex;justify-content:center;gap:8px;align-items:center;color:#7f8ba6;font-size:11px;margin-top:20px}
.auth-trust span{color:#35d69a}
.auth .flash{margin:0 0 14px}
.auth .pw input{padding-right:72px}
@media(max-width:420px){.auth-shell{padding:18px 13px}.auth{border-radius:20px}.auth-brand{margin-bottom:25px}}

.glow{position:relative}.glow:before{content:"";position:absolute;inset:-1px;border-radius:19px;padding:1px;background:linear-gradient(135deg,#7c5cff88,transparent 40%,#22d3ee66);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none}
h1,h2,h3{margin:0 0 14px;letter-spacing:-.2px}h2{font-size:18px}h3{font-size:16px}
label{display:block;font-size:12px;font-weight:600;color:var(--mut);margin:14px 0 6px;letter-spacing:.3px;text-transform:uppercase}
input,select{width:100%;padding:13px 14px;border-radius:12px;border:1px solid var(--line2);background:#0a0c14;color:var(--txt);font-size:15px;font-family:inherit;outline:none;transition:.15s}
input:hover,select:hover{border-color:#3a4268}
input:focus,select:focus{border-color:var(--a);box-shadow:0 0 0 4px #7c5cff26}
input[readonly]{color:#b9c2ff;font-family:ui-monospace,Menlo,monospace;font-size:13px}
.pw{position:relative}.pw input{padding-right:70px}
.eye{position:absolute;right:8px;top:50%;transform:translateY(-50%);border:0;background:#1a1f33;color:#b9c2ff;border-radius:8px;padding:6px 10px;font-size:12px;font-weight:600;cursor:pointer}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:0;cursor:pointer;padding:12px 20px;border-radius:12px;font-weight:700;color:#fff;background:linear-gradient(90deg,var(--a),var(--a2));font-size:14px;font-family:inherit;box-shadow:0 8px 24px #7c5cff35;transition:transform .15s,box-shadow .15s,filter .15s}
.btn:hover{transform:translateY(-1px);filter:brightness(1.08);box-shadow:0 12px 30px #7c5cff4d;text-decoration:none}
.btn:active{transform:none}
.btn.full{width:100%;margin-top:20px;padding:15px;font-size:15px}
.btn.sm{padding:8px 14px;font-size:12.5px;border-radius:10px;box-shadow:none}
.btn.gray{background:#1e2338;box-shadow:none;color:#dfe3f5}.btn.red{background:#b42323;box-shadow:none}.btn.green{background:#15803d;box-shadow:none}
.flash{padding:12px 14px;border-radius:12px;margin-bottom:14px;font-size:14px;border:1px solid;word-break:break-word}
.flash.ok{background:#22c55e14;border-color:#22c55e55;color:#86efac}
.flash.err{background:#ef444414;border-color:#ef444455;color:#fca5a5}
.flash.warn{background:#f59e0b14;border-color:#f59e0b55;color:#fcd34d}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin-bottom:18px}
.grid .card{margin:0}
.stat{display:flex;align-items:center;gap:14px;padding:18px}
.stat .si{width:46px;height:46px;border-radius:13px;display:grid;place-items:center;flex:none;background:linear-gradient(135deg,#7c5cff33,#22d3ee22);color:var(--b)}
.stat span{color:var(--mut);font-size:12.5px;font-weight:500}
.stat b{display:block;font-size:24px;margin-top:2px;letter-spacing:-.4px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{padding:12px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
th{color:var(--mut);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.7px;white-space:nowrap}
tr:last-child td{border-bottom:0}tbody tr:hover td,table tr:hover td{background:#ffffff04}
.tag{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:99px;font-size:12px;font-weight:700;background:#ffffff12;color:#c9cfe6}
.tag:before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor;opacity:.8}
.tag.ok{background:#22c55e1f;color:#86efac}.tag.bad{background:#ef44441f;color:#fca5a5}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
details{background:#0a0c14;border:1px solid var(--line);border-radius:12px;padding:8px 12px;margin:4px 0}
summary{cursor:pointer;color:var(--b);font-size:13px;font-weight:600}
.row{display:flex;gap:12px;flex-wrap:wrap;align-items:end}.row>*{flex:1;min-width:160px}
.mut{color:var(--mut);font-size:13.5px}.center{text-align:center}
.note{display:flex;gap:10px;padding:12px 14px;border-radius:12px;background:#22d3ee0f;border:1px solid #22d3ee33;color:#9fe7f5;font-size:13.5px;margin:6px 0 4px}
.gl{display:flex;align-items:center;gap:14px;padding:16px;border:1px solid var(--line);border-radius:16px;background:linear-gradient(180deg,#121524,#0b0d15);margin-bottom:12px;transition:.18s}
.gl:hover{border-color:#7c5cff66;transform:translateY(-2px);box-shadow:0 12px 30px #7c5cff1f;text-decoration:none}
.gl .gi{width:44px;height:44px;border-radius:13px;display:grid;place-items:center;background:linear-gradient(135deg,#7c5cff33,#22d3ee22);color:var(--b)}
.gl .gt{flex:1;min-width:0}.gl .gt b{display:block;font-size:15.5px}.gl .gt span{color:var(--mut);font-size:13px;word-break:break-all}
code{background:#0a0c14;padding:2px 7px;border-radius:6px;font-size:13px;color:#b9c2ff}
pre{overflow:auto;background:#080a11;border:1px solid var(--line);padding:16px;border-radius:12px;font-size:13px;line-height:1.55}
/* checkout */
.co{max-width:440px;margin:0 auto}
.back{display:inline-flex;align-items:center;gap:6px;font-weight:700;margin:4px 0 14px;color:#b9c2ff}
.cohead{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:18px}
.cohead .nm{font-weight:800;font-size:17px}
.secure{font-size:11.5px;font-weight:700;color:#86efac;background:#22c55e1a;border:1px solid #22c55e44;padding:4px 10px;border-radius:99px;white-space:nowrap}
.amt{font-size:44px;font-weight:800;letter-spacing:-1px;background:linear-gradient(90deg,#fff,#c7d0ff);-webkit-background-clip:text;background-clip:text;color:transparent;line-height:1.1}
.qrbox{background:#fff;display:inline-block;padding:14px;border-radius:18px;margin:16px 0 6px;box-shadow:0 0 0 6px #7c5cff26,0 16px 40px #00000066}
.upirow{display:flex;align-items:center;justify-content:space-between;gap:10px;background:#0a0c14;border:1px dashed var(--line2);border-radius:12px;padding:10px 12px;margin:14px 0;text-align:left}
.upirow small{display:block;color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.5px}
.upirow b{font-size:14px;word-break:break-all}
.bar{height:6px;border-radius:99px;background:#1a1f33;overflow:hidden;margin:14px 0 8px}
.bar i{display:block;height:100%;width:100%;border-radius:99px;background:linear-gradient(90deg,var(--a),var(--b));transition:width 1s linear}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--ok);margin-right:6px;animation:pulse 1.4s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 #22c55e88}100%{box-shadow:0 0 0 10px #22c55e00}}
.big{font-size:60px;line-height:1}
</style></head><body>{% block body %}{% endblock %}</body></html>"""


ICONS = """{% macro ico(n) %}{% set P={
'home':'<path d="M3 11l9-8 9 8"/><path d="M5 10v10h5v-6h4v6h5V10"/>',
'grid':'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
'list':'<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
'book':'<path d="M4 4h12a3 3 0 0 1 3 3v13H7a3 3 0 0 1-3-3z"/><path d="M4 17a3 3 0 0 1 3-3h12"/>',
'user':'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
'users':'<circle cx="9" cy="8" r="3.5"/><path d="M2 20a7 7 0 0 1 14 0"/><circle cx="17" cy="9" r="2.5"/><path d="M17 14a5 5 0 0 1 5 5"/>',
'gear':'<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
'logout':'<path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4"/><path d="M16 8l4 4-4 4M20 12H9"/>',
'chart':'<path d="M4 20V4M4 20h16"/><path d="M8 16v-5M12 16V7M16 16v-8"/>',
'plus':'<path d="M12 5v14M5 12h14"/>',
'wallet':'<path d="M3 7a2 2 0 0 1 2-2h13v4"/><path d="M3 7v11a2 2 0 0 0 2 2h14a1 1 0 0 0 1-1v-9a1 1 0 0 0-1-1H5a2 2 0 0 1-2-2"/><circle cx="16" cy="14" r="1.2"/>',
'check':'<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
'shield':'<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>'} %}<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{{ P[n]|safe }}</svg>{% endmacro %}"""

MARK = '<span class="mark"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round"><path d="M8 20V5h6a4 4 0 0 1 0 8H8"/></svg></span>'

def _layout(items, who, av, sub, tail):
    links = "".join(
        '<a href="%s" class="{{ \'active\' if active==\'%s\' }}">{{ ico(\'%s\') }}<span>%s</span></a>' % (h, k, i, t)
        for k, h, t, i in items)
    return ("{% extends 'base.html' %}{% from 'icons.html' import ico %}{% block body %}"
      '<div class="topbar"><button class="menu-btn" onclick="tgl()" aria-label="Menu"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h16"/></svg></button>'
      '<div class="brand">' + MARK + '<span class="logo">Pay Gateway</span></div><div class="grow"></div></div>'
      '<div class="overlay" onclick="tgl()"></div>'
      '<aside class="drawer"><div class="brand">' + MARK + '<span class="logo">Pay Gateway</span></div>'
      '<div class="who"><div class="av">' + av + '</div><div><b>' + who + '</b><small>' + sub + '</small></div></div>'
      + links + '<div class="sp"></div>' + tail + '</aside>'
      '<main class="page">' + FLASH + '{% block content %}{% endblock %}</main>'
      '<script>function tgl(){document.body.classList.toggle("open")}</script>{% endblock %}')

USER_ITEMS = [("home", "/admin", "Dashboard", "home"), ("gateways", "/gateways", "Gateway Setup", "grid"),
              ("gws", "/admin/gateways", "Gateway Management", "layers"), ("add", "/gateway/new", "Add Gateway", "plus"),
              ("orders", "/orders", "Payments &amp; Orders", "list"),
              ("docs", "/docs", "API Documentation", "book"), ("set", "/admin/settings", "Settings &amp; Backup", "gear")]
ADMIN_ITEMS = USER_ITEMS
LAYOUT_ADMIN = _layout(ADMIN_ITEMS, "Owner", "O", "Single owner · Full access", '<a class="out" href="/admin/logout">{{ ico(\'logout\') }}<span>Logout</span></a>')
LAYOUT_USER = LAYOUT_ADMIN

def page(layout, active, title, content):
    return ("{% extends '" + layout + "' %}{% set active='" + active + "' %}{% block title %}" + title + "{% endblock %}{% block content %}" + content + "{% endblock %}")

_PWJS = """<script>function sp(b){var i=document.getElementById('pw');var s=i.type=='password';i.type=s?'text':'password';b.textContent=s?'Hide':'Show'}</script>"""

AUTH = """{% extends 'base.html' %}{% block title %}{{ 'Create account' if mode=='signup' else 'Login' }} · Pay Gateway{% endblock %}
{% block body %}
<main class="auth-shell">
<section class="auth glow">
  <div class="auth-brand">""" + MARK + """<span class="logo">Pay Gateway</span></div>
  <div class="auth-kicker">{{ 'Owner access' if mode=='login' else 'Merchant registration' }}</div>
  <h1>{{ 'Create your account' if mode=='signup' else 'Welcome back, Owner' }}</h1>
  <p class="auth-sub">{{ 'Set up your merchant workspace and start managing payments securely.' if mode=='signup' else 'Sign in once to access every gateway, payment, order, API and setting from one dashboard.' }}</p>
  """ + FLASH + """
  <form method="post" action="{{ '/signup' if mode=='signup' else '/login' }}" autocomplete="on">
    <input type="hidden" name="csrf" value="{{ csrf }}">
    <label for="username">Username</label>
    <input id="username" name="username" type="text" required minlength="3" maxlength="30"
      placeholder="Enter your username" autocomplete="username" autocapitalize="off" autocorrect="off" spellcheck="false">
    {% if mode=='signup' %}
      <label for="phone">Phone number</label>
      <input id="phone" name="phone" type="tel" required inputmode="tel" maxlength="15"
        pattern="[0-9+ ]{10,15}" placeholder="Your mobile number" autocomplete="tel">
      <label for="email">Gmail address</label>
      <input id="email" name="email" type="email" required maxlength="254"
        placeholder="you@gmail.com" autocomplete="email" autocapitalize="off">
    {% endif %}
    <label for="pw">Password</label>
    <div class="pw"><input id="pw" name="password" type="password" required minlength="6"
      placeholder="{{ 'Create a password (6+ characters)' if mode=='signup' else 'Enter your password' }}"
      autocomplete="{{ 'new-password' if mode=='signup' else 'current-password' }}">
      <button type="button" class="eye" onclick="sp(this)" aria-label="Show or hide password">Show</button></div>
    <button class="btn full" type="submit">{{ 'Create account' if mode=='signup' else 'Sign in securely' }} <span aria-hidden="true">→</span></button>
  </form>
  <div class="auth-foot">
    {% if mode=='signup' %}Already have an account? <a href="/login">Sign in</a>{% else %}Owner access only · Single dashboard{% endif %}
  </div>
  <div class="auth-trust"><span>●</span> Secure session · Protected merchant access</div>
</section>
</main>
""" + _PWJS + """{% endblock %}"""

ADMIN_LOGIN = """{% extends 'base.html' %}{% block title %}Administrator Login · Pay Gateway{% endblock %}
{% block body %}<main class="auth-shell"><section class="auth glow">
<div class="auth-brand">""" + MARK + """<span class="logo">Pay Gateway</span></div>
<div class="auth-kicker">Restricted area</div><h1>Administrator sign in</h1>
<p class="auth-sub">Sign in with your administrator credentials to access gateway controls and platform settings.</p>
""" + FLASH + """
<form method="post" action="/admin/login" autocomplete="on"><input type="hidden" name="csrf" value="{{ csrf }}">
<label for="admin-user">Admin username</label><input id="admin-user" name="username" required autocomplete="username" autocapitalize="off" placeholder="Administrator username">
<label for="pw">Password</label><div class="pw"><input id="pw" name="password" type="password" required autocomplete="current-password" placeholder="Enter admin password"><button type="button" class="eye" onclick="sp(this)">Show</button></div>
<button class="btn full" type="submit">Access admin panel →</button></form>
<div class="auth-foot"><a href="/login">← Back to merchant login</a></div>
<div class="auth-trust"><span>●</span> Authorized administrators only</div>
</section></main>""" + _PWJS + """{% endblock %}"""

def stat(label, val, icon="chart"):
    return ('<div class="card stat"><div class="si">{{ ico(\'%s\') }}</div><div><span>%s</span><b>%s</b></div></div>' % (icon, label, val))


ORDER_ROWS = """{% for o in rows %}<tr><td>{{o.id[:8]}}</td><td>{{o.gname}}</td><td>{{o.ref or '-'}}</td><td>{{money(o.amount)}}</td>
<td><span class="tag {{ 'ok' if o.status=='paid' else 'bad' if o.status=='expired' else '' }}">{{o.status}}</span></td><td>{{ist(o.created_ts)}}</td></tr>
{% else %}<tr><td colspan="6" class="mut">No orders yet.</td></tr>{% endfor %}"""
ORDER_HEAD = "<tr><th>Order</th><th>Gateway</th><th>Ref</th><th>Amount ₹</th><th>Status</th><th>Time (IST)</th></tr>"

DASH = page('layout_user.html', 'home', 'Dashboard', """
<div class="pagehead"><h1>Hi, {{u.username}}</h1><a class="btn sm" href="/gateway/new">{{ ico('plus') }} Add gateway</a></div>
<div class="grid">""" + stat("Gateways", "{{gcount}}", "grid") + stat("Payments", "{{st.total}}", "list") + stat("Successful", "{{st.paid}}", "check") + stat("Received ₹", "{{st.sum}}", "wallet") + """</div>
<div class="card"><h2>Recent orders</h2><div class="scroll"><table>""" + ORDER_HEAD + ORDER_ROWS + """</table></div>
<p style="margin:14px 0 0"><a href="/orders">View all orders →</a></p></div>""")

GATEWAYS = page('layout_user.html', 'gateways', 'Gateways', """
<div class="pagehead"><h1>Gateways</h1><a class="btn sm" href="/gateway/new">{{ ico('plus') }} Add gateway</a></div>
{% for x in gws %}<a class="gl" href="/gateway/{{x.id}}" style="color:inherit"><div class="gi">{{ ico('grid') }}</div>
<div class="gt"><b>{{x.name}}</b><span>{{ 'FamPay' if x.type=='fampay' else 'Paytm' }} · {{x.upi_id}}</span></div>
<span class="tag {{ 'ok' if x.active else 'bad' }}">{{ 'Active' if x.active else 'Off' }}</span></a>
{% else %}<div class="card center mut">No gateway yet. Tap “Add gateway” to create one.</div>{% endfor %}""")

GATEWAY_NEW = page('layout_user.html', 'add', 'Add gateway', """
<div class="pagehead"><h1>Add gateway</h1><a href="/gateways">← Back</a></div>
<div class="card"><form method="post" action="/gateway/add"><input type="hidden" name="csrf" value="{{csrf}}">
<label>Gateway type</label><select name="type" id="gt" onchange="sw()"><option value="fampay">FamPay (Gmail auto verification)</option><option value="paytm">Paytm Business (Merchant ID)</option></select>
<div class="row"><div><label>Shop name (shown to payer)</label><input name="name" required maxlength="40" placeholder="My Shop"></div>
<div><label>UPI ID</label><input name="upi_id" required placeholder="name@fam / name@paytm" autocapitalize="off" autocorrect="off"></div></div>
<div id="f_fam"><div class="note">Google Account → Security → 2-Step Verification ON → App passwords → create one (16 characters). Turn IMAP on in Gmail settings.</div>
<div class="row"><div><label>Gmail that receives FamPay emails</label><input name="gmail" type="email"></div>
<div><label>Gmail app password (16 characters)</label><input name="app_password" autocomplete="off" placeholder="xxxx xxxx xxxx xxxx"></div></div></div>
<div id="f_pt" style="display:none"><div class="note">Only your Paytm Merchant ID is needed. No Merchant Key. Payments are verified automatically.</div>
<div class="row"><div><label>Merchant ID (MID)</label><input name="mid" autocomplete="off" autocapitalize="off" placeholder="e.g. ABCDEF12345678901234"></div></div></div>
<button class="btn full">Verify &amp; create</button></form></div>
<script>function sw(){const p=document.getElementById('gt').value=='paytm';
document.getElementById('f_fam').style.display=p?'none':'block';document.getElementById('f_pt').style.display=p?'block':'none'}</script>""")


GATEWAY = page('layout_user.html', 'gateways', '{{gw.name}}', """
<div class="pagehead"><h1>{{gw.name}} <span class="tag {{ 'ok' if gw.active else 'bad' }}">{{ 'Active' if gw.active else 'Off' }}</span></h1><a href="/gateways">← Back</a></div>
<div class="card"><table><tr><th>Type</th><td>{{ 'FamPay (Gmail auto verification)' if gw.type=='fampay' else 'Paytm Business (Merchant ID)' }}</td></tr><tr><th>UPI ID</th><td>{{gw.upi_id}}</td></tr>
{% if gw.type=='fampay' %}<tr><th>Gmail</th><td>{{gw.gmail}}</td></tr>{% else %}<tr><th>Merchant ID</th><td>{{gw.mid}}</td></tr>{% endif %}<tr><th>Last check</th><td>{{last}}</td></tr>
{% if gw.last_error %}<tr><th>Last error</th><td style="color:#fca5a5">{{gw.last_error}}</td></tr>{% endif %}</table>
<h3 style="margin-top:20px">API key</h3><input readonly value="{{gw.api_key}}" onclick="this.select()">
<p class="mut">Base URL: {{base}}</p>
<div class="row" style="margin-top:14px">
{% for path,label,cls in [('test','Test connection','gray'),('test-order','Create ₹1 test order',''),('toggle','Turn ' + ('off' if gw.active else 'on'),'gray'),('regen','Regenerate API key','gray'),('delete','Delete gateway','red')] %}
<form method="post" action="/gateway/{{gw.id}}/{{path}}" style="flex:0" {% if path in ('delete','regen') %}onsubmit="return confirm('Are you sure?')"{% endif %}>
<input type="hidden" name="csrf" value="{{csrf}}"><button class="btn sm {{cls}}">{{label}}</button></form>{% endfor %}</div></div>
<div class="card"><h2>Recent orders</h2><div class="scroll"><table>
<tr><th>Order</th><th>Ref</th><th>Amount ₹</th><th>Status</th><th>UTR</th><th>Created (IST)</th><th>Webhook</th></tr>
{% for o in orders %}<tr><td>{{o.id[:8]}}</td><td>{{o.ref or '-'}}</td><td>{{money(o.amount)}}</td>
<td><span class="tag {{ 'ok' if o.status=='paid' else 'bad' if o.status=='expired' else '' }}">{{o.status}}</span></td>
<td>{{o.utr or '-'}}</td><td>{{ist(o.created_ts)}}</td><td>{{o.webhook_status or '-'}}</td></tr>
{% else %}<tr><td colspan="7" class="mut">No orders yet.</td></tr>{% endfor %}</table></div></div>""")

ORDERS = page('layout_user.html', 'orders', 'Orders', """
<div class="pagehead"><h1>Orders</h1><a class="btn sm" href="/orders.csv?gateway={{gsel or ''}}&status={{ssel}}">Download CSV</a></div>
<div class="card"><form method="get" class="row" style="margin-bottom:12px">
<div><select name="gateway"><option value="">All gateways</option>{% for x in gws %}<option value="{{x.id}}" {{ 'selected' if gsel==x.id }}>{{x.name}}</option>{% endfor %}</select></div>
<div><select name="status"><option value="">All status</option>{% for s in ['paid','pending','expired'] %}<option {{ 'selected' if ssel==s }}>{{s}}</option>{% endfor %}</select></div>
<div style="flex:0"><button class="btn gray">Filter</button></div></form>
<div class="scroll"><table><tr><th>Order</th><th>Gateway</th><th>Ref</th><th>Amount ₹</th><th>Status</th><th>UTR</th><th>Created (IST)</th><th>Paid (IST)</th></tr>
{% for o in orders %}<tr><td>{{o.id[:8]}}</td><td>{{o.gname}}</td><td>{{o.ref or '-'}}</td><td>{{money(o.amount)}}</td>
<td><span class="tag {{ 'ok' if o.status=='paid' else 'bad' if o.status=='expired' else '' }}">{{o.status}}</span></td><td>{{o.utr or '-'}}</td><td>{{ist(o.created_ts)}}</td><td>{{ist(o.paid_ts)}}</td></tr>
{% else %}<tr><td colspan="8" class="mut">No orders.</td></tr>{% endfor %}</table></div>
<div class="row" style="margin-top:14px"><div>{% if page>1 %}<a class="btn sm gray" href="?page={{page-1}}&gateway={{gsel or ''}}&status={{ssel}}">← Prev</a>{% endif %}</div>
<div style="text-align:right">{% if more %}<a class="btn sm gray" href="?page={{page+1}}&gateway={{gsel or ''}}&status={{ssel}}">Next →</a>{% endif %}</div></div></div>""")

DOCS = page('layout_user.html', 'docs', 'API docs', """
<div class="pagehead"><h1>API docs</h1></div><div class="card">
<p class="mut">Base URL: <b>{{base}}</b> &nbsp; Auth: header <code>X-API-Key: YOUR_GATEWAY_KEY</code></p>
<h3>1. Create order</h3>
<pre>POST {{base}}/api/v1/orders
Content-Type: application/json

{"amount": 100, "ref": "your-order-id",
 "webhook_url": "https://yoursite.com/hook",
 "redirect_url": "https://yoursite.com/thanks",
 "cancel_url": "https://yoursite.com/cart"}</pre>
<p class="mut">Only <code>amount</code> is required. Response:</p>
<pre>{"order_id":"...","payment_url":"{{base}}/pay/...","amount":"100.00","expires_in":300}</pre>
<p class="mut">Send the user to <code>payment_url</code>. Orders expire in 5 minutes. For FamPay the amount can be a few paise higher so each pending payment is unique; use the returned <code>amount</code>. The Back button on the payment page goes to <code>cancel_url</code> (or <code>redirect_url</code>).</p>
<h3>2. Check status</h3>
<pre>GET {{base}}/api/v1/orders/ORDER_ID   →  {"status":"pending|paid|expired", ...}</pre>
<h3>3. Webhook</h3>
<p class="mut">When paid, we POST JSON <code>{event, order_id, ref, amount, status, utr, paid_at}</code> to your webhook_url with header <code>X-Signature</code> = HMAC-SHA256 of the raw body using your API key. Always verify it, and confirm the order with the status API.</p></div>""")

ACCOUNT = page('layout_user.html', 'account', 'Account', """
<div class="pagehead"><h1>Account</h1></div>
<div class="card"><table><tr><th>Username</th><td>{{u.username}}</td></tr><tr><th>Phone</th><td>{{u.phone}}</td></tr><tr><th>Gmail</th><td>{{u.email}}</td></tr><tr><th>Joined</th><td>{{u.created}}</td></tr></table></div>
<div class="card"><h3>Change password</h3>
<form method="post" action="/change-password" class="row"><input type="hidden" name="csrf" value="{{csrf}}">
<div><label>Current password</label><input type="password" name="old" required></div>
<div><label>New password</label><input type="password" name="new" required minlength="6"></div>
<div><button class="btn">Update</button></div></form></div>""")

CHECKOUT = """{% extends 'base.html' %}{% block title %}Pay ₹{{amt}} · {{gw.name}}{% endblock %}
{% block body %}<div class="page"><div class="co">
<a class="back" href="#" onclick="goBack();return false"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7"/></svg>Back</a>
<div class="card glow center" style="padding:26px 22px">
<div class="cohead"><div class="brand">""" + MARK + """<span class="nm">{{gw.name}}</span></div><span class="secure">&#128274; Secure</span></div>
<div id="pending">
<div class="mut">Amount to pay</div>
<div class="amt">₹{{amt}}</div>
<div class="mut" style="margin-top:4px">Order {{o.id[:8]}}</div>
{% if gw.type=='fampay' %}<div class="flash warn" style="margin:14px 0 0;text-align:left">Pay exactly ₹{{amt}}, including the paise, or it will not be detected.</div>{% endif %}
<div id="qr" class="qrbox"></div>
<div class="mut">Scan with any UPI app</div>
<div class="upirow"><div><small>Pay to UPI ID</small><b id="upi">{{gw.upi_id}}</b></div><button class="btn sm gray" type="button" onclick="cp()" id="cpb">Copy</button></div>
<a class="btn full" style="margin-top:6px" href="{{upi}}">Open UPI app</a>
<div class="bar"><i id="bar"></i></div>
<div class="mut"><span class="dot"></span>Waiting for payment · expires in <b id="t">--:--</b></div></div>
<div id="ok" style="display:none"><div class="big">✅</div><h2 style="margin-top:14px">Payment received</h2><p class="mut" id="rd"></p></div>
<div id="ex" style="display:none"><div class="big">⌛</div><h2 style="margin-top:14px">QR expired</h2><p class="mut">Please go back and start a new payment.</p><a class="btn" href="#" onclick="goBack();return false">Back</a></div>
</div></div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<script>
const link={{upi|tojson}}, redirect={{(o.redirect_url or '')|tojson}}, back={{(o.cancel_url or o.redirect_url or '')|tojson}};
function goBack(){if(back)location.href=back;else if(history.length>1)history.back();else location.href='/'}
function cp(){const v=document.getElementById('upi').textContent,b=document.getElementById('cpb');const ok=()=>{b.textContent='Copied';setTimeout(()=>b.textContent='Copy',1500)};
if(navigator.clipboard)navigator.clipboard.writeText(v).then(ok,ok);else ok()}
if(window.QRCode)new QRCode(document.getElementById('qr'),{text:link,width:210,height:210});
let left={{remaining}};const total=Math.max(1,left);
function show(id){for(const x of['pending','ok','ex'])document.getElementById(x).style.display=x==id?'block':'none'}
function tick(){const m=String(Math.floor(left/60)).padStart(2,'0'),s=String(left%60).padStart(2,'0');document.getElementById('t').textContent=m+':'+s;document.getElementById('bar').style.width=(left/total*100)+'%'}
tick();
setInterval(()=>{left=Math.max(0,left-1);tick();if(left==0&&document.getElementById('pending').style.display!='none')poll(true)},1000);
const st={{o.status|tojson}};
if(st=='paid')done();else if(st=='expired')show('ex');else poll();
function done(){show('ok');if(redirect){document.getElementById('rd').textContent='Redirecting…';setTimeout(()=>location.href=redirect,2000)}}
let busy=false;
async function poll(once){if(busy&&!once)return;busy=true;try{const r=await fetch('/pay/{{o.id}}/status');const d=await r.json();
if(d.status=='paid')return done();if(d.status=='expired')return show('ex');left=d.remaining}catch(e){}busy=false;if(!once)setTimeout(poll,1500)}
</script>{% endblock %}"""


ADMIN_HOME = page('layout_admin.html', 'home', 'Overview', """
<div class="pagehead"><h1>Overview</h1></div>
<div class="grid">""" + stat("Gateways", "{{gw.n}}", "grid") + stat("Paid orders", "{{ost.p or 0}}", "check") + stat("Total orders", "{{ost.n or 0}}", "list") + stat("Revenue today ₹", "{{money(ost.t or 0)}}", "wallet") + stat("Revenue total ₹", "{{money(ost.s or 0)}}", "wallet") + """</div>
<div class="card"><h2>Latest payments</h2><div class="scroll"><table>""" + ORDER_HEAD + ORDER_ROWS + """</table></div></div>
<div class="grid"><a class="card" href="/gateway/new"><h2>＋ Add a gateway</h2><p class="mut">Connect FamPay or Paytm merchant credentials.</p></a>
<a class="card" href="/docs"><h2>API Documentation</h2><p class="mut">Connect your existing bot using the API token and base URL.</p></a></div>""")

ADMIN_USERS = page('layout_admin.html', 'users', 'Users', """
<div class="pagehead"><h1>Users</h1></div>
<div class="grid">""" + stat("Total", "{{stats.total}}", "users") + stat("Active", "{{stats.active}}", "check") + stat("Banned", "{{stats.banned}}", "shield") + """</div>
<div class="card">
<form method="get" class="row" style="margin-bottom:12px"><input name="q" value="{{q}}" placeholder="Search username / phone / gmail"><button class="btn gray" style="flex:0">Search</button></form>
<div class="scroll"><table><tr><th>ID</th><th>Username</th><th>Phone</th><th>Gmail</th><th>Status</th><th>Joined</th><th>Actions</th></tr>
{% for x in users %}<tr><td>{{x.id}}</td><td>{{x.username}}</td><td>{{x.phone}}</td><td>{{x.email}}</td>
<td><span class="tag {{ 'bad' if x.banned else 'ok' }}">{{ 'Banned' if x.banned else 'Active' }}</span></td><td>{{x.created}}</td>
<td style="min-width:260px">
<details><summary>Edit / Password</summary>
<form method="post" action="/admin/user/{{x.id}}/update"><input type="hidden" name="csrf" value="{{csrf}}">
<label>Phone</label><input name="phone" value="{{x.phone}}"><label>Gmail</label><input name="email" value="{{x.email}}">
<button class="btn sm" style="margin-top:8px">Save</button></form>
<form method="post" action="/admin/user/{{x.id}}/password"><input type="hidden" name="csrf" value="{{csrf}}">
<label>New password (blank = auto-generate)</label><input name="password">
<button class="btn sm gray" style="margin-top:8px">Set / Reset password</button></form></details>
<form method="post" action="/admin/user/{{x.id}}/toggle" style="display:inline"><input type="hidden" name="csrf" value="{{csrf}}">
<button class="btn sm {{ 'green' if x.banned else 'gray' }}">{{ 'Unban' if x.banned else 'Ban' }}</button></form>
<form method="post" action="/admin/user/{{x.id}}/delete" style="display:inline" onsubmit="return confirm('Delete this user?')"><input type="hidden" name="csrf" value="{{csrf}}">
<button class="btn sm red">Delete</button></form></td></tr>
{% else %}<tr><td colspan="7" class="mut">No users yet.</td></tr>{% endfor %}</table></div></div>""")

ADMIN_GW = page('layout_admin.html', 'gws', 'Gateways', """
<div class="pagehead"><h1>Gateways &amp; Orders</h1></div>
<div class="grid">""" + stat("Orders", "{{ost.n}}", "list") + stat("Paid", "{{ost.p or 0}}", "check") + stat("Revenue total ₹", "{{money(ost.s or 0)}}", "wallet") + stat("Revenue today ₹", "{{money(ost.t or 0)}}", "wallet") + """</div>
<div class="card"><h2>All gateways</h2><div class="scroll"><table>
<tr><th>ID</th><th>Owner</th><th>Name</th><th>UPI</th><th>Type / Account</th><th>Orders</th><th>Paid</th><th>Status</th><th>Last error</th><th></th></tr>
{% for x in gws %}<tr><td>{{x.id}}</td><td>{{x.username}}</td><td>{{x.name}}</td><td>{{x.upi_id}}</td><td>{{x.type}} · {{x.gmail or x.mid}}</td><td>{{x.n}}</td><td>{{x.p or 0}}</td>
<td><span class="tag {{ 'ok' if x.active else 'bad' }}">{{ 'Active' if x.active else 'Off' }}</span></td><td>{{x.last_error or '-'}}</td>
<td style="white-space:nowrap"><form method="post" action="/admin/gateway/{{x.id}}/toggle" style="display:inline"><input type="hidden" name="csrf" value="{{csrf}}"><button class="btn sm gray">{{ 'Off' if x.active else 'On' }}</button></form>
<form method="post" action="/admin/gateway/{{x.id}}/delete" style="display:inline" onsubmit="return confirm('Delete gateway?')"><input type="hidden" name="csrf" value="{{csrf}}"><button class="btn sm red">Delete</button></form></td></tr>
{% else %}<tr><td colspan="10" class="mut">No gateways.</td></tr>{% endfor %}</table></div></div>
<div class="card"><h2>Latest orders</h2><div class="scroll"><table>
<tr><th>Order</th><th>Gateway</th><th>Ref</th><th>Amount ₹</th><th>Status</th><th>UTR</th><th>Created (IST)</th><th>Webhook</th><th></th></tr>
{% for o in orders %}<tr><td>{{o.id[:8]}}</td><td>{{o.gateway_id}}</td><td>{{o.ref or '-'}}</td><td>{{money(o.amount)}}</td><td>{{o.status}}</td><td>{{o.utr or '-'}}</td><td>{{ist(o.created_ts)}}</td><td>{{o.webhook_status or '-'}}</td>
<td>{% if o.status!='paid' %}<form method="post" action="/admin/order/{{o.id}}/paid" onsubmit="return confirm('Mark as paid manually?')"><input type="hidden" name="csrf" value="{{csrf}}"><button class="btn sm green">Mark paid</button></form>{% endif %}</td></tr>
{% else %}<tr><td colspan="9" class="mut">No orders.</td></tr>{% endfor %}</table></div></div>""")

ADMIN_SET = page('layout_admin.html', 'set', 'Settings', """
<div class="pagehead"><h1>Settings &amp; Backup</h1></div>
<div class="card"><h2>Settings</h2><form method="post"><input type="hidden" name="csrf" value="{{csrf}}">
<label>Public base URL (used in API docs and payment links; blank = auto)</label><input name="base_url" value="{{s.base_url}}" placeholder="https://yourname.onrender.com">
<label>FamPay email sender filter (part of the From address)</label><input name="fampay_sender" value="{{s.fampay_sender}}">
<label>Payment-received keywords in the email (comma separated, any one must match)</label><input name="fampay_keywords" value="{{s.fampay_keywords}}">
<label>Order / QR expiry (minutes)</label><input name="order_expiry_min" type="number" min="3" max="120" value="{{s.order_expiry_min}}">
<label>Paytm environment</label><select name="paytm_env"><option value="prod" {{ 'selected' if s.paytm_env!='stage' }}>Production</option><option value="stage" {{ 'selected' if s.paytm_env=='stage' }}>Staging (test)</option></select>
<h3 style="margin-top:22px">Auto backup (every 12 hours)</h3>
<p class="mut">Set a Telegram bot token and your chat ID and every backup is sent to you as a file. Leave the token blank to keep the saved one.</p>
<div class="row"><div><label>Telegram bot token</label><input name="tg_token" type="password" placeholder="{{ 'saved' if s.tg_token else 'not set' }}" autocomplete="off"></div>
<div><label>Telegram chat ID</label><input name="tg_chat" value="{{s.tg_chat}}"></div></div>
<p class="mut">Last backup: {{last_backup}} · {{s.last_backup_msg or '-'}}</p>
<button class="btn full">Save</button></form></div>
<div class="card"><h2>Backup &amp; restore</h2>
<div class="row"><a class="btn" href="/admin/backup" style="flex:0">Download backup</a>
<form method="post" action="/admin/backup-now" style="flex:0"><input type="hidden" name="csrf" value="{{csrf}}"><button class="btn gray">Backup now (Telegram)</button></form></div>
<form method="post" action="/admin/restore" enctype="multipart/form-data" class="row" style="margin-top:16px"><input type="hidden" name="csrf" value="{{csrf}}">
<input type="file" name="file" required><button class="btn gray" style="flex:0">Restore</button></form></div>""")

ERROR_PAGE = """{% extends 'base.html' %}{% block title %}Temporary error · Pay Gateway{% endblock %}
{% block body %}<main class="auth-shell"><section class="auth glow center">
<div class="auth-brand">""" + MARK + """<span class="logo">Pay Gateway</span></div>
<div class="big" style="font-size:42px;margin:8px 0 18px">500</div><h1>Something went wrong</h1>
<p class="auth-sub">The server could not complete this request. Your account data has not been intentionally changed. Please try again in a moment.</p>
<a class="btn full" href="/login">Return to login</a><div class="auth-foot">If this keeps happening, contact the site administrator.</div>
</section></main>{% endblock %}"""


TEMPLATES = {"base.html": BASE, "icons.html": ICONS, "layout_user.html": LAYOUT_USER, "layout_admin.html": LAYOUT_ADMIN,
  "auth.html": AUTH, "admin_login.html": ADMIN_LOGIN, "error.html": ERROR_PAGE, "dash.html": DASH, "gateways.html": GATEWAYS, "gateway_new.html": GATEWAY_NEW,
  "gateway.html": GATEWAY, "orders.html": ORDERS, "docs.html": DOCS, "account.html": ACCOUNT, "checkout.html": CHECKOUT,
  "admin_home.html": ADMIN_HOME, "admin_users.html": ADMIN_USERS, "admin_gw.html": ADMIN_GW, "admin_set.html": ADMIN_SET}
