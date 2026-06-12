import os, json, uuid, io, zipfile, smtplib, logging, threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

tpool = ThreadPoolExecutor(max_workers=4)

import requests
from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from flask_cors import CORS

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("siteforge")

app = Flask(__name__, template_folder="templates")
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8634108372:AAFD4jb69EGfqsNQr1ySLR6C0gB-IzlaDEE")
CHAT_ID = os.environ.get("CHAT_ID", "1000583946")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
SENDGRID_KEY = os.environ.get("SENDGRID_API_KEY", "")
SENDGRID_FROM = os.environ.get("SENDGRID_FROM", "paternmod@gmail.com")
BASE_URL = os.environ.get("BASE_URL", "https://siteforge-bot.onrender.com")
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

ORDERS_FILE = "/tmp/siteforge_orders.json"

def load_orders():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_orders(data):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_order(order_id):
    orders = load_orders()
    return orders.get(order_id)

def set_order(order_id, data):
    orders = load_orders()
    orders[order_id] = data
    save_orders(orders)

CLARIFYING_QUESTIONS = [
    {"key": "business_type", "q": "Какой у вас бизнес или проект? Опишите чем занимаетесь.", "hint": "например: кофейня, школа английского, стоматология, портфолио фотографа"},
    {"key": "goal", "q": "Какая главная цель сайта?", "hint": "например: продажи, запись клиентов, портфолио, информирование"},
    {"key": "sections", "q": "Какие разделы должны быть на сайте?", "hint": "например: главная, услуги, цены, портфолио, контакты, форма записи, отзывы"},
    {"key": "style", "q": "Какой стиль предпочитаете? Пришлите ссылки на сайты-примеры если есть.", "hint": "например: тёмная тема, минимализм, яркий, строгий бизнес-стиль"},
    {"key": "colors", "q": "Какие цвета используете? Есть ли брендбук или логотип?", "hint": "например: синий + белый, зелёный, корпоративные цвета компании"},
    {"key": "pages_count", "q": "Сколько страниц нужно? Одностраничный сайт (лендинг) или многостраничный?", "hint": "одностраничный — вся информация на одной странице"},
    {"key": "special", "q": "Есть ли особые требования? Кастомный функционал, анимации, интеграции?", "hint": "например: калькулятор, онлайн-запись, корзина, карта"},
    {"key": "audience", "q": "Кто ваша целевая аудитория?", "hint": "например: молодые родители, бизнесмены, студенты, пенсионеры"},
]



PROMO_TEXT = """
\u26A1 \u0421\u0430\u0439\u0442 \u0437\u0430 1000\u20BD \u0437\u0430 24 \u0447\u0430\u0441\u0430!
\u0417\u0430\u043A\u0430\u0436\u0438\u0442\u0435 \u043D\u0430 \u0441\u0430\u0439\u0442\u0435: https://mrwudrock.github.io/siteforge-landing/
"""

SYSTEM_PROMPT = """\
\u0422\u044B \u0432\u0435\u0431-\u0440\u0430\u0437\u0440\u0430\u0431\u043E\u0442\u0447\u0438\u043A \u044D\u043A\u0441\u043F\u0435\u0440\u0442. \u0421\u043E\u0437\u0434\u0430\u0439 \u043F\u043E\u043B\u043D\u043E\u0446\u0435\u043D\u043D\u044B\u0439 \u043E\u0434\u043D\u043E\u0441\u0442\u0440\u0430\u043D\u0438\u0447\u043D\u044B\u0439 \u0441\u0430\u0439\u0442 \u043D\u0430 \u043E\u0441\u043D\u043E\u0432\u0435 \u0422\u0417.
\u041E\u0442\u0432\u0435\u0442\u044C \u0442\u043E\u043B\u044C\u043A\u043E \u043A\u043E\u0434\u043E\u043C HTML (\u0431\u0435\u0437 markdown, \u0431\u0435\u0437 \u043E\u0431\u044A\u044F\u0441\u043D\u0435\u043D\u0438\u0439).
\u0412\u0435\u0441\u044C CSS \u0434\u043E\u043B\u0436\u0435\u043D \u0431\u044B\u0442\u044C \u0432\u043D\u0443\u0442\u0440\u0438 <style> \u0432 <head>.
\u0412\u0435\u0441\u044C JS \u0434\u043E\u043B\u0436\u0435\u043D \u0431\u044B\u0442\u044C \u0432\u043D\u0443\u0442\u0440\u0438 <script> \u0432 \u043A\u043E\u043D\u0446\u0435 body.
\u042F\u0437\u044B\u043A \u0441\u0430\u0439\u0442\u0430 \u0440\u0443\u0441\u0441\u043A\u0438\u0439.
\u0422\u0440\u0435\u0431\u043E\u0432\u0430\u043D\u0438\u044F:
- \u0421\u043E\u0432\u0440\u0435\u043C\u0435\u043D\u043D\u044B\u0439 \u0434\u0438\u0437\u0430\u0439\u043D
- \u0410\u0434\u0430\u043F\u0442\u0438\u0432 \u043F\u043E\u0434 \u043C\u043E\u0431\u0438\u043B\u044C\u043D\u044B\u0435 (mobile first)
- \u041F\u043B\u0430\u0432\u043D\u0430\u044F \u0430\u043D\u0438\u043C\u0430\u0446\u0438\u044F \u043F\u0440\u0438 \u0441\u043A\u0440\u043E\u043B\u043B\u0435
- \u0424\u043E\u0440\u043C\u0430 \u0437\u0430\u044F\u0432\u043A\u0438 / \u043A\u043E\u043D\u0442\u0430\u043A\u0442\u043E\u0432
- \u041E\u043F\u0442\u0438\u043C\u0438\u0437\u0430\u0446\u0438\u044F \u0434\u043B\u044F \u0431\u044B\u0441\u0442\u0440\u043E\u0439 \u0437\u0430\u0433\u0440\u0443\u0437\u043A\u0438
"""


def send_tg(msg):
    tpool.submit(_send_tg, msg)

def _send_tg(msg):
    try:
        requests.post(BOT_URL, json={"chat_id": CHAT_ID, "text": msg,
                      "parse_mode": "HTML"}, timeout=15)
    except Exception as e:
        log.warning(f"tg send fail: {e}")


def send_email(to, subject, html, reply_to=None):
    tpool.submit(_send_email, to, subject, html, reply_to)

def _send_email(to, subject, html, reply_to=None):
    # Try SendGrid first (works on Render)
    if SENDGRID_KEY:
        try:
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {SENDGRID_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "personalizations": [{"to": [{"email": to}], "subject": subject}],
                    "from": {"email": SENDGRID_FROM},
                    "content": [{"type": "text/html", "value": html}]
                },
                timeout=15
            )
            if resp.status_code in (200, 201, 202):
                log.info(f"email sent via SendGrid to {to}")
                return
            else:
                log.error(f"SendGrid error {resp.status_code}: {resp.text}")
        except Exception as e:
            log.error(f"SendGrid fail: {e}")
        return

    # Fallback to SMTP
    if not SMTP_USER or not SMTP_PASS:
        log.info(f"[EMAIL MOCK] To: {to}, Subject: {subject}")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.attach(MIMEText(html, "html"))
        use_ssl = (SMTP_PORT == 465)
        if use_ssl:
            srv = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
        else:
            srv = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            srv.starttls()
        srv.login(SMTP_USER, SMTP_PASS)
        srv.sendmail(SMTP_FROM, [to], msg.as_string())
        srv.quit()
        log.info(f"email sent via SMTP to {to}")
    except Exception as e:
        log.error(f"SMTP fail: {e}")


def build_tz_text(answers):
    parts = []
    for q in CLARIFYING_QUESTIONS:
        val = answers.get(q["key"], "").strip()
        if val:
            parts.append(f"{q['q']} {val}")
    revision = answers.get("_revision", "").strip()
    if revision:
        parts.append(f"\u041F\u0440\u0430\u0432\u043A\u0438 \u043A\u043B\u0438\u0435\u043D\u0442\u0430: {revision}")
    return "\n".join(parts)


def call_openai(tz_text):
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
        json={"model": "gpt-4o-mini", "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": tz_text}
        ], "temperature": 0.7, "max_tokens": 8192},
        timeout=120
    )
    if resp.status_code != 200:
        log.error(f"OpenAI error: {resp.status_code} {resp.text[:200]}")
        return None
    html = resp.json()["choices"][0]["message"]["content"]
    html = html.strip()
    if html.startswith("```html"): html = html[7:]
    elif html.startswith("```"): html = html[3:]
    if html.endswith("```"): html = html[:-3]
    return html.strip()


def call_claude(tz_text):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                 "Content-Type": "application/json"},
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 8192,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": tz_text}]
        },
        timeout=120
    )
    if resp.status_code != 200:
        log.error(f"Claude error: {resp.status_code} {resp.text[:200]}")
        return None
    html = resp.json()["content"][0]["text"]
    html = html.strip()
    if html.startswith("```html"): html = html[7:]
    elif html.startswith("```"): html = html[3:]
    if html.endswith("```"): html = html[:-3]
    return html.strip()


def generate_demo(tz_text, name):
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{name} — SiteForge AI</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:#0a0a0f;color:#e8e8f0;line-height:1.6}}
.hero{{padding:80px 20px;text-align:center;background:linear-gradient(135deg,#0a0a0f 0%,#1a1a2e 100%)}}
.hero h1{{font-size:clamp(2rem,5vw,3rem);background:linear-gradient(135deg,#3b82f6,#8b5cf6,#f97316);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:16px}}
.hero p{{color:#8888a0;font-size:1.1rem;max-width:600px;margin:0 auto 32px}}
.container{{max-width:1100px;margin:0 auto;padding:0 20px}}
.section{{padding:60px 0;border-bottom:1px solid rgba(255,255,255,0.05)}}
.section h2{{font-size:1.8rem;margin-bottom:24px;color:#3b82f6}}
.section p{{color:#b0b0c0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:24px;margin-top:24px}}
.card{{background:#12121a;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:24px}}
.card h3{{margin-bottom:8px;font-size:1.1rem}}
.card p{{color:#8888a0;font-size:0.95rem}}
.contact{{padding:60px 20px;text-align:center;background:linear-gradient(135deg,#12121a 0%,#0a0a0f 100%)}}
.contact h2{{font-size:1.8rem;margin-bottom:16px}}
.btn{{display:inline-block;padding:14px 36px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;text-decoration:none;border-radius:8px;font-weight:700;margin-top:16px}}
@media(max-width:768px){{.hero{{padding:40px 20px}}}}
</style>
</head>
<body>
<section class="hero">
<h1>{name}</h1>
<p>Сайт создан AI-агентом SiteForge AI. Заполните этот шаблон своими данными.</p>
<a class="btn" href="#contact">Связаться</a>
</section>
<section class="section">
<div class="container">
<h2>О нас</h2>
<p>Мы — {name}. Добавьте сюда описание вашей компании,产品或 услуг.</p>
<div class="grid">
<div class="card"><h3>Услуга 1</h3><p>Опишите первую услугу</p></div>
<div class="card"><h3>Услуга 2</h3><p>Опишите вторую услугу</p></div>
<div class="card"><h3>Услуга 3</h3><p>Опишите третью услугу</p></div>
</div>
</div>
</section>
<section class="contact" id="contact">
<div class="container">
<h2>Свяжитесь с нами</h2>
<p>Телефон: +7 (999) 000-00-00<br>Email: info@{name.lower().replace(' ','')}.ru</p>
</div>
</section>
</body>
</html>"""


def generate_site(answers):
    name = answers.get("business_type", "Мой сайт").strip() or "Мой сайт"
    tz_text = build_tz_text(answers)

    if not tz_text.strip():
        tz_text = "Создай одностраничный сайт с секциями: герой, о нас, услуги, контакты."

    if ANTHROPIC_KEY:
        log.info("Trying Claude...")
        result = call_claude(tz_text)
        if result:
            return result

    if OPENAI_KEY:
        log.info("Trying OpenAI...")
        result = call_openai(tz_text)
        if result:
            return result

    log.info("No AI keys configured, using demo template")
    return generate_demo(tz_text, name)


def make_zip(order_id, html_content):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("index.html", html_content)
        instructions = f"""\
==========================================
  \u0421\u0430\u0439\u0442 \u0441\u043E\u0437\u0434\u0430\u043D AI-\u0430\u0433\u0435\u043D\u0442\u043E\u043C SiteForge AI
  \u0417\u0430\u043A\u0430\u0437 #{order_id}
  \u0414\u0430\u0442\u0430: {datetime.now().strftime('%d.%m.%Y %H:%M')}
==========================================

\u041A\u0410\u041A \u0417\u0410\u041F\u0423\u0421\u0422\u0418\u0422\u042C \u0421\u0410\u0419\u0422:

\u0412\u0430\u0440\u0438\u0430\u043D\u0442 1 \u2014 \u041E\u0442\u043A\u0440\u044B\u0442\u044C \u043B\u043E\u043A\u0430\u043B\u044C\u043D\u043E:
1. \u0420\u0430\u0441\u043F\u0430\u043A\u0443\u0439\u0442\u0435 \u0430\u0440\u0445\u0438\u0432
2. \u0414\u0432\u0430\u0436\u0434\u044B \u043A\u043B\u0438\u043A\u043D\u0438\u0442\u0435 index.html
3. \u0421\u0430\u0439\u0442 \u043E\u0442\u043A\u0440\u043E\u0435\u0442\u0441\u044F \u0432 \u0431\u0440\u0430\u0443\u0437\u0435\u0440\u0435

\u0412\u0430\u0440\u0438\u0430\u043D\u0442 2 \u2014 \u041E\u043F\u0443\u0431\u043B\u0438\u043A\u043E\u0432\u0430\u0442\u044C \u0432 \u0438\u043D\u0442\u0435\u0440\u043D\u0435\u0442\u0435:

--- Netlify (\u0431\u0435\u0441\u043F\u043B\u0430\u0442\u043D\u043E, 2 \u043A\u043B\u0438\u043A\u0430) ---
1. \u0417\u0430\u0439\u0434\u0438\u0442\u0435 \u043D\u0430 https://app.netlify.com/drop
2. \u041F\u0435\u0440\u0435\u0442\u0430\u0449\u0438\u0442\u0435 \u043F\u0430\u043F\u043A\u0443 \u0441 \u0441\u0430\u0439\u0442\u043E\u043C \u0432 \u043E\u043A\u043D\u043E
3. \u0413\u043E\u0442\u043E\u0432\u043E! \u0421\u0441\u044B\u043B\u043A\u0430 \u0432\u0438\u0434\u0430 site-name.netlify.app

--- GitHub Pages ---
1. \u0421\u043E\u0437\u0434\u0430\u0439\u0442\u0435 \u0440\u0435\u043F\u043E\u0437\u0438\u0442\u043E\u0440\u0438\u0439 \u043D\u0430 github.com
2. \u0417\u0430\u043B\u0435\u0439\u0442\u0435 \u0444\u0430\u0439\u043B\u044B
3. Settings \u2192 Pages \u2192 \u0432\u043A\u043B\u044E\u0447\u0438\u0442\u0435 GitHub Pages
4. \u0421\u0430\u0439\u0442 \u0434\u043E\u0441\u0442\u0443\u043F\u0435\u043D \u043F\u043E \u0430\u0434\u0440\u0435\u0441\u0443 \u0432\u0430\u0448-\u043B\u043E\u0433\u0438\u043D.github.io/\u0438\u043C\u044F-\u0440\u0435\u043F\u043E

--- Vercel ---
1. \u0417\u0430\u0439\u0434\u0438\u0442\u0435 \u043D\u0430 https://vercel.com/new
2. \u0412\u044B\u0431\u0435\u0440\u0438\u0442\u0435 \u043F\u0430\u043F\u043A\u0443 \u0441 \u0441\u0430\u0439\u0442\u043E\u043C
3. \u041D\u0430\u0436\u043C\u0438\u0442\u0435 Deploy
4. \u0413\u043E\u0442\u043E\u0432\u043E!

\u041F\u041E\u041B\u0415\u0417\u041D\u042B\u0415 \u0421\u0421\u042B\u041B\u041A\u0418:
- \u041A\u0443\u043F\u0438\u0442\u044C \u0434\u043E\u043C\u0435\u043D .ru: https://reg.ru
- \u0411\u0435\u0441\u043F\u043B\u0430\u0442\u043D\u044B\u0439 \u0445\u043E\u0441\u0442\u0438\u043D\u0433: https://netlify.com
- \u041F\u0440\u043E\u0432\u0435\u0440\u0438\u0442\u044C \u0441\u043A\u043E\u0440\u043E\u0441\u0442\u044C: https://pagespeed.web.dev

\u041D\u0443\u0436\u043D\u044B \u043F\u0440\u0430\u0432\u043A\u0438? \u041E\u0441\u0442\u0430\u0432\u044C\u0442\u0435 \u0437\u0430\u044F\u0432\u043A\u0443:
{revision_link}

\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014\u2014
SiteForge AI \u2014 \u041B\u044E\u0431\u043E\u0439 \u0441\u0430\u0439\u0442 \u0437\u0430 1000\u20BD
"""
        z.writestr("INSTRUCTION.txt", instructions)
    buf.seek(0)
    return buf


def send_site_notification(name, order_id):
    site_link = f"{BASE_URL}/order/{order_id}/download"
    send_tg(
        f"\u2705 <b>\u0421\u0430\u0439\u0442 \u0433\u043E\u0442\u043E\u0432!</b>\n\n"
        f"\U0001F464 {name}\n"
        f"\U0001F517 \u0417\u0430\u043A\u0430\u0437 #{order_id}\n"
        f"\U0001F4E6 \u0421\u043A\u0430\u0447\u0430\u0442\u044C: {site_link}"
    )


@app.route("/")
def index():
    return f"SiteForge AI Bot is running<br><a href='/debug'>Debug SMTP</a>"

import traceback

@app.errorhandler(500)
def handle_500(e):
    tb = traceback.format_exc()
    log.error(f"500 error: {tb}")
    return f"<pre>{tb}</pre>", 500

@app.route("/admin/orders")
def admin_orders():
    all_orders = load_orders()
    lines = [f"<b>Total orders:</b> {len(all_orders)}<br><br>"]
    for oid, odata in list(all_orders.items())[:10]:
        lines.append(f"<b>{oid}</b>: {odata.get('name')} | status: {odata.get('status')} | html: {'yes' if odata.get('html') else 'no'}<br>")
    if not all_orders:
        lines.append("No orders found.<br>")
    return "".join(lines)

@app.route("/debug")
def debug_smtp():
    import html as h
    lines = []

    if SENDGRID_KEY:
        lines.append(f"<b>SendGrid:</b> configured (key ends with ...{h.escape(SENDGRID_KEY[-8:])})<br>")
        lines.append(f"<b>From:</b> {h.escape(SENDGRID_FROM)}<br><br>")
        try:
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {SENDGRID_KEY}", "Content-Type": "application/json"},
                json={
                    "personalizations": [{"to": [{"email": SENDGRID_FROM}], "subject": "SiteForge Bot - Test"}],
                    "from": {"email": SENDGRID_FROM},
                    "content": [{"type": "text/html", "value": "<h1>Test</h1><p>SendGrid works!</p>"}]
                },
                timeout=15
            )
            if resp.status_code in (200, 201, 202):
                lines.append("<span style='color:green'>\u2705 SendGrid test email sent!</span><br>")
            else:
                lines.append(f"<span style='color:red'>\u274C SendGrid error {resp.status_code}: {h.escape(resp.text[:200])}</span><br>")
        except Exception as e:
            lines.append(f"<span style='color:red'>\u274C SendGrid error: {h.escape(str(e))}</span><br>")
    else:
        lines.append("<span style='color:orange'>\u26A0 SendGrid not configured.</span><br>")
        lines.append(f"<b>SMTP:</b> {h.escape(SMTP_SERVER)}:{SMTP_PORT}<br>")
    return "".join(lines)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    name = data.get("name", "Не указано")
    phone = data.get("phone", "Не указан")
    email = data.get("email", "")
    description = data.get("description", "")

    order_id = uuid.uuid4().hex[:12].upper()
    set_order(order_id, {
        "name": name, "phone": phone, "email": email,
        "description": description, "status": "new",
        "answers": {}, "html": None, "created": datetime.now().isoformat()
    })

    link = f"{BASE_URL}/order/{order_id}/questions"
    msg = (
        f"\U0001F525 <b>\u041D\u043E\u0432\u0430\u044F \u0437\u0430\u044F\u0432\u043A\u0430! \u0421\u0430\u0439\u0442 \u0437\u0430 1000\u20BD</b>\n\n"
        f"\U0001F464 <b>\u0418\u043C\u044F:</b> {name}\n"
        f"\U0001F4DE <b>\u0422\u0435\u043B\u0435\u0444\u043E\u043D:</b> {phone}\n"
        f"\U0001F4E7 <b>Email:</b> {email}\n"
        f"\U0001F4CB <b>\u041E\u043F\u0438\u0441\u0430\u043D\u0438\u0435:</b>\n{description}\n\n"
        f"\U0001F517 <b>\u0417\u0430\u043A\u0430\u0437:</b> #{order_id}\n"
        f"\U0001F4AC <b>\u0421\u0441\u044B\u043B\u043A\u0430 \u0434\u043B\u044F \u043A\u043B\u0438\u0435\u043D\u0442\u0430:</b>\n{link}"
    )
    send_tg(msg)

    return jsonify({"ok": True, "order_id": order_id}), 200


@app.route("/order/<order_id>/questions", methods=["GET"])
def questions_page(order_id):
    order = get_order(order_id)
    if not order:
        return "<h1>\u0417\u0430\u043A\u0430\u0437 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D</h1><p>\u041F\u0440\u043E\u0432\u0435\u0440\u044C\u0442\u0435 \u0441\u0441\u044B\u043B\u043A\u0443 \u0438\u043B\u0438 \u043E\u0431\u0440\u0430\u0442\u0438\u0442\u0435\u0441\u044C \u0432 \u043F\u043E\u0434\u0434\u0435\u0440\u0436\u043A\u0443</p>", 404
    if order["status"] in ("generating", "done"):
        return redirect(url_for("site_page", order_id=order_id))
    return render_template("questions.html", order=order, order_id=order_id, questions=CLARIFYING_QUESTIONS, base_url=BASE_URL)


@app.route("/order/<order_id>/questions", methods=["POST"])
def questions_submit(order_id):
    order = get_order(order_id)
    if not order:
        return jsonify({"error": "not found"}), 404
    answers = {q["key"]: request.form.get(q["key"], "") for q in CLARIFYING_QUESTIONS}
    order["answers"] = answers
    order["status"] = "generating"
    set_order(order_id, order)
    send_tg(f"\U0001F916 \u0413\u0435\u043D\u0435\u0440\u0438\u0440\u0443\u044E \u0441\u0430\u0439\u0442 \u0434\u043B\u044F \u0437\u0430\u043A\u0430\u0437\u0430 #{order_id}...")

    html = generate_site(answers)
    if html:
        order["html"] = html
        order["status"] = "done"
        set_order(order_id, order)
        send_site_notification(order["name"], order_id)
        return redirect(url_for("site_page", order_id=order_id))
    else:
        order["status"] = "error"
        set_order(order_id, order)
        send_tg(f"\u274C \u041E\u0448\u0438\u0431\u043A\u0430 \u0433\u0435\u043D\u0435\u0440\u0430\u0446\u0438\u0438 \u0437\u0430\u043A\u0430\u0437\u0430 #{order_id}")
        return "<h1>\u041E\u0448\u0438\u0431\u043A\u0430 \u0433\u0435\u043D\u0435\u0440\u0430\u0446\u0438\u0438</h1><p>\u041F\u043E\u043F\u0440\u043E\u0431\u0443\u0439\u0442\u0435 \u043F\u043E\u0437\u0436\u0435</p>", 500


@app.route("/order/<order_id>/site")
def site_page(order_id):
    order = get_order(order_id)
    if not order:
        return "<h1>Not found</h1>", 404
    status = order["status"]
    if status == "new":
        return redirect(url_for("questions_page", order_id=order_id))
    if status == "generating":
        return render_template("generating.html", order_id=order_id, base_url=BASE_URL)
    return render_template("site_ready.html", order=order, order_id=order_id, base_url=BASE_URL)


@app.route("/order/<order_id>/download")
def download_site(order_id):
    order = get_order(order_id)
    if not order or not order.get("html"):
        return "<h1>Not available</h1>", 404
    buf = make_zip(order_id, order["html"])
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"siteforge-{order_id}.zip"
    )


@app.route("/order/<order_id>/revision", methods=["GET"])
def revision_page(order_id):
    order = get_order(order_id)
    if not order:
        return "<h1>Not found</h1>", 404
    return render_template("revision.html", order=order, order_id=order_id, base_url=BASE_URL)


@app.route("/order/<order_id>/revision", methods=["POST"])
def revision_submit(order_id):
    order = get_order(order_id)
    if not order:
        return jsonify({"error": "not found"}), 404
    revision_text = request.form.get("revision", "")
    if not revision_text.strip():
        return redirect(url_for("revision_page", order_id=order_id))

    answers = order.get("answers", {})
    answers["_revision"] = revision_text
    order["answers"] = answers
    order["status"] = "generating"
    set_order(order_id, order)
    send_tg(f"\U0001F527 \u041F\u0440\u0430\u0432\u043A\u0438 \u0434\u043B\u044F \u0437\u0430\u043A\u0430\u0437\u0430 #{order_id}: {revision_text[:100]}")

    html = generate_site(answers)
    if html:
        order["html"] = html
        order["status"] = "done"
        set_order(order_id, order)
        send_tg(f"\u2705 \u041F\u0440\u0430\u0432\u043A\u0438 \u0433\u043E\u0442\u043E\u0432\u044B \u0434\u043B\u044F \u0437\u0430\u043A\u0430\u0437\u0430 #{order_id}\n\U0001F4E6 {BASE_URL}/order/{order_id}/download")
    else:
        order["status"] = "error"
        set_order(order_id, order)
        send_tg(f"\u274C \u041E\u0448\u0438\u0431\u043A\u0430 \u043F\u0440\u0438 \u043F\u0440\u0430\u0432\u043A\u0430\u0445 #{order_id}")

    return redirect(url_for("site_page", order_id=order_id))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
