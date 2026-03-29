import telebot
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", 0))

if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.chat.id
    bot.reply_to(msg, f"🔐 <b>Auto Hitter Authentication</b>\n\n"
                     f"Your Chat ID: <code>{uid}</code>\n\n"
                     f"Use this ID on the web dashboard to receive your login code.", parse_mode="HTML")

print(f"🚀 Auth Bot started... Web Dashboard ready at http://localhost:5000")
bot.infinity_polling()