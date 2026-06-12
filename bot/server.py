import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8634108372:AAFD4jb69EGfqsNQr1ySLR6C0gB-IzlaDEE")
CHAT_ID = os.environ.get("CHAT_ID", "")
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

@app.route("/", methods=["GET"])
def index():
    return "SiteForge AI Bot is running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    name = data.get("name", "Не указано")
    phone = data.get("phone", "Не указан")
    email = data.get("email", "Не указан")
    description = data.get("description", "Не указано")

    msg = (
        f"\U0001F525 <b>Новая заявка! Сайт за 1000\u20BD</b>\n\n"
        f"\U0001F464 <b>Имя:</b> {name}\n"
        f"\U0001F4DE <b>Телефон:</b> {phone}\n"
        f"\U0001F4E7 <b>Email:</b> {email}\n"
        f"\U0001F4CB <b>Описание:</b>\n{description}"
    )

    try:
        resp = requests.post(BOT_URL, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=10)
        if resp.status_code != 200:
            return jsonify({"ok": False, "error": resp.text}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
