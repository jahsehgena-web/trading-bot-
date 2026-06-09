import asyncio
import os
import telebot
from metaapi_cloud_sdk import MetaApi
from google import genai

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
METAAPI_ACCOUNT_ID = os.getenv("METAAPI_ACCOUNT_ID")

# Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

# Telegram bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


async def main():
    # Initialize MetaApi
    meta_api = MetaApi(METAAPI_TOKEN)

    # Get account
    account = await meta_api.metatrader_account_api.get_account(
        METAAPI_ACCOUNT_ID
    )

    # Connect to account
    connection = account.get_streaming_connection()
    await connection.connect()
    await connection.wait_synchronized()

    print("Bot connected successfully.")

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        bot.reply_to(
            message,
            "Bot is online. Send your trading commands!"
        )

    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        bot.reply_to(message, "🧠 AI is analyzing your input...")

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=message.text
            )

            bot.reply_to(
                message,
                f"✅ AI Response:\n{response.text}"
            )

        except Exception as e:
            bot.reply_to(
                message,
                f"❌ AI Error:\n{str(e)}"
            )

    bot.infinity_polling()


if __name__ == "__main__":
    asyncio.run(main())
