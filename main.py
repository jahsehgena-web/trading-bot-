import os
import telebot
import pandas as pd
import google.generativeai as genai

# ======================
# ENV VARIABLES
# ======================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN or GEMINI_API_KEY")

# ======================
# GEMINI (OLD SDK)
# ======================
genai.configure(api_key=GEMINI_API_KEY)

# IMPORTANT FIX: correct model for old SDK
model = genai.GenerativeModel("models/gemini-pro")

# ======================
# TELEGRAM BOT
# ======================
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# ======================
# SAFE MARKET ANALYSIS (NO SERIES BUGS)
# ======================
def analyze_market(df):
    try:
        if df is None or len(df) < 2:
            return {"error": "Not enough data"}

        close = float(df["close"].iloc[-1])
        open_ = float(df["open"].iloc[-1])
        high = float(df["high"].iloc[-1])
        low = float(df["low"].iloc[-1])
        prev_close = float(df["close"].iloc[-2])

        if close > open_ and close > prev_close:
            trend = "bullish"
        elif close < open_ and close < prev_close:
            trend = "bearish"
        else:
            trend = "ranging"

        return {
            "close": close,
            "open": open_,
            "high": high,
            "low": low,
            "trend": trend
        }

    except Exception as e:
        return {"error": str(e)}

# ======================
# GEMINI CALL
# ======================
def ask_gemini(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"

# ======================
# TELEGRAM HANDLERS
# ======================
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Bot is active. Send a pair like EURUSD.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.reply_to(message, "Analyzing market structure...")

    try:
        user_input = message.text

        # MOCK DATA (replace later with real feed)
        df = pd.DataFrame({
            "open": [1.100, 1.101],
            "high": [1.105, 1.108],
            "low": [1.098, 1.099],
            "close": [1.102, 1.107]
        })

        analysis = analyze_market(df)

        if "error" in analysis:
            bot.reply_to(message, f"⚠️ Error: {analysis['error']}")
            return

        prompt = f"""
You are a professional trading analyst.

Market Data:
{analysis}

User Input:
{user_input}

Return:
- BUY / SELL / WAIT
- Clear reasoning
"""

        result = ask_gemini(prompt)

        bot.reply_to(message, result)

    except Exception as e:
        bot.reply_to(message, f"⚠️ System Error: {str(e)}")

# ======================
# RUN BOT
# ======================
if __name__ == "__main__":
    bot.infinity_polling()
