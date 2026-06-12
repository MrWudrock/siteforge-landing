import os, json, uuid, io, zipfile, smtplib, logging, threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

tpool = ThreadPoolExecutor(max_workers=4)

import requests
from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("siteforge")

app = Flask(__name__, template_folder="templates")
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8634108372:AAFD4jb69EGfqsNQr1ySLR6C0gB-IzlaDEE")
CHAT_ID = os.environ.get("CHAT_ID", "1000583946")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.yandex.ru")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
BASE_URL = os.environ.get("BASE_URL", "https://siteforge-bot.onrender.com")
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

orders = {}

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

QUESTIONS_EMAIL_TPL = """\
<h2 style="color:#3b82f6;">\u2709\ufe0f Уточняем детали вашего сайта</h2>
<p>Здравствуйте, <strong>{name}</strong>!</p>
<p>Мы получили вашу заявку на создание сайта. Чтобы AI-агент сделал идеальный сайт, ответьте на несколько вопросов:</p>
<p style="text-align:center;margin:30px 0">
  <a href="{link}" style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;">
    \U0001F4AC Ответить на вопросы
  </a>
</p>
<p style="color:#888;font-size:13px;">Ссылка действительна 7 дней. Если возникли вопросы, пишите в Telegram @SiteForgeAIBot</p>
"""

SITE_READY_TPL = """\
<h2 style="color:#22c55e;">\u2705 Ваш сайт готов!</h2>
<p>Здравствуйте, <strong>{name}</strong>!</p>
<p>AI-агент создал сайт по вашему ТЗ. Скачайте архив с файлами и инструкцией по запуску:</p>
<p style="text-align:center;margin:30px 0">
  <a href="{link}" style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;text-decoration:none;border-radius:8px;font-weight:700;font-size:16px;">
    \U0001F4E6 Скачать сайт
  </a>
</p>
<p>Если нужно что-то поправить — <a href="{revision_link}">оставьте запрос на правку</a>.</p>
<p style="color:#888;font-size:13px;">SiteForge AI — любой сайт за 1000\u20BD</p>
"""

REVISION_CONFIRM_TPL = """\
<h2 style="color:#f97316;">\U0001F527 Правки приняты</h2>
<p>Здравствуйте, <strong>{name}</strong>!</p>
<p>Мы получили ваш запрос на правки. AI-агент вносит изменения...</p>
<p>Обновлённая версия будет доступна через несколько минут по той же ссылке:</p>
<p style="text-align:center;margin:20px 0">
  <a href="{link}" style="color:#3b82f6;">{link}</a>
</p>
"""

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
            srv = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=15)
        else:
            srv = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
            srv.starttls()
        srv.login(SMTP_USER, SMTP_PASS)
        srv.sendmail(SMTP_FROM, [to], msg.as_string())
        srv.quit()
        log.info(f"email sent to {to}")
    except smtplib.SMTPAuthenticationError:
        log.error(f"SMTP auth fail — check SMTP_USER/SMTP_PASS (use app password!)")
    except smtplib.SMTPConnectError:
        log.error(f"SMTP connect fail — check SMTP_SERVER/SMTP_PORT ({SMTP_SERVER}:{SMTP_PORT})")
    except Exception as e:
        log.error(f"email fail: {e} [{SMTP_SERVER}:{SMTP_PORT}]")


def generate_site(answers):
    if not OPENAI_KEY:
        return "<html><body><h1>Demo site</h1><p>AI not configured</p></body></html>"

    tz_parts = []
    for q in CLARIFYING_QUESTIONS:
        val = answers.get(q["key"], "").strip()
        if val:
            tz_parts.append(f"{q['q']} {val}")
    tz_text = "\n".join(tz_parts)

    prompt = f"""\
{SYSTEM_PROMPT}

\u0422\u0415\u0425\u041D\u0418\u0427\u0415\u0421\u041A\u041E\u0415 \u0417\u0410\u0414\u0410\u041D\u0418\u0415:
{tz_text}

\u0421\u043E\u0437\u0434\u0430\u0439 \u043F\u043E\u043B\u043D\u044B\u0439 \u0444\u0430\u0439\u043B index.html \u0441\u043E \u0432\u0441\u0442\u0440\u043E\u0435\u043D\u043D\u044B\u043C\u0438 CSS \u0438 JS.
"""

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": tz_text}],
                "temperature": 0.7,
                "max_tokens": 8192
            },
            timeout=120
        )
        if resp.status_code != 200:
            log.error(f"OpenAI error: {resp.text}")
            return None
        html = resp.json()["choices"][0]["message"]["content"]
        html = html.strip()
        if html.startswith("```html"):
            html = html[7:]
        if html.startswith("```"):
            html = html[3:]
        if html.endswith("```"):
            html = html[:-3]
        return html.strip()
    except Exception as e:
        log.error(f"generate fail: {e}")
        return None


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


def send_site_email(name, email, order_id):
    site_link = f"{BASE_URL}/order/{order_id}/download"
    revision_link = f"{BASE_URL}/order/{order_id}/revision"
    html = SITE_READY_TPL.format(name=name, link=site_link,
                                  revision_link=revision_link)
    send_email(email, f"\u2705 \u0412\u0430\u0448 \u0441\u0430\u0439\u0442 \u0433\u043E\u0442\u043E\u0432! \u0417\u0430\u043A\u0430\u0437 #{order_id}", html)
    send_tg(f"\u2705 \u0421\u0430\u0439\u0442 \u0433\u043E\u0442\u043E\u0432 \u0434\u043B\u044F \u0437\u0430\u043A\u0430\u0437\u0430 #{order_id} \u2014 {name} \u2014 \u043E\u0442\u043F\u0440\u0430\u0432\u043B\u0435\u043D\u043E \u043D\u0430 {email}")


@app.route("/")
def index():
    return f"SiteForge AI Bot is running<br><a href='/debug'>Debug SMTP</a>"

@app.route("/debug")
def debug_smtp():
    import html as h
    lines = [f"<b>Config:</b> {h.escape(SMTP_SERVER)}:{SMTP_PORT} | User: {h.escape(SMTP_USER)}<br><br>"]

    if not SMTP_USER or not SMTP_PASS:
        return "SMTP not configured. Set SMTP_USER and SMTP_PASS env vars."

    try:
        use_ssl = (SMTP_PORT == 465)
        if use_ssl:
            srv = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
        else:
            srv = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            srv.starttls()
        srv.login(SMTP_USER, SMTP_PASS)
        srv.quit()
        lines.append("<span style='color:green'>\u2705 Auth OK!</span><br>")

        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = SMTP_USER
        msg["Subject"] = "SiteForge Bot - SMTP Test"
        msg.attach(MIMEText("<h1>Test</h1><p>SMTP works!</p>", "html"))
        if use_ssl:
            srv2 = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
        else:
            srv2 = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
            srv2.starttls()
        srv2.login(SMTP_USER, SMTP_PASS)
        srv2.sendmail(SMTP_FROM, [SMTP_USER], msg.as_string())
        srv2.quit()
        lines.append(f"<span style='color:green'>\u2705 Test email sent!</span><br>")
        lines.append(f"Check inbox: {h.escape(SMTP_USER)}<br>")
    except smtplib.SMTPAuthenticationError:
        lines.append("<span style='color:red'>\u274C SMTP Auth error.</span><br>")
        lines.append("For mail.ru: Settings → Password and Security → App password → Generate<br>")
        lines.append("Use that app password as SMTP_PASS (NOT your regular password).<br>")
    except Exception as e:
        lines.append(f"<span style='color:red'>\u274C {h.escape(str(e))}</span><br>")
        lines.append("Tip: Try changing SMTP_PORT to 587 (STARTTLS) in env vars.<br>")
    return "".join(lines)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    name = data.get("name", "Не указано")
    phone = data.get("phone", "Не указан")
    email = data.get("email", "")
    description = data.get("description", "")

    order_id = uuid.uuid4().hex[:12].upper()
    orders[order_id] = {
        "name": name, "phone": phone, "email": email,
        "description": description, "status": "new",
        "answers": {}, "html": None, "created": datetime.now().isoformat()
    }

    msg = (
        f"\U0001F525 <b>\u041D\u043E\u0432\u0430\u044F \u0437\u0430\u044F\u0432\u043A\u0430! \u0421\u0430\u0439\u0442 \u0437\u0430 1000\u20BD</b>\n\n"
        f"\U0001F464 <b>\u0418\u043C\u044F:</b> {name}\n"
        f"\U0001F4DE <b>\u0422\u0435\u043B\u0435\u0444\u043E\u043D:</b> {phone}\n"
        f"\U0001F4E7 <b>Email:</b> {email}\n"
        f"\U0001F4CB <b>\u041E\u043F\u0438\u0441\u0430\u043D\u0438\u0435:</b>\n{description}\n\n"
        f"\U0001F517 <b>\u0417\u0430\u043A\u0430\u0437:</b> #{order_id}"
    )
    send_tg(msg)

    if email:
        q_link = f"{BASE_URL}/order/{order_id}/questions"
        html = QUESTIONS_EMAIL_TPL.format(name=name, link=q_link)
        send_email(email,
                   f"\u2709\ufe0f \u0423\u0442\u043E\u0447\u043D\u0438\u0442\u0435 \u0434\u0435\u0442\u0430\u043B\u0438 \u0434\u043B\u044F \u0441\u0430\u0439\u0442\u0430 \u2014 \u0417\u0430\u043A\u0430\u0437 #{order_id}",
                   html)
        msg2 = f"\u2709\ufe0f \u041E\u0442\u043F\u0440\u0430\u0432\u043B\u0435\u043D\u043E \u043F\u0438\u0441\u044C\u043C\u043E \u0441 \u0432\u043E\u043F\u0440\u043E\u0441\u0430\u043C\u0438 \u043A\u043B\u0438\u0435\u043D\u0442\u0443 #{order_id}"
        send_tg(msg2)

    return jsonify({"ok": True, "order_id": order_id}), 200


@app.route("/order/<order_id>/questions", methods=["GET"])
def questions_page(order_id):
    order = orders.get(order_id)
    if not order:
        return "<h1>\u0417\u0430\u043A\u0430\u0437 \u043D\u0435 \u043D\u0430\u0439\u0434\u0435\u043D</h1><p>\u041F\u0440\u043E\u0432\u0435\u0440\u044C\u0442\u0435 \u0441\u0441\u044B\u043B\u043A\u0443 \u0438\u043B\u0438 \u043E\u0431\u0440\u0430\u0442\u0438\u0442\u0435\u0441\u044C \u0432 \u043F\u043E\u0434\u0434\u0435\u0440\u0436\u043A\u0443</p>", 404
    if order["status"] in ("generating", "done"):
        return redirect(url_for("site_page", order_id=order_id))
    return render_template("questions.html", order=order, order_id=order_id, questions=CLARIFYING_QUESTIONS, base_url=BASE_URL)


@app.route("/order/<order_id>/questions", methods=["POST"])
def questions_submit(order_id):
    order = orders.get(order_id)
    if not order:
        return jsonify({"error": "not found"}), 404
    answers = {q["key"]: request.form.get(q["key"], "") for q in CLARIFYING_QUESTIONS}
    order["answers"] = answers
    order["status"] = "generating"
    send_tg(f"\U0001F916 \u0413\u0435\u043D\u0435\u0440\u0438\u0440\u0443\u044E \u0441\u0430\u0439\u0442 \u0434\u043B\u044F \u0437\u0430\u043A\u0430\u0437\u0430 #{order_id}...")

    html = generate_site(answers)
    if html:
        order["html"] = html
        order["status"] = "done"
        buf = make_zip(order_id, html)
        order["zip"] = buf
        send_site_email(order["name"], order["email"], order_id)
        return redirect(url_for("site_page", order_id=order_id))
    else:
        order["status"] = "error"
        send_tg(f"\u274C \u041E\u0448\u0438\u0431\u043A\u0430 \u0433\u0435\u043D\u0435\u0440\u0430\u0446\u0438\u0438 \u0437\u0430\u043A\u0430\u0437\u0430 #{order_id}")
        return "<h1>\u041E\u0448\u0438\u0431\u043A\u0430 \u0433\u0435\u043D\u0435\u0440\u0430\u0446\u0438\u0438</h1><p>\u041F\u043E\u043F\u0440\u043E\u0431\u0443\u0439\u0442\u0435 \u043F\u043E\u0437\u0436\u0435</p>", 500


@app.route("/order/<order_id>/site")
def site_page(order_id):
    order = orders.get(order_id)
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
    order = orders.get(order_id)
    if not order or not order.get("zip"):
        return "<h1>Not available</h1>", 404
    order["zip"].seek(0)
    return send_file(
        order["zip"],
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"siteforge-{order_id}.zip"
    )


@app.route("/order/<order_id>/revision", methods=["GET"])
def revision_page(order_id):
    order = orders.get(order_id)
    if not order:
        return "<h1>Not found</h1>", 404
    return render_template("revision.html", order=order, order_id=order_id, base_url=BASE_URL)


@app.route("/order/<order_id>/revision", methods=["POST"])
def revision_submit(order_id):
    order = orders.get(order_id)
    if not order:
        return jsonify({"error": "not found"}), 404
    revision_text = request.form.get("revision", "")
    if not revision_text.strip():
        return redirect(url_for("revision_page", order_id=order_id))

    answers = order.get("answers", {})
    answers["_revision"] = revision_text
    order["answers"] = answers
    order["status"] = "generating"
    send_tg(f"\U0001F527 \u041F\u0440\u0430\u0432\u043A\u0438 \u0434\u043B\u044F \u0437\u0430\u043A\u0430\u0437\u0430 #{order_id}: {revision_text[:100]}")

    html = generate_site(answers)
    if html:
        order["html"] = html
        order["status"] = "done"
        buf = make_zip(order_id, html)
        order["zip"] = buf
        revision_link = f"{BASE_URL}/order/{order_id}/revision"
        html_email = REVISION_CONFIRM_TPL.format(name=order["name"],
                                                   link=f"{BASE_URL}/order/{order_id}/download",
                                                   revision_link=revision_link)
        send_email(order["email"],
                   f"\U0001F527 \u0421\u0430\u0439\u0442 \u043E\u0431\u043D\u043E\u0432\u043B\u0451\u043D! \u0417\u0430\u043A\u0430\u0437 #{order_id}",
                   html_email)
        send_tg(f"\u2705 \u041F\u0440\u0430\u0432\u043A\u0438 \u0433\u043E\u0442\u043E\u0432\u044B \u0434\u043B\u044F \u0437\u0430\u043A\u0430\u0437\u0430 #{order_id}")
    else:
        order["status"] = "error"
        send_tg(f"\u274C \u041E\u0448\u0438\u0431\u043A\u0430 \u043F\u0440\u0438 \u043F\u0440\u0430\u0432\u043A\u0430\u0445 #{order_id}")

    return redirect(url_for("site_page", order_id=order_id))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
