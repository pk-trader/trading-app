import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "7730999818:AAH3mD_Nn_zJ6uD9T_5w8A_XYZ"  # তোর আসল বট টোকেন বসাবি
WEB_APP_URL = "https://pk-trader.github.io/trading-app/"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 OPEN PK TRADER REAL PRO", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    await update.message.reply_text(
        "⚡ **WELCOME TO PK TRADER REAL PRO** ⚡\n\n"
        "✔ Live Crypto & Major Forex Market Analysis\n"
        "✔ 1-Min Candle Expiry Timing Engine\n"
        "✔ Multi-Indicator Confluence Calculations\n\n"
        "Click below to launch the Mini App:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot is running properly...")
    app.run_polling()