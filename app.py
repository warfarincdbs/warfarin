from flask import Flask, request, jsonify, abort
import os
import requests

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    TextMessage, ReplyMessageRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
from dotenv import load_dotenv
from inr_chart import generate_inr_chart

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
GOOGLE_APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzbxslA3d641BIjPOClJZenJcuQRvJLkRp8MMMVGgh6Ssd_H50OXlfH2qpeYDvd_5MbjQ/exec"

# ====== In-Memory Session ======
user_sessions = {}

# ====== ฟังก์ชันส่งข้อมูลไป Google Sheet ======
def send_to_google_sheet(user_id, name, inr, bleeding="", supplement="", warfarin_dose=""):
    payload = {
        "userId": user_id,
        "name": name,
        "inr": inr,
        "bleeding": bleeding,
        "supplement": supplement,
        "warfarin_dose": warfarin_dose
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

# ====== API POST (Optional) ======
@app.route("/log_inr", methods=["POST"])
def log_inr():
    data = request.get_json()
    userId = data.get("user_id")
    name = data.get("name")
    inr = data.get("inr")
    bleeding = data.get("bleeding", "")
    supplement = data.get("supplement", "")
    warfarin_dose = data.get("warfarin_dose", "")
    if not (userId and name and inr):
        return jsonify({"error": "Missing required fields"}), 400
    result = send_to_google_sheet(userId, name, inr, bleeding, supplement, warfarin_dose)
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

def get_inr_history_from_sheet(user_id):
    url = "https://script.google.com/macros/s/PASTE_YOUR_SCRIPT_ID_HERE/exec"  # เปลี่ยน URL นี้
    try:
        response = requests.get(url, params={"userId": user_id}, timeout=10)
        data = response.json()
        if not data:
            return [], []
        dates = [item["date"] for item in data]
        inrs = [float(item["inr"]) for item in data]
        return dates, inrs
    except Exception as e:
        print(f"Error fetching INR: {e}")
        return [], []
    
def upload_image_and_reply(user_id, reply_token, image_buf):
    from linebot.v3.messaging import ImageMessage, ReplyMessageRequest
    tmp_path = f"/tmp/inr_chart_{user_id}.png"
    with open(tmp_path, "wb") as f:
        f.write(image_buf.read())
    with open(tmp_path, "rb") as f:
        res = messaging_api.upload_rich_media(f)

    image_url = res.content_provider.original_content_url
    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[ImageMessage(original_content_url=image_url, preview_image_url=image_url)]
        )
    )
# ====== LINE Message Handler ======
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    text = event.message.text.strip()

    if text == "ดูกราฟ INR":
        dates, inrs = get_inr_history_from_sheet(user_id)
        if not dates:
            messaging_api.reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=[
                    TextMessage(text="❌ ไม่พบข้อมูล INR ย้อนหลังของคุณ")
                ])
            )
            return
        buf = generate_inr_chart(dates, inrs)
        upload_image_and_reply(user_id, reply_token, buf)
        return

    # เริ่มต้นใช้งาน
    if text == "บันทึกค่า INR":
        user_sessions[user_id] = {"step": "ask_name"}
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="👤 กรุณาพิมพ์ชื่อ-นามสกุลของคุณ")
            ])
        )
        return

    session = user_sessions.get(user_id)

    # ถามชื่อ
    if session and session["step"] == "ask_name":
        session["name"] = text
        session["step"] = "ask_inr"
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="🧪 กรุณาพิมพ์ค่า INR เช่น 2.7")
            ])
        )
        return

    # ถาม INR
    if session and session["step"] == "ask_inr":
        try:
            session["inr"] = float(text)
            session["step"] = "ask_bleeding"
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
    if session and session["step"] == "ask_bleeding":
        if text.lower() not in ["yes", "no"]:
            messaging_api.reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=[
                    TextMessage(text="❌ กรุณาพิมพ์ yes หรือ no เท่านั้น")
                ])
            )
            return
        session["bleeding"] = text.lower()
        session["step"] = "ask_supplement"
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="🌿 มีการใช้สมุนไพร/อาหารเสริมหรือไม่? (ถ้าไม่มี พิมพ์ 'ไม่มี')")
            ])
        )
        return

    # ถาม supplement
    if session and session["step"] == "ask_supplement":
        session["supplement"] = text
        session["step"] = "ask_warf_dose"
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="💊 กรุณาระบุขนาดยา Warfarin รายวันใน 1 สัปดาห์ จันทร์,อังคาร,พุธ,....,อาทิตย์ (เช่น 3,3,3,3,3,1.5,0)")
            ])
        )
        return

    # ถาม dose warfarin
    if session and session["step"] == "ask_warf_dose":
        session["warfarin_dose"] = text
        user_sessions.pop(user_id)  # ล้าง session

        # แปลงเป็นรายวัน
        dose_list = text.split(",")
        days_th = ["จันทร์", "อังคาร", "พุธ", "พฤหัส", "ศุกร์", "เสาร์", "อาทิตย์"]
        doses_by_day = [f"📅 วัน{day}: {dose.strip()} mg" for day, dose in zip(days_th, dose_list)]
        dose_preview = "\n".join(doses_by_day)

        result = send_to_google_sheet(
            user_id=user_id,
            name=session["name"],
            inr=session["inr"],
            bleeding=session["bleeding"],
            supplement=session["supplement"],
            warfarin_dose=session["warfarin_dose"]
        )

        reply = f"""✅ ข้อมูลถูกบันทึกเรียบร้อยแล้ว
👤 {session['name']}
🧪 INR: {session['inr']}
🩸 Bleeding: {session['bleeding']}
🌿 Supplement: {session['supplement']}

💊 Warfarin (1 week):
{dose_preview}
"""
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text=reply)
            ])
        )
        return

    # หากไม่มี session
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