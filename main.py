import os
import telebot
import google.generativeai as genai
from metaapi_cloud_sdk import MetaApi
import asyncio

# 1. Fetching all configuration secrets from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
METAAPI_ACCOUNT_ID = os.environ.get('METAAPI_ACCOUNT_ID')
METAAPI_TOKEN = os.environ.get('METAAPI_TOKEN')

# Initialize Telegram Bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Initialize Gemini AI Model
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Initialize MetaApi
meta_api = MetaApi(METAAPI_TOKEN)

async def execute_market_order(symbol: str, action: str, volume: float):
    try:
        account = await meta_api.metatrader_account_api.get_account(METAAPI_ACCOUNT_ID)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        order_type = 'ORDER_TYPE_BUY' if action.upper() == 'BUY' else 'ORDER_TYPE_SELL'
        result = await connection.create_market_order(symbol.upper(), order_type, volume)
        return f"✅ Order Executed! Position ID: {result.get('positionId', 'N/A')}"
    except Exception as e:
        return f"❌ Failed to execute: {str(e)}"

@bot.message_handler(func=lambda message: str(message.chat.id) == str(TELEGRAM_CHAT_ID))
def handle_message(message):
    user_input = message.text
    bot.reply_to(message, "🧠 AI is processing your request...")
    
    # Simple logic to identify simple trade commands
    parts = user_input.split()
    if len(parts) >= 3:
        action = parts[0]
        symbol = parts[1]
        volume = float(parts[2])
        
        # Execute trade
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(execute_market_order(symbol, action, volume))
        bot.reply_to(message, result)
    else:
        bot.reply_to(message, "Please use the format: 'BUY EURUSD 0.01'")

if __name__ == "__main__":
    bot.infinity_polling()
