import os
import telebot
import pandas as pd
import numpy as np
import yfinance as yf
import google.generativeai as genai

# =========================
# CONFIG
# =========================
bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# =========================
# DATA
# =========================

def get_data(symbol, interval):
    df = yf.download(symbol, interval=interval, period="5d")
    df = df.dropna()
    return df

# =========================
# INDICATORS
# =========================

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def swings(df, lookback=3):
    highs = df["High"]
    lows = df["Low"]

    swing_highs = []
    swing_lows = []

    for i in range(lookback, len(df) - lookback):
        if highs[i] == max(highs[i-lookback:i+lookback]):
            swing_highs.append((i, highs[i]))
        if lows[i] == min(lows[i-lookback:i+lookback]):
            swing_lows.append((i, lows[i]))

    return swing_highs, swing_lows

# =========================
# STRUCTURE ENGINE
# =========================

def market_structure(df):
    swing_highs, swing_lows = swings(df)

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "UNDEFINED"

    hh = swing_highs[-1][1] > swing_highs[-2][1]
    hl = swing_lows[-1][1] > swing_lows[-2][1]

    lh = swing_highs[-1][1] < swing_highs[-2][1]
    ll = swing_lows[-1][1] < swing_lows[-2][1]

    if hh and hl:
        return "BULLISH"
    elif lh and ll:
        return "BEARISH"
    else:
        return "RANGE"

# =========================
# LIQUIDITY SWEEP (simple but real)
# =========================

def liquidity_sweep(df):
    highs = df["High"].values
    lows = df["Low"].values
    closes = df["Close"].values

    # sweep high then reject
    if highs[-1] > max(highs[-20:-2]) and closes[-1] < highs[-1]:
        return "BEARISH_SWEEP"

    # sweep low then reject
    if lows[-1] < min(lows[-20:-2]) and closes[-1] > lows[-1]:
        return "BULLISH_SWEEP"

    return "NONE"

# =========================
# STRATEGY ENGINE
# =========================

def analyze(symbol):

    m15 = get_data(symbol, "15m")
    h1 = get_data(symbol, "60m")

    if len(m15) < 50 or len(h1) < 50:
        return {"status": "NO TRADE", "reason": "Not enough data"}

    # EMA trend (H1)
    h1["ema20"] = ema(h1["Close"], 20)
    h1["ema200"] = ema(h1["Close"], 200)

    trend = "BUY" if h1["ema20"].iloc[-1] > h1["ema200"].iloc[-1] else "SELL"

    # Structure
    struct = market_structure(m15)

    # Liquidity
    sweep = liquidity_sweep(m15)

    price = float(m15["Close"].iloc[-1])

    # FILTERS
    if struct == "UNDEFINED":
        return {"status": "NO TRADE", "reason": "Weak structure"}

    if trend == "BUY" and struct != "BULLISH":
        return {"status": "NO TRADE", "reason": "Trend-structure mismatch"}

    if trend == "SELL" and struct != "BEARISH":
        return {"status": "NO TRADE", "reason": "Trend-structure mismatch"}

    if trend == "BUY" and sweep != "BULLISH_SWEEP":
        return {"status": "NO TRADE", "reason": "No liquidity confirmation"}

    if trend == "SELL" and sweep != "BEARISH_SWEEP":
        return {"status": "NO TRADE", "reason": "No liquidity confirmation"}

    sl = price * (0.997 if trend == "BUY" else 1.003)
    tp = price * (1.006 if trend == "BUY" else 0.994)

    rr = abs(tp - price) / abs(price - sl)

    if rr < 1.5:
        return {"status": "NO TRADE", "reason": "Low RR"}

    return {
        "status": trend,
        "entry": price,
        "sl": sl,
        "tp": tp,
        "rr": round(rr, 2),
        "structure": struct,
        "sweep": sweep
    }

# =========================
# GEMINI FORMAT ONLY
# =========================

def format_signal(signal, symbol):

    if signal["status"] == "NO TRADE":
        return f"⚠️ NO TRADE\nReason: {signal['reason']}"

    prompt = f"""
Format this trading signal:

PAIR: {symbol}
DIRECTION: {signal['status']}
ENTRY: {signal['entry']}
SL: {signal['sl']}
TP: {signal['tp']}
RR: {signal['rr']}
STRUCTURE: {signal['structure']}
LIQUIDITY: {signal['sweep']}

Rules:
- Do not change values
- Only format cleanly for Telegram
"""

    try:
        return model.generate_content(prompt).text
    except:
        return str(signal)

# =========================
# TELEGRAM
# =========================

@bot.message_handler(func=lambda m: True)
def handle(m):
    try:
        symbol = m.text.strip().upper()

        if "USD" not in symbol:
            bot.reply_to(m, "Send a valid pair like EURUSD or GBPUSD")
            return

        signal = analyze(symbol + "=X")
        output = format_signal(signal, symbol)

        bot.reply_to(m, output)

    except Exception as e:
        bot.reply_to(m, f"Error: {str(e)}")

print("SMC Bot running...")
bot.infinity_polling()
