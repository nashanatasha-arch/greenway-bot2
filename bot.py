import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = os.getenv("TOKEN")

users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users[user_id] = {"stage": "new"}

    keyboard = [
        ["🚀 Старт", "📘 Система"],
        ["👥 Партнёр", "🛍 Продукт"]
    ]

    await update.message.reply_text(
        "🔥 Привет! Я помогу тебе запустить систему за 7 дней.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    if "старт" in text:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Я начал", callback_data="started")]
        ])
        await update.message.reply_text(
            "🚀 Твой шаг: напиши 10 людям простое сообщение:\n'Можно вопрос?'",
            reply_markup=keyboard
        )

    elif "система" in text:
        await update.message.reply_text("📘 Система: 7 дней запуска. Напиши СТАРТ")

    elif "парт" in text:
        await update.message.reply_text("👥 Партнёрство: давай разберём твой старт")

    elif "продукт" in text:
        await update.message.reply_text("🛍 Подберём продукт под тебя")

    else:
        await update.message.reply_text("Выбери: Старт / Система / Партнёр / Продукт")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔥 Отлично! Двигайся дальше по системе.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(CallbackQueryHandler(callback))

    print("Bot running...")
    app.run_polling()
