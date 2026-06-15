from telegram import Update
from telegram.ext import Application, CommandHandler

BOT_TOKEN = "8798378718:AAGRxt_IwUR0m8a2M97l-5TPn8PhWpcNL9s"

async def start(update: Update, context):
    await update.message.reply_text("✅ Бот работает!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🤖 Бот запущен! Напиши /start")
    app.run_polling()

if __name__ == "__main__":
    main()
