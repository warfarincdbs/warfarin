from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (Configuration, ApiClient, MessagingApi,TextMessage, ReplyMessageRequest)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
import os
from datetime import datetime, timedelta
from linebot.v3.messaging import FlexMessage
from linebot.v3.messaging.models import FlexContainer


app = Flask(__name__)

# ✅ ดึงค่าจาก Environment Variables
channel_secret = os.getenv("LINE_CHANNEL_SECRET")
access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

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

def calculate_warfarin(inr, twd, bleeding, supplement=None):
    if bleeding == "yes":
        return "\U0001f6a8 มี major bleeding → หยุด Warfarin, ให้ Vitamin K1 10 mg IV"

    warning = ""
    if supplement:
        herb_map = {
            "กระเทียม": "garlic", "ใบแปะก๊วย": "ginkgo", "โสม": "ginseng",
            "ขมิ้น": "turmeric", "น้ำมันปลา": "fish oil", "dong quai": "dong quai", "cranberry": "cranberry",
            "ตังกุย": "dong quai", "โกจิ": "goji berry", "คาร์โมไมล์": "chamomile", "ขิง": "ginger", "ชะเอมเทศ": "licorice",
            "ชาเขียว": "green tea", "นมถั่วเหลือง": "soy milk", "คลอโรฟิลล์": "chlorophyll",
            "วิตามินเค": "vitamin K", "โคเอนไซม์ Q10": "Coenzyme Q10", "St.John’s Wort": "St.John’s Wort"
        }
        high_risk = list(herb_map.keys())
        matched = [name for name in high_risk if name in supplement]
        if matched:
            herbs = ", ".join(matched)
            warning = f"\n\u26a0\ufe0f พบว่าสมุนไพร/อาหารเสริมที่อาจมีผลต่อ INR ได้แก่: {herbs}\nโปรดพิจารณาความเสี่ยงต่อการเปลี่ยนแปลง INR อย่างใกล้ชิด"
        else:
            warning = "\n\u26a0\ufe0f มีการใช้อาหารเสริมหรือสมุนไพร → พิจารณาความเสี่ยงต่อการเปลี่ยนแปลง INR"

    followup_text = get_followup_text(inr)

    if inr < 1.5:
        result = f"\U0001f539 INR < 1.5 → เพิ่มขนาดยา 10–20%\nขนาดยาใหม่: {twd * 1.1:.1f} – {twd * 1.2:.1f} mg/สัปดาห์"
    elif 1.5 <= inr <= 1.9:
        result = f"\U0001f539 INR 1.5–1.9 → เพิ่มขนาดยา 5–10%\nขนาดยาใหม่: {twd * 1.05:.1f} – {twd * 1.10:.1f} mg/สัปดาห์"
    elif 2.0 <= inr <= 3.0:
        result = "✅ INR 2.0–3.0 → คงขนาดยาเดิม"
    elif 3.1 <= inr <= 3.9:
        result = f"\U0001f539 INR 3.1–3.9 → ลดขนาดยา 5–10%\nขนาดยาใหม่: {twd * 0.9:.1f} – {twd * 0.95:.1f} mg/สัปดาห์"
    elif 4.0 <= inr <= 4.9:
        result = f"⚠\ufe0f INR 4.0–4.9 → หยุดยา 1 วัน และลดขนาดยา 10%\nขนาดยาใหม่: {twd * 0.9:.1f} mg/สัปดาห์"
    elif 5.0 <= inr <= 8.9:
        result = "⚠\ufe0f INR 5.0–8.9 → หยุดยา 1–2 วัน และพิจารณาให้ Vitamin K1 1 mg"
    else:
        result = "\U0001f6a8 INR ≥ 9.0 → หยุดยา และพิจารณาให้ Vitamin K1 5–10 mg"

    return f"{result}{warning}\n\n{followup_text}"

def get_inr_followup(inr):
    if inr < 1.5: return 7
    elif inr <= 1.9: return 14
    elif inr <= 3.0: return 56
    elif inr <= 3.9: return 14
    elif inr <= 6.0: return 7
    elif inr <= 8.9: return 5
    elif inr > 9.0: return 2
    return None

def get_followup_text(inr):
    days = get_inr_followup(inr)
    if days:
        date = (datetime.now() + timedelta(days=days)).strftime("%-d %B %Y")
        return f"📅  คำแนะนำ: ควรตรวจ INR ภายใน {days} วัน\n📌 วันที่ควรตรวจ: {date}"
    else:
        return ""



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
                            for herb in ["กระเทียม", "ใบแปะก๊วย", "โสม", "ขมิ้น", "ขิง", "น้ำมันปลา", "ใช้หลายชนิด", "สมุนไพร/อาหารเสริมชนิดอื่นๆ"]
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
        "Amiodarone", "Gemfibrozil", "Azole antifungal", "Trimethoprim/Sulfamethoxazole",
        "Macrolides(ex.Erythromycin)", "NSAIDs", "Quinolones(ex.Ciprofloxacin)"
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

    if text_lower in ['คำนวณยา warfarin']:
        user_sessions.pop(user_id, None)
        user_drug_selection.pop(user_id, None)
        user_sessions[user_id] = {"flow": "warfarin", "step": "ask_inr"}
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="🧪 กรุณาใส่ค่า INR (เช่น 2.5)")]
            )
        )
        return

    if user_id in user_sessions:
        session = user_sessions[user_id]
        if session.get("flow") == "warfarin":
            step = session.get("step")
            if step == "ask_inr":
                try:
                    session["inr"] = float(text)
                    session["step"] = "ask_twd"
                    reply = "📈 ใส่ Total Weekly Dose (TWD) เช่น 28"
                except:
                    reply = "❌ กรุณาใส่ค่า INR เป็นตัวเลข เช่น 2.5"
                messaging_api.reply_message(
                    ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=reply)])
                )
                return

            elif step == "ask_twd":
                try:
                    session["twd"] = float(text)
                    session["step"] = "ask_bleeding"
                    reply = "🩸 มี major bleeding หรือไม่? (yes/no)"
                except:
                    reply = "❌ กรุณาใส่ค่า TWD เป็นตัวเลข เช่น 28"
                messaging_api.reply_message(
                    ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=reply)])
                )
                return

            elif step == "ask_bleeding":
                if text.lower().strip(".") not in ["yes", "no"]:
                    reply = "❌ ตอบว่า yes หรือ no เท่านั้น"
                    messaging_api.reply_message(
                        ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=reply)])
                    )
                    return
                session["bleeding"] = text.lower()
                if text.lower().strip(".") == "yes":
                # ✅ มี bleeding → แสดงผลทันทีและจบ flow
                    result = calculate_warfarin(session["inr"], session["twd"], session["bleeding"])
                    user_sessions.pop(user_id, None)
                    messaging_api.reply_message(
                        ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=result)])
                )
                
                else:   
                    # ถ้าไม่มี bleeding → ไปถามเรื่องสมุนไพรต่อ
                    session["step"] = "choose_supplement"
                    send_supplement_flex(reply_token)
                return


            elif step == "choose_supplement":
                if text == "ไม่ได้ใช้":
                    session["supplement"] = ""
                    session["step"] = "choose_interaction"
                    send_interaction_flex(reply_token)
                    return

                elif text == "สมุนไพร/อาหารเสริมชนิดอื่นๆ":
                    session["step"] = "ask_custom_supplement"
                    messaging_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[TextMessage(text="🌿 กรุณาพิมพ์ชื่อสมุนไพร/อาหารเสริมที่ใช้ เช่น ตังกุย ขิง ชาเขียว")]
                        )
                    )
                    return
                
                elif step == "ask_custom_supplement":
                    session["supplement"] = text
                    session["step"] = "choose_interaction"
                    send_interaction_flex(reply_token)
                    return

                else:
                    session["supplement"] = text
                    session["step"] = "choose_interaction"
                    send_interaction_flex(reply_token)
                    return

            elif step == "choose_interaction":
                if text == "ไม่ได้ใช้":
                    interaction_note = ""
                    supplement = session.get("supplement", "")
                    result = calculate_warfarin(session["inr"], session["twd"], session["bleeding"], supplement)
                    final_result = f"{result.split('\n\n')[0]}{interaction_note}\n\n{result.split('\n\n')[1]}"
                    user_sessions.pop(user_id, None)
                    messaging_api.reply_message(
                        ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=final_result)])
                    )
                    return

                elif text in ["ใช้หลายชนิด", "ยาชนิดอื่นๆ"]:
                    session["step"] = "ask_interaction"
                    reply = "💊 โปรดพิมพ์ชื่อยาที่ใช้อยู่ เช่น Amiodarone, NSAIDs"
                    messaging_api.reply_message(
                        ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=reply)])
                    )
                    return

                else:
                    interaction_note = f"\n⚠️ พบการใช้ยา: {text} ซึ่งอาจมีปฏิกิริยากับ Warfarin"
                    supplement = session.get("supplement", "")
                    result = calculate_warfarin(session["inr"], session["twd"], session["bleeding"], supplement)
                    final_result = f"{result.split('\n\n')[0]}{interaction_note}\n\n{result.split('\n\n')[1]}"
                    user_sessions.pop(user_id, None)
                    messaging_api.reply_message(
                        ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=final_result)])
                    )
                    return

            elif step == "ask_interaction":
                interaction_note = f"\n⚠️ พบการใช้ยา: {text.strip()} ซึ่งอาจมีปฏิกิริยากับ Warfarin"
                supplement = session.get("supplement", "")
                result = calculate_warfarin(session["inr"], session["twd"], session["bleeding"], supplement)
                final_result = f"{result.split('\n\n')[0]}{interaction_note}\n\n{result.split('\n\n')[1]}"
                user_sessions.pop(user_id, None)
                messaging_api.reply_message(
                    ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=final_result)])
                )
                return


    if user_id not in user_sessions and user_id not in user_drug_selection:
        messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text="❓ พิมพ์ 'คำนวณยา warfarin' หรือ 'คำนวณยาเด็ก' เพื่อเริ่มต้นใช้งาน")]
            )
        )
        return

@app.route("/")
def home():
    return "✅ LINE Bot is ready to receive Webhook"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port) 