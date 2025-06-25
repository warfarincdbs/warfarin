import requests

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzzopJeXyDmbOPQv0qFjMXg-vGuxcRNQVMYP3VXEuaVns1rYzY1K0gD9a0UQvaKHVHs/exec"  # ⬅️ เปลี่ยนเป็น URL ของคุณ

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
        response = requests.post(SCRIPT_URL, json=payload)
        print("✅ ส่งข้อมูล:", response.text)
    except Exception as e:
        print("❌ เกิดข้อผิดพลาด:", e)
