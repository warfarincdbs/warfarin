import requests

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwxbfc3tY3YcUIhvlh4koGdnq2uexT5-lXq1XxViFpPx7V_pw__snBi_ycnL4KoSPk/exec"  # ⬅️ เปลี่ยนเป็น URL ของคุณ

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
        response = requests.post(SCRIPT_URL, json=payload)
        print("✅ ส่งข้อมูล:", response.text)
    except Exception as e:
        print("❌ เกิดข้อผิดพลาด:", e)
