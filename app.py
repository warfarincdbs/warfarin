import os, re, requests
from flask import Flask, request, abort
from dotenv import load_dotenv
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    TextMessage, ReplyMessageRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# โหลด .env
load_dotenv()
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
google_script_url = os.getenv("GOOGLE_SCRIPT_URL")

app = Flask(__name__)
handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=access_token)
messaging_api = MessagingApi(ApiClient(configuration))

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip().lower()
    reply_token = event.reply_token

    # ✅ บันทึกค่า INR
    match = re.match(r"inr\s*([0-9.]+)", text)
    if match:
        inr = float(match.group(1))
        requests.post(google_script_url, json={"user_id": user_id, "inr_value": inr})
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=f"✅ บันทึก INR {inr} แล้ว")]
            )
        )
        return

    # ✅ ดูประวัติ INR
    if "ดูประวัติ" in text:
        resp = requests.get(google_script_url)
        data = resp.json()
        user_logs = [f"• {row[1]} เมื่อ {row[2]}" for row in data if row[0] == user_id][-5:]
        msg = "📋 ประวัติ INR ล่าสุด:\n" + "\n".join(user_logs) if user_logs else "ยังไม่มีประวัติ"
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=msg)]
            )
        )
        return
    if __name__ == "__main__":
    app.run(port=5000)