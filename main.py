import os
import telebot
import pandas as pd
import yfinance as yf
import numpy as np
import google.generativeai as genai

# =========================
# CONFIG
# =========================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

genai.configure(api_key=GEMINI_KEY)

MODEL_NAME = "gemini-1.5-flash"  # stable + lower quota pressure


# =========================
# DATA LOADING
# =========================
def get_data(symbol):
    try:
        df = yf.download(symbol, interval="15m", period="30d", progress=False)

        if df is None or df.empty:
            return None

        df = df.dropna()

        if len(df) < 20:
            return None

        return df

    except Exception as e:
        print("DATA ERROR:", e)
        return None


# =========================
# INDICATORS
# =========================
def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def market_structure(df):
    try:
        highs = df["High"].values
        lows = df["Low"].values

        if len(highs) < 5:
            return "UNDEFINED"

        if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
            return "BULLISH"
        elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
            return "BEARISH"

        return "RANGE"

    except:
        return "UNDEFINED"


# =========================
# ANALYSIS ENGINE
# =========================
def analyze(symbol):
    symbol = symbol.upper().strip()

    if "EURUSD" in symbol:
        symbol = "EURUSD=X"

    df = get_data(symbol)

    if df is None:
        return {"status": "NO TRADE", "reason": "No data available"}

    if len(df) < 20:
        return {"status": "NO TRADE", "reason": "Not enough data"}

    try:
        df["ema20"] = ema(df["Close"], 20)
        df["ema200"] = ema(df["Close"], 200)

        last_close = float(df["Close"].iloc[-1])
        ema20 = float(df["ema20"].iloc[-1])
        ema200 = float(df["ema200"].iloc[-1])

        trend = "BUY" if ema20 > ema200 else "SELL"

        structure = market_structure(df)

        if structure == "UNDEFINED":
            return {"status": "NO TRADE", "reason": "Weak structure"}

        # simple SL/TP logic
        if trend == "BUY":
            sl = last_close * 0.997
            tp = last_close * 1.006
        else:
            sl = last_close * 1.003
            tp = last_close * 0.994

        rr = abs(tp - last_close) / abs(last_close - sl)

        if rr < 1.5:
            return {"status": "NO TRADE", "reason": "Low RR"}

        return {
            "status": trend,
            "entry": last_close,
            "sl": sl,
            "tp": tp,
            "rr": round(rr, 2),
            "structure": structure
        }

    except Exception as e:
        return {"status": "NO TRADE", "reason": str(e)}


# =========================
# FORMAT OUTPUT
# =========================
def format_signal(symbol, result):
    if result["status"] == "NO TRADE":
        return f"⚠️ NO TRADE\nReason: {result['reason']}"

    return f"""
📊 {symbol}
📌 Signal: {result['status']}
💰 Entry: {result['entry']:.5f}
🛑 SL: {result['sl']:.5f}
🎯 TP: {result['tp']:.5f}
📈 RR: {result['rr']}
📉 Structure: {result['structure']}
"""


# =========================
# TELEGRAM HANDLER
# =========================
@bot.message_handler(func=lambda m: True)
def handle(m):
    try:
        symbol = m.text.strip()

        result = analyze(symbol)

        output = format_signal(symbol, result)

        bot.reply_to(m, output)

    except Exception as e:
        bot.reply_to(m, f"System Error: {str(e)}")


print("Bot running...")
bot.infinity_polling()
