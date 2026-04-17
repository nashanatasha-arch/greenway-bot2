import os
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # необязательно
SHOP_URL = os.getenv("SHOP_URL")  # ссылка на интернет-магазин
TEAM_URL = os.getenv("TEAM_URL")  # ссылка на команду / анкету / чат

# Простая память в RAM. Для первого этапа хватает.
users = {}


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()


def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def get_user(user_id: int):
    if user_id not in users:
        users[user_id] = {
            "stage": "new",
            "segment": None,
            "contacts_written": 0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "last_action": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    return users[user_id]


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str):
    if ADMIN_ID:
        try:
            await context.bot.send_message(chat_id=int(ADMIN_ID), text=text)
        except Exception:
            pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    user["stage"] = "start"
    user["last_action"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    keyboard = [
        ["🚀 Старт", "📘 Хочу систему"],
        ["👥 Хочу в команду", "🛍 Хочу продукт"],
    ]

    await update.message.reply_text(
        "Привет 👋\n\n"
        "Я помогу тебе включиться в систему за 7 дней:"
        " первые действия, первые клиенты, первые деньги.\n\n"
        "Выбери, что тебе сейчас ближе:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )

    await notify_admin(context, f"🆕 Новый лид: {user_id}")
    await schedule_day_messages(context, user_id)


async def show_income_flow(update: Update):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Начать сейчас", callback_data="start_now")],
        [InlineKeyboardButton("📩 Дай скрипт", callback_data="give_script")],
    ])
    await update.message.reply_text(
        "Отлично 🔥\n\n"
        "Если тебе интересна подработка, начнём с простого:"
        " первые сообщения → первые ответы → первые деньги.\n\n"
        "Первый шаг: написать 10 знакомым по готовому сообщению.\n\n"
        "Жми кнопку ниже:",
        reply_markup=keyboard,
    )


async def show_career_flow(update: Update):
    await update.message.reply_text(
        "🚀 Если ты рассматриваешь это как основную работу — важно сразу идти по системе.\n\n"
        "Что ты получаешь:\n"
        "• понятный план на 7 дней\n"
        "• первые действия без перегруза\n"
        "• выход на первые деньги\n"
        "• возможность масштабировать через команду\n\n"
        "Напиши: СТАРТ — и я проведу тебя по системе шаг за шагом."
    )


async def show_system_flow(update: Update):
    await update.message.reply_text(
        "📘 Система запуска на 7 дней:\n\n"
        "1 день — включение\n"
        "2 день — первые сообщения\n"
        "3 день — продукт\n"
        "4 день — обучение\n"
        "5 день — дожим\n"
        "6 день — команда\n"
        "7 день — разбор результата\n\n"
        "Если хочешь пройти её со мной — напиши: СТАРТ"
    )


async def show_team_flow(update: Update):
    keyboard = None
    if TEAM_URL:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Перейти в команду", url=TEAM_URL)]
        ])

    await update.message.reply_text(
        "👥 Команда — это путь для тех, кто хочет не просто пользоваться продуктом, а строить доход через систему.\n\n"
        "Напиши: КОМАНДА\n"
        "И я дам тебе первый шаг для входа.",
        reply_markup=keyboard,
    )


async def show_product_flow(update: Update):
    keyboard = None
    if SHOP_URL:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍 Перейти в магазин", url=SHOP_URL)]
        ])

    text = (
        "🛍 Продукт — это простой вход: польза для здоровья + возможность рекомендовать дальше.\n\n"
        "Нажми кнопку ниже, чтобы перейти в магазин."
        if SHOP_URL else
        "🛍 Продукт — это простой вход: польза для здоровья + возможность рекомендовать дальше.\n\n"
        "Пока ссылка не добавлена. В Render добавь переменную SHOP_URL, и кнопка будет вести прямо в магазин."
    )

    await update.message.reply_text(text, reply_markup=keyboard)


async def send_day_message(bot, chat_id: int, day: int):
    messages = {
        1: "День 1️⃣\n\nСтартуем. Сегодня важен первый шаг: напиши 10 знакомым. Нужен текст — напиши: СКРИПТ",
        2: "День 2️⃣\n\nПроверь ответы. Даже 1 диалог — уже движение. Нужен дожим — напиши: ДОЖИМ",
        3: "День 3️⃣\n\nДень продукта. Выбери: энергия / кожа / ЖКТ / иммунитет / вес",
        4: "День 4️⃣\n\nФокус: 1 действие = результат. Напиши: СТАРТ / ОТВЕТЫ / ИНТЕРЕС",
        5: "День 5️⃣\n\nДожим: напиши тем, кто не ответил. Это нормально и работает",
        6: "День 6️⃣\n\nХочешь доход через людей — напиши: КОМАНДА",
        7: "День 7️⃣\n\nИтог. Напиши: ИТОГ и я скажу следующий шаг"
    }
    await bot.send_message(chat_id=chat_id, text=messages[day])


async def scheduled_day_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    await send_day_message(context.bot, data["chat_id"], data["day"])


async def schedule_day_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    for day in range(1, 8):
        context.job_queue.run_once(
            scheduled_day_job,
            when=day * 86400,
            data={"chat_id": chat_id, "day": day},
            name=f"day_{day}_{chat_id}"
        )


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    text = (update.message.text or "").strip()
    text_low = text.lower()
    user["last_action"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    if text == "/start":
        await start(update, context)
        return

    if text == "🚀 Старт":
        user["stage"] = "start_choice"
        keyboard = [
            ["🛍 Просто купить продукт"],
            ["💸 Хочу подзаработать"],
            ["🚀 Ищу основную работу"],
        ]
        await update.message.reply_text(
            "Супер, давай поймём, что тебе сейчас ближе 👇\n\nВыбери один вариант:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return

    if text == "🛍 Просто купить продукт":
        user["stage"] = "product"
        user["segment"] = "product"
        await show_product_flow(update)
        return

    if text == "💸 Хочу подзаработать":
        user["stage"] = "income"
        user["segment"] = "income"
        await show_income_flow(update)
        return

    if text == "🚀 Ищу основную работу":
        user["stage"] = "career"
        user["segment"] = "career"
        await show_career_flow(update)
        return

    if text == "📘 Хочу систему":
        await show_system_flow(update)
        return

    if text == "👥 Хочу в команду":
        await show_team_flow(update)
        return

    if text == "🛍 Хочу продукт":
        await show_product_flow(update)
        return

    if text_low == "старт":
        user["stage"] = "started"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я написал 10 людям", callback_data="written_10")],
            [InlineKeyboardButton("📩 Дай скрипт", callback_data="give_script")],
        ])
        await update.message.reply_text(
            "Супер. Твоё первое действие:\n\n"
            "Напиши 10 знакомым:\n"
            "«Привет! Я сейчас прохожу систему запуска в онлайн-бизнесе. Можно задам тебе один вопрос?»\n\n"
            "Когда сделаешь — нажми кнопку ниже.",
            reply_markup=keyboard,
        )
        return

    if text_low == "скрипт":
        await update.message.reply_text(
            "Готовый скрипт 👇\n\n"
            "Привет! Я сейчас прохожу систему запуска в онлайн-бизнесе. Можно задам тебе один вопрос?"
        )
        return

    await update.message.reply_text("Выбери действие из меню 👇")


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "start_now":
        await query.edit_message_text("Давай стартуем 🚀")


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("TOKEN не найден")

    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(CallbackQueryHandler(callback))

    print("Bot running...")
    app.run_polling()
