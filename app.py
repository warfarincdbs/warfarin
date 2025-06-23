from flask import Flask, request, jsonify, abort
import os
import requests
from datetime import datetime
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    TextMessage, ReplyMessageRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
from dotenv import load_dotenv
load_dotenv()

# ====== LINE API Setup ======
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=access_token)
messaging_api = MessagingApi(ApiClient(configuration))

# ====== Flask Setup ======
app = Flask(__name__)

# ====== Google Apps Script Webhook URL ======
GOOGLE_APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbza1rHmPavl3SynzKN0Y9D_TFxd3gSmGNUVvgScdrip0DTpyXUu43d70KvOeApzJHBV9g/exec"

# ====== In-Memory Session ======
user_sessions = {}

# ====== ฟังก์ชันส่งข้อมูลไป Google Sheet ======
def send_to_google_sheet(user_id, name, inr, bleeding="", supplement=""):
    payload = {
        "userId": user_id,
        "name": name,
        "inr": inr,
        "bleeding": bleeding,
        "supplement": supplement
    }

    try:
        response = requests.post(GOOGLE_APPS_SCRIPT_URL, json=payload, timeout=10)
        return response.text
    except Exception as e:
        return f"❌ Error: {str(e)}"

# ====== หน้า Home ======
@app.route("/", methods=["GET"])
def home():
    return "✅ Flask on Render is live"

# ====== API POST โดยตรงแบบ REST (Optional) ======
@app.route("/log_inr", methods=["POST"])
def log_inr():
    data = request.get_json()
    userId = data.get("user_id")
    name = data.get("name")
    inr = data.get("inr")
    bleeding = data.get("bleeding", "")
    supplement = data.get("supplement", "")

    if not (userId and name and inr):
        return jsonify({"error": "Missing required fields"}), 400

    result = send_to_google_sheet(userId, name, inr, bleeding, supplement)
    return jsonify({"status": "sent", "google_response": result})

# ====== Webhook Endpoint (LINE) ======
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# ====== LINE Message Handler ======
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    text = event.message.text.strip()

    # เริ่มต้น flow
    if text == "เริ่มต้นใช้งาน":
        user_sessions[user_id] = {"step": "ask_name"}
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="👤 กรุณาพิมพ์ชื่อ-นามสกุลของคุณ")
            ])
        )
        return

    # ถามชื่อ
    if user_id in user_sessions and user_sessions[user_id]["step"] == "ask_name":
        user_sessions[user_id]["name"] = text
        user_sessions[user_id]["step"] = "ask_inr"
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="🧪 กรุณาพิมพ์ค่า INR เช่น 2.7")
            ])
        )
        return

    # ถามค่า INR
    if user_sessions[user_id]["step"] == "ask_inr":
        try:
            inr = float(text)
            user_sessions[user_id]["inr"] = inr
            user_sessions[user_id]["step"] = "ask_bleeding"
            messaging_api.reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=[
                    TextMessage(text="🩸 มีภาวะเลือดออกหรือไม่? (yes/no)")
                ])
            )
        except ValueError:
            messaging_api.reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=[
                    TextMessage(text="❌ กรุณาพิมพ์ INR เป็นตัวเลข เช่น 2.7")
                ])
            )
        return

    # ถาม bleeding
    if user_sessions[user_id]["step"] == "ask_bleeding":
        if text.lower() not in ["yes", "no"]:
            messaging_api.reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=[
                    TextMessage(text="❌ กรุณาพิมพ์ yes หรือ no เท่านั้น")
                ])
            )
            return
        user_sessions[user_id]["bleeding"] = text.lower()
        user_sessions[user_id]["step"] = "ask_supplement"
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="🌿 มีการใช้สมุนไพร/อาหารเสริมหรือไม่? (ถ้าไม่มี พิมพ์ 'ไม่มี')")
            ])
        )
        return

    # ✅ สุดท้าย: บันทึก Supplement และส่งไป Google Sheet
    if user_sessions[user_id]["step"] == "ask_supplement":
        session = user_sessions.pop(user_id)
        session["supplement"] = text

        result = send_to_google_sheet(
            user_id=user_id,
            name=session["name"],
            inr=session["inr"],
            bleeding=session["bleeding"],
            supplement=session["supplement"]
        )

        reply = f"""✅ ข้อมูลถูกบันทึกเรียบร้อยแล้ว
👤 {session['name']}
🧪 INR: {session['inr']}
🩸 Bleeding: {session['bleeding']}
🌿 Supplement: {session['supplement']}"""

        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=reply)])
        )
        return

    # กรณีไม่มี session
    if user_id not in user_sessions:
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="❓ พิมพ์ 'เริ่มต้นใช้งาน' เพื่อบันทึกข้อมูล INR")
            ])
        )

# ====== Run App ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)