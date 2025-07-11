
from flask import Flask, request, jsonify, abort
import os
import requests

import matplotlib.pyplot as plt
import io
from PIL import Image
import base64

from datetime import datetime
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    TextMessage, ReplyMessageRequest,  ImageMessage 
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
from dotenv import load_dotenv
load_dotenv()

from inr_chart import generate_inr_chart
from flask import send_file  # อย่าลืม import นี้ด้านบน
from linebot.v3.messaging import FlexMessage
from linebot.v3.messaging.models import FlexContainer
from linebot.v3.messaging import QuickReply, QuickReplyItem, MessageAction

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import requests

DOSE_DESC_MAP = {
    "0": "งดยา",
    "0.75": "เม็ดสีฟ้า เสี้ยว เม็ด",
    "1.25": "เม็ดสีชมพู เสี้ยว เม็ด",
    "1.5": "เม็ดสีฟ้า ครึ่ง เม็ด",
    "2": "เม็ดสีฟ้า เสี้ยว เม็ด + เม็ดสีชมพู เสี้ยว เม็ด",
    "2.25": "เม็ดสีฟ้า 3 ใน 4  เม็ด",
    "2.5": "เม็ดสีชมพู ครึ่ง เม็ด",
    "2.75": " เม็ดสีฟ้าครึ่งเม็ด + ชมพู เสี้ยวเม็ด",
    "3": "เม็ดสีฟ้า 1 เม็ด",
    "3.25": "เม็ดสีฟ้า เสี้ยว เม็ด + ชมพู ครึ่ง เม็ด",
    "3.5": "เม็ดสีฟ้า 3 ใน 4 เม็ด + ชมพู เสี้ยว เม็ด",
    "3.75": "เม็ดสีชมพู 3 ใน 4 เม็ด",
    "4": "เม็ดสีฟ้า ครึ่ง เม็ด + ชมพู ครึ่ง เม็ด",
    "4.25": "เม็ดสีฟ้า 1 เม็ด + ชมพู เสี้ยว เม็ด",
    "4.5": "เม็ดสีฟ้า 1 เม็ด ครึ่ง",
    "4.75": "เม็ดสีฟ้า 3 ใน 4 เม็ด + ชมพู ครึ่ง เม็ด",
    "5": "เม็ดสีชมพู 1 เม็ด",
    "5.25": " เม็ดสีฟ้า 1 เม็ด +  เม็ดสีฟ้า 3 ใน 4 เม็ด",
    "5.5": " เม็ดสีฟ้า 1 เม็ด +  เม็ดสีชมพู ครึ่ง เม็ด",
    "5.75": "เม็ดสีฟ้า เสี้ยว เม็ด + ชมพู 1 เม็ด",
    "6": "เม็ดสีฟ้า 2 เม็ด",
    "6.25": "เม็ดสีชมพู 1 เม็ด เสี้ยว",
    "6.5": "เม็ดสีฟ้า ครึ่ง เม็ด +  เม็ดสีชมพู 1 เม็ด",
    "6.75": "เม็ดสีฟ้า 1 เม็ด + เม็ดสีชมพู 3 ใน 4 เม็ด",
    "7.25": "เม็ดสีฟ้า 3 ใน 4 เม็ด + เม็ดสีชมพู 1 เม็ด",
    "7.5": "สีชมพู 1 เม็ด ครึ่ง",
    "8": "เม็ดสีฟ้า 1 เม็ด + เม็ดสีชมพู 1 เม็ด",
    "8.75": "เม็ดสีชมพู 1 เม็ด + เม็ดสีชมพู 3 ใน 4 เม็ด",
    "9": "เม็ดสีฟ้า 3 เม็ด",
    "10": "เม็ดสีชมพู 2 เม็ด"
}

DOSE_IMAGE_MAP = {
  "0": "https://drive.google.com/uc?export=view&id=1C-xnILoUHREpjR7R7CRTXNM2GZcbBGGl",
  "0.75": "https://drive.google.com/uc?export=view&id=1oLJSf3pl3Aegci4V3vWlCNtIe1C1SezL",
  "1.25": "https://drive.google.com/uc?export=view&id=1ZTcC9N36PX1zHQSXgOgG5WIZifnskOsm",
  "1.5": "https://drive.google.com/uc?export=view&id=1mtlw2S1D3aFulnXWqWbuOqK4p3xvM56s",
  "2": "https://drive.google.com/uc?export=view&id=1Oqxk2xddHLeX-4V47vcKDJ4ZuzNzsuvQ",
  "2.25": "https://drive.google.com/uc?export=view&id=12jQ5jGHTa2wGRxUaJ8S1B82DKYqxD02u",
  "2.5": "https://drive.google.com/uc?export=view&id=1Y7YfElYjNYCkY4ljmE9MJNXesHYuFFXd",
  "2.75": "https://drive.google.com/uc?export=view&id=1ZXf111FIpxrl37eMyVdxrhF3QF1QvgWw",
  "3": "https://drive.google.com/uc?export=view&id=1E9q3rkXD4ThRFxFbiRxs4BkgSNPuRYJx",
  "3.25": "https://drive.google.com/uc?export=view&id=1YKMs-h-gGLDYg0vI0byZ_4zTf0uXWXyh",
  "3.5": "https://drive.google.com/uc?export=view&id=1EREz7P9-GI_8mERjTUtQ5k_fyqOfigSP",
  "3.75": "https://drive.google.com/uc?export=view&id=1DLbTm8grBHk5OCp9q6ZsJhePfc-W1DGp",
  "4": "https://drive.google.com/uc?export=view&id=1tgXDrVC3nWH10WsDauxVOdycZ3uUKnbX",
  "4.25": "https://drive.google.com/uc?export=view&id=1elqoZlPgSZVoSpyv_HOzJqHCnaK-O4DQ",
  "4.5": "https://drive.google.com/uc?export=view&id=1Zk8isy0hd0HRfeegSpNqPUZeDyRCK1TF",
  "4.75": "https://drive.google.com/uc?export=view&id=1B4M4Eyw2S_yuZmcFsWloxbmWPwMGgHXM",
  "5": "https://drive.google.com/uc?export=view&id=1VL70qndziWlYHPrCVqHjE99jg6TrIHuN",
  "5.25": "https://drive.google.com/uc?export=view&id=1pgIwUZ0u8ow9NlXX4qn8TYXfGY5QI1o0",
  "5.5": "https://drive.google.com/uc?export=view&id=1uC5CxdWBrWy0aRKKKNt2AiizNZkE4Ha-",
  "5.75": "https://drive.google.com/uc?export=view&id=1GLgVX1rC5kwh33cyYwJApgCzVEjYZkSs",
  "6": "https://drive.google.com/uc?export=view&id=1DSH9PPRLrCtoZIsspNg72VMVPx4GMiQr",
  "6.25": "https://drive.google.com/uc?export=view&id=1arIeHmlcCDjlZRCxaXp9HinNF5RFTObM",
  "6.5": "https://drive.google.com/uc?export=view&id=14_c6VwFtimrUz_08KYi2eHrtz03IxVs0",
  "6.75": "https://drive.google.com/uc?export=view&id=1TLkBttSsd-jgR3gF0PXtYadgwDDKvpLy",
  "7.25": "https://drive.google.com/uc?export=view&id=1YMenxS-yjiYI9FMcxsWgWF8vrv7Nxk-K",
  "7.5": "https://drive.google.com/uc?export=view&id=1FE_nDZGagBATeLFqVKsk8ZuyahFxyhH2",
  "8": "https://drive.google.com/uc?export=view&id=1WGQkiYlkRFdqyxx8frbeMnH23xjPWQf7",
  "8.75": "https://drive.google.com/uc?export=view&id=113hhEtD9drIp5FxG96YD1_icFDo0q5iJ",
  "9": "https://drive.google.com/uc?export=view&id=1vA_ZmQV5VE-it-IsYPjxwt0NR8buIdhy",
  "10": "https://drive.google.com/uc?export=view&id=1B4WnZ_6FD9ORgw1_WGbFbRpJMr81Z16Z",
# เพิ่มได้ตามขนาดยา
}


# ====== LINE API Setup ======
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=access_token)
messaging_api = MessagingApi(ApiClient(configuration))

# ====== Flask Setup ======
app = Flask(__name__)

# ====== Google Apps Script Webhook URL ======
GOOGLE_APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwdi3et7_H6dHFA7dTNRjNESjljUq1KZl2JOitV0fDkeVORlvyJMBgEEEG9nqAdSP4D/exec"

# ====== In-Memory Session ======
user_sessions = {}

# ====== ฟังก์ชันส่งข้อมูลไป Google Sheet ======
def send_to_google_sheet(user_id, name, birthdate, inr, bleeding="", supplement="", warfarin_dose=""):
    payload = {
        "userId": user_id,
        "name": name,
        "birthdate": birthdate,  # ✅ เพิ่มตรงนี้
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

@app.route("/daily_notify", methods=["GET"])
def daily_notify():
    main()
    return "📤 แจ้งเตือนเรียบร้อย"


# ====== แจ้งเตือนการกินยา (สำหรับเรียกจาก scheduler) ======
def connect_sheet():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)

# ========== แปลงวันเป็นคอลัมน์ภาษาไทย ==========
def get_today_column():
    thai_days = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัส', 'ศุกร์', 'เสาร์', 'อาทิตย์']
    today_index = datetime.now().weekday()
    return thai_days[today_index]

# ========== ส่งข้อความเข้า LINE ==========
def send_line_notify(user_id, message):
    # หาค่าขนาดยา (เช่น 3 mg) จากข้อความ
    dose = None
    for token in message.split():
        if token.endswith("mg"):
            dose = token.replace("mg", "").strip()
            break

    # ดึง URL รูปจาก IMAGE_MAP
    image_url = IMAGE_MAP.get(dose)

    headers = {
        'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }

    # สร้างข้อความ text เป็น default
    messages = [{'type': 'text', 'text': message}]

    # ถ้ามีรูปภาพขนาดยานี้ → เพิ่มข้อความแบบ image
    if image_url:
        messages.append({
            'type': 'image',
            'originalContentUrl': image_url,
            'previewImageUrl': image_url
        })

    payload = {
        'to': user_id,
        'messages': messages
    }

    response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload)
    print(f'Sent to {user_id}: {response.status_code}')

# ========== MAIN ==========
def main():
    sheet = connect_sheet()
    data = sheet.get_all_records()
    today_col = get_today_column()

    for row in data:
        user_id = row.get('userID')
        name = f"{row.get('firstName', '')} {row.get('lastName', '')}".strip()
        message_text = row.get(today_col, '').strip()

        if user_id and message_text and message_text != '-':
            # ✅ เพิ่มบรรทัดนี้: เติม mg อัตโนมัติถ้าไม่มี
            dose_with_unit = f"{message_text} mg" if "mg" not in message_text.lower() else message_text

            message = f"\U0001F4C5 วันนี้วัน{today_col}\nคุณ {name}\nกรุณากินยา\n{dose_with_unit}"
            send_line_notify(user_id, message)



# ====== API POST โดยตรงแบบ REST (Optional) ======
@app.route("/log_inr", methods=["POST"])
def log_inr():
    data = request.get_json()
    userId = data.get("user_id")
    name = data.get("name")
    birthdate = data.get("birthdate", "")  # ✅ เพิ่มบรรทัดนี้
    inr = data.get("inr")
    bleeding = data.get("bleeding", "")
    supplement = data.get("supplement", "")
    warfarin_dose = data.get("warfarin_dose", "")

    if not (userId and name and inr):
        return jsonify({"error": "Missing required fields"}), 400

    result = send_to_google_sheet(userId, name, birthdate, inr, bleeding, supplement, warfarin_dose)
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
    url = "https://script.google.com/macros/s/AKfycbwdi3et7_H6dHFA7dTNRjNESjljUq1KZl2JOitV0fDkeVORlvyJMBgEEEG9nqAdSP4D/exec"
    try:
        response = requests.get(url, params={"userId": user_id, "history": "true"}, timeout=10)
        data = response.json()
        if not data:
            return [], []
        dates = [item["date"] for item in data]
        inrs = [float(item["inr"]) for item in data]
        return dates, inrs
    except Exception as e:
        print(f"Error fetching INR: {e}")
        return [], []

def get_user_profile(user_id):
    try:
        response = requests.get(GOOGLE_APPS_SCRIPT_URL, params={"userId": user_id, "profile": "true"}, timeout=10)
        data = response.json()
        return data  # {firstName, lastName, birthdate} หรือ {}
    except Exception as e:
        print("❌ Error loading profile:", e)
        return {}


def upload_image_and_reply(user_id, reply_token, image_buf):
    # 1. บันทึกภาพลงเป็นไฟล์ชั่วคราว
    filename = f"inr_chart_{user_id}.png"
    tmp_path = f"/tmp/{filename}"

    with open(tmp_path, "wb") as f:
        f.write(image_buf.read())

    # 2. กำหนด URL สำหรับให้ LINE ดูภาพได้
    image_url = f"https://warfarin.onrender.com/image/{filename}"  # ✅ เปลี่ยน domain

    # 3. ส่งภาพกลับผ่าน LINE
    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[
                ImageMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            ]
        )
    )


def generate_inr_chart(dates, inr_values):

    dates.reverse()
    inr_values.reverse()

    fig, ax = plt.subplots(figsize=(8, 4))

    # ตัดค่าที่เกิน 5.5 แต่ให้วาดจุดไว้เหนือ 5.5
    clipped_values = [min(v, 5.5) for v in inr_values]

    # วาดกราฟเส้น
    ax.plot(dates, clipped_values, marker="o", color="#007bff", label="INR")

    # เติม label ที่จุด
    for i, (x, y, raw_y) in enumerate(zip(dates, clipped_values, inr_values)):
        ax.text(x, y + 0.15, f"{raw_y:.1f}", ha="center", fontsize=10, color="black")
        # ถ้า INR >= 6 ให้ใช้จุดแดง
        if raw_y >= 6:
            ax.plot(x, y, marker="o", color="red", markersize=10)

    # พื้นหลังสีเขียวระหว่าง INR 2.0–3.5
    ax.axhspan(2.0, 3.5, facecolor='green', alpha=0.1)

    # ตั้ง y scale เริ่มที่ 0.5 ถึง 5.5
    ax.set_ylim(0.5, 6.2)
    ax.set_yticks([i * 0.5 for i in range(1, 12)])
    ax.set_ylabel("INR")
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels(dates, rotation=45)
    ax.set_title("INR chart")

    plt.tight_layout()

    # แปลงเป็น buffer image
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    return buf    

@app.route("/image/<filename>")
def serve_image(filename):
    filepath = f"/tmp/{filename}"
    return send_file(filepath, mimetype="image/png")

def send_symptom_assessment_flex(reply_token):
    # Flex 1: เลือกอาการเลือดออก
    bubble_bleeding = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{"type": "text", "text": "🩸 อาการเลือดออกผิดปกติ", "weight": "bold", "size": "lg"}]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "คุณมีอาการใดต่อไปนี้หรือไม่?", "wrap": True},
                *[
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#FFCDD2",
                        "action": {"type": "message", "label": label, "text": label}
                    }
                    for label in ["จุดจ้ำเลือด","เลือดไหลไม่หยุด","ไอ/อาเจียนเป็นเลือด","อุจจาระสีดำ","ปัสสาวะมีสีสนิม","ประจำเดือนมามากผิดปกติ", "ไม่มีอาการ"]
                ]
            ]
        }
    }

    # Flex 2: เลือกอาการลิ่มเลือดอุดตัน
    bubble_clot = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [{"type": "text", "text": "🧠 อาการลิ่มเลือดอุดตัน", "weight": "bold", "size": "lg"}]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "คุณมีอาการใดต่อไปนี้หรือไม่?", "wrap": True},
                *[
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#BBDEFB",
                        "action": {"type": "message", "label": label, "text": label}
                    }
                    for label in ["เจ็บหน้าอก หายใจลำบาก", "ปวด/เวียนศีรษะ", "แขนขาบวม", "อ่อนแรงครึ่งซีก แขนขาชา", "พูดไม่ชัด","ไม่มีอาการ"]
                ]
            ]
        }
    }

    messaging_api.reply_message(
        ReplyMessageRequest(
            reply_token=reply_token,
            messages=[
                FlexMessage(alt_text="เลือดออกผิดปกติ", contents=FlexContainer.from_dict(bubble_bleeding)),
                FlexMessage(alt_text="ลิ่มเลือดอุดตัน", contents=FlexContainer.from_dict(bubble_clot))
            ]
        )
    )


# ====== LINE Message Handler ======
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    text = event.message.text.strip()
    session = user_sessions.get(user_id, {})

    bleeding_symptoms = ["จุดจ้ำเลือด","เลือดไหลไม่หยุด","ไอ/อาเจียนเป็นเลือด","อุจจาระสีดำ","ปัสสาวะมีสีสนิม","ประจำเดือนมามากผิดปกติ"]
    clot_symptoms = ["เจ็บหน้าอก หายใจลำบาก", "ปวด/เวียนศีรษะ", "แขนขาบวม", "อ่อนแรงครึ่งซีก แขนขาชา", "พูดไม่ชัด"]

    if text in bleeding_symptoms:
            msg = "⚠️ ตรวจพบอาการเลือดออกผิดปกติ\n⛔ โปรดหยุดยา Warfarin และพบแพทย์ทันที"
    elif text in clot_symptoms:
            msg = "⚠️ ตรวจพบอาการที่อาจเกิดลิ่มเลือดอุดตัน\n⛔ ถ้าอาการไม่ดีขึ้น ให้รีบไปโรงพยาบาลที่ใกล้ที่สุด"
    elif text == "ไม่มีอาการ":
            msg = "✅ ขอบคุณสำหรับการประเมิน ไม่มีอาการผิดปกติในขณะนี้"
    else:
            msg = None

    if msg:
            messaging_api.reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=msg)])
            )
            return

    if text == "ดูกราฟ INR":
        dates, inrs = get_inr_history_from_sheet(user_id)

        # debug logs
        print("DEBUG: dates =", dates)
        print("DEBUG: inrs =", inrs)

        if not dates or not inrs:
            messaging_api.reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=[
                    TextMessage(text="❌ ไม่พบข้อมูล INR ย้อนหลังของคุณ")
                ])
            )
            return

        buf = generate_inr_chart(dates, inrs)
        upload_image_and_reply(user_id, reply_token, buf)
        return

    if text == "วันนี้ฉันกินยาอย่างไร":
        thai_days = ["วันจันทร์", "วันอังคาร", "วันพุธ", "วันพฤหัสบดี", "วันศุกร์", "วันเสาร์", "วันอาทิตย์"]
        today_index = datetime.now().weekday()
        today_th = thai_days[today_index] + " (คำอธิบาย)"

        try:
            response = requests.get(
                GOOGLE_APPS_SCRIPT_URL,
                params={"userId": user_id, "latest": "true"},
                timeout=10
            )
            data = response.json()

            if today_th in data:
                today_dose = data[today_th]
                if not today_dose or today_dose.strip() in ["", "งดยา", "-"]:
                    msg = f"📅 วันนี้{thai_days[today_index]} คุณไม่มียา Warfarin ครับ"

                    image_url = DOSE_IMAGE_MAP.get("0")  # รูปงดยา
                    messages = [TextMessage(text=msg)]
                    if image_url:
                        messages.append(ImageMessage(
                            original_content_url=image_url,
                            preview_image_url=image_url
                        ))

                    messaging_api.reply_message(
                        ReplyMessageRequest(reply_token=reply_token, messages=messages)
                    )
                    return

                msg = f"📅 วันนี้{thai_days[today_index]}\n💊 คุณต้องกินยา Warfarin ดังนี้:\n{today_dose}"

                # หาคีย์ของขนาดยาใน DOSE_DESC_MAP ที่ตรงกับคำอธิบาย
                dose_key = next((k for k, v in DOSE_DESC_MAP.items() if v == today_dose.strip()), None)
                image_url = DOSE_IMAGE_MAP.get(dose_key)

                messages = [TextMessage(text=msg)]
                if image_url:
                    messages.append(ImageMessage(
                        original_content_url=image_url,
                        preview_image_url=image_url
                    ))

                messaging_api.reply_message(
                    ReplyMessageRequest(reply_token=reply_token, messages=messages)
                )
                return

            else:
                msg = "❌ ไม่พบข้อมูลยาวันนี้ในระบบ"

        except Exception as e:
            print("❌ Error fetching today's dose:", e)
            msg = "⚠️ เกิดข้อผิดพลาดในการดึงข้อมูลยา กรุณาลองใหม่ภายหลัง"

        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=msg)])
        )
        return

    
# ✅ เพิ่มฟังก์ชันสำหรับอัปเดตโปรไฟล์ (ไว้ท้ายไฟล์หรือส่วน util)

    # เริ่มต้น flow
        # เริ่มต้น flow
    # ✅ เพิ่มใน handler ด้านบน (ก่อน session flow)
    if text == "แก้ชื่อ":
        user_sessions[user_id] = {"step": "edit_name"}
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="📛 กรุณาพิมพ์ชื่อ-นามสกุลใหม่ของคุณ")
            ])
        )
        return

    if text == "แก้วันเกิด":
        user_sessions[user_id] = {"step": "edit_birthdate"}
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="🎂 กรุณาพิมพ์วันเกิดใหม่ (เช่น 01/01/2540)")
            ])
        )
        return

    if session.get("step") == "edit_name":
        new_name = text.strip()
        update_user_profile(user_id=user_id, new_name=new_name)
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text=f"✅ เปลี่ยนชื่อเป็น \"{new_name}\" เรียบร้อยแล้ว")
            ])
        )
        user_sessions.pop(user_id, None)
        return

    if session.get("step") == "edit_birthdate":
        new_birthdate = text.strip()
        update_user_profile(user_id=user_id, new_birthdate=new_birthdate)
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text=f"✅ เปลี่ยนวันเกิดเป็น {new_birthdate} เรียบร้อยแล้ว")
            ])
        )
        user_sessions.pop(user_id, None)
        return

# ✅ แก้ไขส่วนข้อความตอบกลับตอนโหลด profile เพื่อเพิ่ม Quick Reply
    if text == "บันทึกค่า INR":
        profile = get_user_profile(user_id)
        if profile and profile.get("firstName"):
            full_name = f"{profile['firstName']} {profile.get('lastName', '')}".strip()
            user_sessions[user_id] = {
                "name": full_name,
                "birthdate": profile.get("birthdate", ""),
                "step": "ask_inr"
            }
            messaging_api.reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=[
                    TextMessage(
                        text=f"""🙋‍♂️ ยินดีต้อนรับกลับมาคุณ {full_name}
                🧪 กรุณาพิมพ์ค่า INR เช่น 2.7""",
                        quick_reply=QuickReply(items=[
                            QuickReplyItem(action=MessageAction(label="✏️ แก้ชื่อ", text="แก้ชื่อ")),
                            QuickReplyItem(action=MessageAction(label="🎂 แก้วันเกิด", text="แก้วันเกิด"))
                        ])
                    )
                ]))
            return


    if session.get("step") == "ask_name":
        session["name"] = text
        session["step"] = "ask_birthdate"
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="🎂 กรุณาพิมพ์วันเกิดของคุณ (เช่น 01/01/2540)")
            ])
        )
        return

    if session.get("step") == "ask_birthdate":
        session["birthdate"] = text
        session["step"] = "ask_inr"
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="🧪 กรุณาพิมพ์ค่า INR เช่น 2.7")
            ])
        )
        return

    if session.get("step") == "ask_inr":
        try:
            inr = float(text)
            session["inr"] = inr
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

    if session.get("step") == "ask_bleeding":
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

    if session.get("step") == "ask_supplement":
        session["supplement"] = text
        session["step"] = "ask_warf_dose"
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="💊 กรุณาระบุขนาดยา Warfarin รายวันใน 1 สัปดาห์ จันทร์,อังคาร,พุธ,...,อาทิตย์ (เช่น 3,3,3,3,3,1.5,0)")
            ])
        )
        return

    if session.get("step") == "ask_warf_dose":
        session["warfarin_dose"] = text
        user_sessions.pop(user_id)

        dose_list = text.split(",")
        if len(dose_list) != 7:
            messaging_api.reply_message(
                ReplyMessageRequest(reply_token=reply_token, messages=[
                    TextMessage(text="❌ กรุณากรอกขนาดยา 7 วัน เช่น 3,3,3,3,3,1.5,0")
                ])
            )
            return

        days_th = ["จันทร์", "อังคาร", "พุธ", "พฤหัส", "ศุกร์", "เสาร์", "อาทิตย์"]
        doses_by_day = [f"📅 วัน{day}: {dose.strip()} mg" for day, dose in zip(days_th, dose_list)]
        dose_preview = "\n".join(doses_by_day)

        result = send_to_google_sheet(
            user_id=user_id,
            name=session["name"],
            birthdate=session["birthdate"],
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

    if text == "ประเมินอาการไม่พึงประสงค์":
        send_symptom_assessment_flex(reply_token)
        return
    

    # หากไม่ได้อยู่ในขั้นตอนใดเลย
    if user_id not in user_sessions:
        messaging_api.reply_message(
            ReplyMessageRequest(reply_token=reply_token, messages=[
                TextMessage(text="❓ พิมพ์ 'บันทึกค่า INR' เพื่อเริ่มบันทึกข้อมูล INR")
            ])
        )
def update_user_profile(user_id, new_name=None, new_birthdate=None):
    payload = {
        "userId": user_id,
        "update_name": new_name,
        "update_dob": new_birthdate
    }
    try:
        response = requests.post(GOOGLE_APPS_SCRIPT_URL, json=payload, timeout=10)
        print("🔄 อัปเดตโปรไฟล์:", response.text)
    except Exception as e:
        print("❌ ERROR while updating profile:", e)



# ====== Run App ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)