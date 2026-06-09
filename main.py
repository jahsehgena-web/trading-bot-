import os
import telebot
import yfinance as yf
import numpy as np
from google import genai

# =====================
# ENV
# =====================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# =====================
# SYMBOL MAP
# =====================
def normalize_symbol(text):
    mapping = {
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
        "XAUUSD": "GC=F",
        "GOLD": "GC=F",
        "BTC": "BTC-USD",
        "ETH": "ETH-USD"
    }
    return mapping.get(text.upper().strip(), "EURUSD=X")

# =====================
# DATA FETCH (HARDENED)
# =====================
def get_data(symbol):
    try:
        df = yf.download(symbol, interval="15m", period="5d")

        if df is None or df.empty or len(df) < 50:
            return None

        df = df.copy()

        # force clean numeric conversion
        df["Close"] = df["Close"].astype(float)
        df["High"] = df["High"].astype(float)
        df["Low"] = df["Low"].astype(float)

        df["EMA20"] = df["Close"].ewm(span=20).mean()
        df["EMA200"] = df["Close"].ewm(span=200).mean()

        return df

    except Exception:
        return None

# =====================
# TREND (100% SAFE SCALAR)
# =====================
def get_trend(df):
    last = df.iloc[-1]

    ema20 = np.float64(last["EMA20"])
    ema200 = np.float64(last["EMA200"])

    if ema20 > ema200:
        return "BULLISH"
    elif ema20 < ema200:
        return "BEARISH"
    return "SIDEWAYS"

# =====================
# LIQUIDITY CHECK
# =====================
def liquidity_sweep(df):
    try:
        if len(df) < 30:
            return "NO_SWEEP"

        recent_high = df["High"].rolling(20).max().iloc[-2]
        recent_low = df["Low"].rolling(20).min().iloc[-2]
        last_close = df["Close"].iloc[-1]

        last_close = float(last_close)

        if last_close > recent_high:
            return "BUY_SWEEP"
        elif last_close < recent_low:
            return "SELL_SWEEP"

        return "NO_SWEEP"

    except Exception:
        return "NO_SWEEP"

# =====================
# SCORE ENGINE
# =====================
def score_trade(trend, sweep):
    score = 50

    if trend in ["BULLISH", "BEARISH"]:
        score += 20

    if sweep != "NO_SWEEP":
        score += 20

    return max(0, min(100, score))

# =====================
# ANALYSIS ENGINE
# =====================
def analyze(user_input):

    symbol = normalize_symbol(user_input)

    df = get_data(symbol)

    if df is None:
        return "❌ No market data available. Try again later.", 0

    trend = get_trend(df)
    sweep = liquidity_sweep(df)
    score = score_trade(trend, sweep)

    last_price = float(df["Close"].iloc[-1])

    prompt = f"""
You are a professional trading analyst.

PAIR: {symbol}
TREND: {trend}
LIQUIDITY: {sweep}
SCORE: {score}/100
PRICE: {last_price}

Rules:
- If score < 60 → NO TRADE
- Be strict
- Do not hallucinate

Return:

PAIR:
DIRECTION:
ENTRY:
STOP LOSS:
TAKE PROFIT:
REASON:
QUALITY:
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text, score

# =====================
# TELEGRAM BOT
# =====================
@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Bot active. Send a pair like EURUSD")

@bot.message_handler(func=lambda m: True)
def handle(message):
    bot.reply_to(message, "Analyzing market structure...")

    try:
        result, score = analyze(message.text)

        bot.reply_to(
            message,
            f"📊 ANALYSIS\n\nScore: {score}/100\n\n{result}"
        )

    except Exception as e:
        bot.reply_to(message, f"⚠️ Error: {str(e)}")

# =====================
# RUN
# =====================
if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
