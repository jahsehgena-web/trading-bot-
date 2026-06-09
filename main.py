import os
import telebot
import pandas as pd
import numpy as np
from google import genai

# ======================
# ENV
# ======================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
MODEL = "gemini-2.0-flash"

# ======================
# MARKET DATA (TEMP SIMULATION)
# Replace later with real API (OANDA, Binance, MT5 bridge)
# ======================
def get_market_data(symbol):
    np.random.seed(len(symbol))

    prices = np.cumsum(np.random.randn(200)) + 100
    df = pd.DataFrame({"close": prices})

    return df

# ======================
# EMA ENGINE
# ======================
def calculate_ema(df):
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    return df

# ======================
# SIGNAL ENGINE
# ======================
def generate_signal(df, symbol):
    last_close = float(df["close"].iloc[-1])
    ema20 = float(df["ema20"].iloc[-1])
    ema200 = float(df["ema200"].iloc[-1])

    # Trend logic
    if ema20 > ema200:
        signal = "BUY"
    elif ema20 < ema200:
        signal = "SELL"
    else:
        signal = "WAIT"

    entry = last_close
    sl = ema200 if signal == "BUY" else ema20
    tp = entry + (abs(entry - sl) * 2)

    rr = abs(tp - entry) / abs(entry - sl) if entry != sl else 0
    quality = "LOW QUALITY" if rr < 1.5 else "HIGH QUALITY"

    return {
        "symbol": symbol,
        "signal": signal,
        "entry": round(entry, 5),
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "rr": round(rr, 2),
        "quality": quality
    }

# ======================
# GEMINI FORMATTER (OPTIONAL)
# ======================
def explain(signal):
    if not client:
        return None

    try:
        prompt = f"""
You are a trading assistant.

Format this into a clean Telegram signal:

{signal}

Keep it short, structured, professional.
"""

        res = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        return res.text

    except:
        return None

# ======================
# TELEGRAM
# ======================
@bot.message_handler(commands=["start"])
def start(msg):
    bot.reply_to(msg, "Bot active. Send a pair like EURUSD or BTCUSD.")

@bot.message_handler(func=lambda m: True)
def handle(msg):
    symbol = msg.text.strip().upper()

    bot.reply_to(msg, "Analyzing market structure...")

    try:
        df = get_market_data(symbol)
        df = calculate_ema(df)

        signal = generate_signal(df, symbol)

        ai = explain(signal)

        if ai:
            bot.reply_to(msg, ai)
        else:
            text = f"""
📊 {signal['symbol']}
📌 Signal: {signal['signal']}
💰 Entry: {signal['entry']}
🛑 SL: {signal['sl']}
🎯 TP: {signal['tp']}
📈 RR: {signal['rr']}
⚠️ {signal['quality']}
"""
            bot.reply_to(msg, text)

    except Exception as e:
        bot.reply_to(msg, f"Error: {str(e)}")

# ======================
# RUN
# ======================
print("Bot running...")
bot.infinity_polling()
