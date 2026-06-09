import os
import telebot
import yfinance as yf
import pandas as pd
from google import genai

# =====================
# ENV
# =====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# =====================
# MARKET DATA
# =====================
def get_data(symbol="EURUSD=X"):
    m15 = yf.download(symbol, interval="15m", period="5d")
    h1 = yf.download(symbol, interval="60m", period="10d")

    for df in [m15, h1]:
        df["EMA20"] = df["Close"].ewm(span=20).mean()
        df["EMA200"] = df["Close"].ewm(span=200).mean()

    return m15, h1


# =====================
# TREND
# =====================
def get_trend(df):
    last = df.iloc[-1]

    if last["EMA20"] > last["EMA200"]:
        return "BULLISH"
    elif last["EMA20"] < last["EMA200"]:
        return "BEARISH"
    return "SIDEWAYS"


# =====================
# LIQUIDITY SWEEP
# =====================
def liquidity_sweep(df):
    recent_high = df["High"].rolling(20).max().iloc[-2]
    recent_low = df["Low"].rolling(20).min().iloc[-2]
    last_close = df["Close"].iloc[-1]

    if last_close > recent_high:
        return "BUY_SWEEP"
    elif last_close < recent_low:
        return "SELL_SWEEP"
    return "NO_SWEEP"


# =====================
# SCORE SYSTEM
# =====================
def score_trade(h1_trend, m15_trend, sweep):
    score = 40

    if h1_trend == m15_trend:
        score += 30
    else:
        score -= 20

    if sweep != "NO_SWEEP":
        score += 20

    if h1_trend in ["BULLISH", "BEARISH"]:
        score += 10

    return max(0, min(100, score))


# =====================
# AI ENGINE
# =====================
def analyze(symbol):

    m15, h1 = get_data(symbol)

    h1_trend = get_trend(h1)
    m15_trend = get_trend(m15)
    sweep = liquidity_sweep(m15)
    score = score_trade(h1_trend, m15_trend, sweep)

    last_price = float(m15["Close"].iloc[-1])

    prompt = f"""
You are a professional trading assistant.

Market Data:
- H1 Trend: {h1_trend}
- M15 Trend: {m15_trend}
- Liquidity Event: {sweep}
- Trade Score: {score}/100
- Current Price: {last_price}

Rules:
- If score < 60 → NO TRADE
- Do not invent data
- Use Smart Money Concepts logic

Return format:

PAIR:
DIRECTION:
ENTRY ZONE:
STOP LOSS:
TAKE PROFIT 1:
TAKE PROFIT 2:
REASON:
QUALITY: High / Medium / Low
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text, score


# =====================
# TELEGRAM
# =====================
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Stage 2 bot is active. Send a pair like EURUSD.")


@bot.message_handler(func=lambda m: True)
def handle(message):
    bot.reply_to(message, "Analyzing market structure...")

    try:
        result, score = analyze(message.text)

        bot.reply_to(
            message,
            f"""
📊 TRADE ANALYSIS

Score: {score}/100

{result}
"""
        )

    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")


if __name__ == "__main__":
    bot.infinity_polling()
