import os
import telebot
import pandas as pd
from google import genai

# =====================
# ENV VARIABLES
# =====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN or GEMINI_API_KEY")

# =====================
# GEMINI (NEW SDK)
# =====================
client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.0-flash"

SYSTEM_PROMPT = """
You are a trading analysis assistant.
Return structured signals with:
- Trend
- Entry
- Stop Loss
- Take Profit
- Risk note
Be precise and do not hallucinate prices.
"""

# =====================
# TELEGRAM BOT
# =====================
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def analyze_market(text: str) -> str:
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=SYSTEM_PROMPT + "\n\nUser input:\n" + text
        )

        return response.text

    except Exception as e:
        return f"AI Error: {str(e)}"


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Bot is active. Send a pair like EURUSD or BTCUSD.")

@bot.message_handler(func=lambda message: True)
def handle(message):
    bot.reply_to(message, "Analyzing market structure...")

    result = analyze_market(message.text)

    bot.reply_to(message, result)


# =====================
# RUN
# =====================
print("Bot is running...")
bot.infinity_polling()
