from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

GOOGLE_APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxDZ8WPdzpzgACUboEi_JARVTRsnN_yg9Qnfy2FmxThTEESDZ56gbPodjb5AAGxagKvUA/exec"  # ใส่ของคุณตรงนี้

@app.route("/", methods=["GET"])
def home():
    return "✅ Flask on Render is live"

@app.route("/log_inr", methods=["POST"])
def log_inr():
    data = request.get_json()

    user_id = data.get("user_id")
    name = data.get("name")
    inr = data.get("inr")

    if not (user_id and name and inr):
        return jsonify({"error": "Missing required fields"}), 400

    # ส่งต่อไป Google Apps Script
    try:
        response = requests.post(GOOGLE_APPS_SCRIPT_URL, json={
            "user_id": user_id,
            "name": name,
            "inr": inr
        })
        return jsonify({"status": "sent", "google_response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)