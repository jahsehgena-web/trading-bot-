import asyncio
import os
import telebot
from metaapi_cloud_sdk import MetaApi
import google.generativeai as genai

# Setup environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
METAAPI_TOKEN = os.getenv('METAAPI_TOKEN')
METAAPI_ACCOUNT_ID = os.getenv('METAAPI_ACCOUNT_ID')

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Initialize Telebot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

async def main():
    # Correct MetaApi initialization
    meta_api = MetaApi(METAAPI_TOKEN)
    
    # Retrieve the account
    account = await meta_api.metaclients.get_account(METAAPI_ACCOUNT_ID)
    
    # Connect to your trading account
    connection = account.get_streaming_connection()
    await connection.connect()
    await connection.wait_synchronized()
    
    print("Bot has started successfully and is connected to your MetaApi account!")

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        bot.reply_to(message, "Bot is online. Send your trading commands!")

    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        # AI Processing Logic
        bot.reply_to(message, "🧠 AI is analyzing your input...")
        
        # Example Gemini call
        try:
            response = model.generate_content(message.text)
            bot.reply_to(message, f"✅ AI Response: {response.text}")
        except Exception as e:
            bot.reply_to(message, f"❌ Error processing with AI: {str(e)}")

    # Keep the bot polling
    bot.infinity_polling()

if __name__ == '__main__':
    asyncio.run(main())
