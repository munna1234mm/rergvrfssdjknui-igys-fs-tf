from flask import Flask, send_from_directory, request, jsonify, session
import os
import random
import requests
import subprocess
from datetime import timedelta
from dotenv import load_dotenv
from database import (
    get_user, add_user, update_user_proxy, 
    increment_stat, get_all_stats, 
    add_requirement, remove_requirement, get_requirements
)

load_dotenv()

app = Flask(__name__)
app.secret_key = "HITTER_SECRET_KEY_987654321" # Fixed key for session persistence
app.permanent_session_lifetime = timedelta(days=7) # Session lasts 7 days

# Global variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("HITTER_API_KEY")
ADMIN_ID = os.getenv("ADMIN_CHAT_ID")
API_URL = "https://hitter1month.replit.app"

def send_telegram_msg(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")

def check_tg_membership(chat_id, user_id):
    """Checks if a user is a member of a specific group/channel."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
        payload = {"chat_id": chat_id, "user_id": user_id}
        res = requests.post(url, json=payload).json()
        if res.get("ok"):
            status = res["result"]["status"]
            return status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"❌ Membership Check Failed: {e}")
    return False

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/admin")
def admin_page():
    return send_from_directory(".", "admin.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

# --- AUTH API ---

@app.route("/api/check-session", methods=["GET"])
def check_session():
    if "chat_id" in session:
        user = get_user(session["chat_id"])
        return jsonify({
            "success": True, 
            "chat_id": session["chat_id"],
            "is_admin": str(session["chat_id"]) == str(ADMIN_ID),
            "proxy": user["proxy"] if user else None
        })
    return jsonify({"success": False, "message": "No active session"}), 401

otp_storage = {}

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
        session.permanent = True
        session["chat_id"] = chat_id
        # Add user to database
        add_user(chat_id, f"User_{chat_id[-4:]}")
        return jsonify({"success": True, "message": "Login successful"})
    else:
        return jsonify({"success": False, "message": "Invalid code"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("chat_id", None)
    return jsonify({"success": True, "message": "Logged out"})

# --- USER REQUIREMENTS ---

@app.route("/api/check-requirements", methods=["GET"])
def check_requirements():
    if "chat_id" not in session: return jsonify({"success": False}), 401
    
    user_id = session["chat_id"]
    if str(user_id) == str(ADMIN_ID): return jsonify({"success": True, "all_joined": True}) # Admin bypass
    
    requirements = get_requirements()
    if not requirements: return jsonify({"success": True, "all_joined": True})
    
    needed = []
    for req in requirements:
        if not check_tg_membership(req["chat_id"], user_id):
            needed.append({
                "name": req["name"],
                "url": req["url"]
            })
            
    return jsonify({
        "success": True, 
        "all_joined": len(needed) == 0,
        "needed": needed
    })

# --- USER SETTINGS ---

@app.route("/api/user/proxy", methods=["POST"])
def save_proxy():
    if "chat_id" not in session: return jsonify({"success": False}), 401
    proxy = request.json.get("proxy", "").strip()
    update_user_proxy(session["chat_id"], proxy)
    return jsonify({"success": True, "message": "Proxy updated successfully"})

# --- ADMIN APIs ---

@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    if str(session.get("chat_id")) != str(ADMIN_ID): return jsonify({"success": False}), 403
    return jsonify({"success": True, "stats": get_all_stats()})

@app.route("/api/admin/requirements", methods=["GET", "POST", "DELETE"])
def admin_reqs():
    if str(session.get("chat_id")) != str(ADMIN_ID): return jsonify({"success": False}), 403
    
    if request.method == "GET":
        return jsonify({"success": True, "requirements": get_requirements()})
    
    if request.method == "POST":
        data = request.json
        add_requirement(data["chat_id"], data["url"], data["name"])
        return jsonify({"success": True})
    
    if request.method == "DELETE":
        chat_id = request.args.get("chat_id")
        remove_requirement(chat_id)
        return jsonify({"success": True})

# --- HITTER API ---

@app.route("/api/hit", methods=["POST"])
def hit():
    if "chat_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    # Requirement Check
    req_res = check_requirements() # Internal call
    if not req_res.json.get("all_joined"):
        return jsonify({"success": False, "message": "Please join required channels first!"}), 403

    data = request.json
    gate = data.get("gate", "checkout")
    url = data.get("url")
    card = data.get("card")
    
    if not url or not card:
        return jsonify({"success": False, "message": "URL and Card are required"}), 400

    # Get User Proxy
    user = get_user(session["chat_id"])
    proxy = user["proxy"] if user and user["proxy"] else None

    try:
        increment_stat("total_hits")
        
        # Build command
        # python browser_hitter.py <url> <card> [proxy]
        cmd = [os.sys.executable, "browser_hitter.py", url, card]
        if proxy: cmd.append(proxy)
        
        print(f"🚀 Launching local hitter: {' '.join(cmd)}")
        
        # Run subprocess and capture output
        # NOTE: This is synchronous in Flask, so it blocks the server during the hit.
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        output_txt = process.stdout + "\n" + process.stderr
        
        # Parse output for results
        status = "unknown"
        message = "Starting..."
        site = "Stripe"
        amount = "10.00 USD" 
        
        # Split into lines and look for statuses
        lines = output_txt.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if "SUCCESS" in line:
                status = "charged"
                message = "Charged Successfully"
                increment_stat("success_hits")
                
                # Send Log to specific Telegram Group (-1003721268860)
                log_group_id = "-1003721268860"
                user_data = get_user(session["chat_id"])
                user_display = user_data["username"] if user_data else f"User {session['chat_id']}"
                
                log_msg = (
                    "🔥 <b>HIT DETECTED</b> ⚡️\n"
                    f"👤 {user_display} ʙᴇɴ [Silver]\n"
                    f"↔️ Gateway: Stripe {gate.capitalize()} Hitter\n"
                    "✅ Response: Charged Successfully\n"
                    f"🌐 Site: {site}\n"
                    f"💰 Amount: {amount}"
                )
                send_telegram_msg(log_group_id, log_msg)
                break # Success is final
                
            elif "FAILURE" in line or "declined" in line.lower():
                status = "declined"
                message = "Card Declined"
            elif "3DS" in line or "security" in line.lower():
                status = "3ds"
                message = "3D Secure Required"
            elif "hCaptcha detected" in line:
                message = "🧩 Solving hCaptcha..."
            elif "✅ hCaptcha Solved!" in line:
                message = "✅ hCaptcha Solved!"
            elif "⌨️ Inputting card" in line:
                message = "⌨️ Inputting Card..."
            elif "🔘 Clicking Pay" in line:
                message = "🔘 Clicking Pay..."
            elif "⌛ Waiting for payment result" in line:
                message = "⌛ Checking Result..."
            elif "UNKNOWN: Result not detected" in line:
                message = "UNKNOWN: Result not detected"
            elif "ERROR:" in line:
                message = f"Error: {line.split('ERROR:')[1].strip()}"
            elif "traceback" in line.lower() or "line " in line.lower():
                # Capture part of the error trace
                message = f"Critical Error: {line.strip()}"

        return jsonify({"status": status, "message": message, "site": site, "amount": amount})
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server Error: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"✅ Dashboard Server running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)
