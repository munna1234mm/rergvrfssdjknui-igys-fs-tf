import threading
import os
import time
from server import app as flask_app
from bot import bot as tele_bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_bot():
    if not tele_bot:
        print("❌ BOT_TOKEN not found. Bot thread will not start.")
        return
    
    print("🚀 Starting Telegram Auth Bot thread...")
    while True:
        try:
            tele_bot.infinity_polling()
        except Exception as e:
            print(f"⚠️ Bot polling failed: {e}. Restarting in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    # 1. Start Bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # 2. Start Flask Server in the main thread (Render uses 'PORT' env var)
    port = int(os.environ.get("PORT", 5000))
    print(f"🔥 Starting Combined Service on port {port}...")
    flask_app.run(host="0.0.0.0", port=port)
