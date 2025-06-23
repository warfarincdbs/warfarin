import os
import re
import requests
from datetime import datetime, timedelta

from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, TextMessage, ReplyMessageRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import FlexMessage
from linebot.v3.messaging.models import FlexContainer


app = Flask(__name__)

# ✅ ดึงค่าจาก Environment Variables
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
google_script_url = os.getenv("GOOGLE_SCRIPT_URL")

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=access_token)

user_sessions = {}
user_drug_selection = {}
messaging_api = MessagingApi(ApiClient(configuration))

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


def send_supplement_flex(reply_token):
    flex_content = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "🌿 สมุนไพร/อาหารเสริม", "weight": "bold", "size": "lg"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "ผู้ป่วยใช้สิ่งใดบ้าง?", "wrap": True, "size": "md"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {"type": "button", "style": "primary", "height": "sm", "color": "#84C1FF",
                         "action": {"type": "message", "label": "ไม่ได้ใช้", "text": "ไม่ได้ใช้"}},
                        *[
                            {"type": "button", "style": "primary", "height": "sm", "color": "#AEC6CF",
                             "action": {"type": "message", "label": herb, "text": herb}}
                            for herb in ["กระเทียม", "ใบแปะก๊วย", "โสม", "ขมิ้น", "น้ำมันปลา", "ใช้หลายชนิด", "สมุนไพร/อาหารเสริมชนิดอื่นๆ"]
                        ]
                    ]
                }
            ]
        },
        "styles": {
            "header": {"backgroundColor": "#D0E6FF"},
            "body": {"backgroundColor": "#FFFFFF"}
        }
    }

    flex_container = FlexContainer.from_dict(flex_content)

    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[FlexMessage(alt_text="เลือกสมุนไพร/อาหารเสริม", contents=flex_container)]
        )
    )
def send_interaction_flex(reply_token):
    interaction_drugs = [
        "Amiodarone", "Metronidazole", "Trimethoprim/Sulfamethoxazole",
        "Fluconazole", "Erythromycin", "NSAIDs", "Aspirin"
    ]
    flex_content = {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{"type": "text", "text": "💊 ยาที่อาจมีปฏิกิริยารุนแรงกับ Warfarin", "weight": "bold", "size": "lg"}]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "ผู้ป่วยได้รับยาใดบ้าง?", "wrap": True, "size": "md"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {"type": "button", "style": "primary", "height": "sm", "color": "#84C1FF",
                         "action": {"type": "message", "label": "ไม่ได้ใช้", "text": "ไม่ได้ใช้"}}
                    ] + [
                        {"type": "button", "style": "primary", "height": "sm", "color": "#FFD700",
                         "action": {"type": "message", "label": drug, "text": drug}}
                        for drug in interaction_drugs
                    ] + [
                        {"type": "button", "style": "primary", "height": "sm", "color": "#FFB6C1",
                         "action": {"type": "message", "label": "ใช้หลายชนิด", "text": "ใช้หลายชนิด"}},
                        {"type": "button", "style": "primary", "height": "sm", "color": "#D8BFD8",
                         "action": {"type": "message", "label": "ยาชนิดอื่นๆ", "text": "ยาชนิดอื่นๆ"}}
                    ]
                }
            ]
        },
        "styles": {
            "header": {"backgroundColor": "#F9E79F"},
            "body": {"backgroundColor": "#FFFFFF"}
        }
    }
    flex_container = FlexContainer.from_dict(flex_content)
    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[FlexMessage(alt_text="เลือกยาที่มีปฏิกิริยา", contents=flex_container)]
        )
    )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    reply_token = event.reply_token
    user_text = event.message.text
    user_id = event.source.user_id
    text = user_text.strip()
    text_lower = text.lower()

     # ✅ บันทึก INR เช่น 'INR 2.4'
    match = re.match(r"inr\s*([0-9.]+)", text_lower)
    if match:
        try:
            inr_value = float(match.group(1))
            requests.post(google_script_url, json={"user_id": user_id, "inr_value": inr_value})
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=f"✅ บันทึก INR {inr_value} สำเร็จ")]
                )
            )
        except:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text="❌ ไม่สามารถบันทึกได้ โปรดลองอีกครั้ง")]
                )
            )
        return

    # ✅ ดูประวัติ INR
    if "ดูประวัติ" in text_lower:
        try:
            resp = requests.get(google_script_url)
            data = resp.json()
            user_logs = [f"• {row[1]} เมื่อ {row[2]}" for row in data if row[0] == user_id][-5:]
            result = "📋 ประวัติ INR ล่าสุด:\n" + "\n".join(user_logs) if user_logs else "ยังไม่มีข้อมูลที่บันทึก"
        except:
            result = "❌ ไม่สามารถโหลดข้อมูลจากระบบได้"
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=result)]
            )
        )
        return 

@app.route("/")
def home():
    return "✅ LINE Bot is ready to receive Webhook"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)