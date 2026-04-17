import os
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
ADMIN_ID = os.getenv("ADMIN_ID")  # необязательно, можно оставить пустым

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
        ["🚀 Хочу доход", "📘 Хочу систему"],
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


async def show_income_flow(update: Update):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Начать сейчас", callback_data="start_now")],
        [InlineKeyboardButton("📩 Дай скрипт", callback_data="give_script")],
    ])
    await update.message.reply_text(
        "Отлично 🔥\n\n"
        "Твоя цель сейчас — не просто читать, а начать действия.\n"
        "Первый шаг: написать 10 знакомым по готовому сообщению.\n\n"
        "Жми кнопку ниже:",
        reply_markup=keyboard,
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
    await update.message.reply_text(
        "👥 Команда — это путь для тех, кто хочет не просто пользоваться продуктом, а строить доход через систему.\n\n"
        "Напиши: КОМАНДА\n"
        "И я дам тебе первый шаг для входа."
    )


async def show_product_flow(update: Update):
    await update.message.reply_text(
        "🛍 Продукт — это простой вход: польза для здоровья + возможность рекомендовать дальше.\n\n"
        "Напиши: ПРОДУКТ\n"
        "И я помогу подобрать первый вариант."
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

    if text == "🚀 Хочу доход":
        user["stage"] = "income"
        user["segment"] = "income"
        await show_income_flow(update)
        await notify_admin(context, f"💸 Лид выбрал доход: {user_id}")
        return

    if text == "📘 Хочу систему":
        user["stage"] = "system"
        user["segment"] = "system"
        await show_system_flow(update)
        return

    if text == "👥 Хочу в команду":
        user["stage"] = "team"
        user["segment"] = "team"
        await show_team_flow(update)
        await notify_admin(context, f"👥 Лид выбрал команду: {user_id}")
        return

    if text == "🛍 Хочу продукт":
        user["stage"] = "product"
        user["segment"] = "product"
        await show_product_flow(update)
        await notify_admin(context, f"🛍 Лид выбрал продукт: {user_id}")
        return

    if text_low == "старт":
        user["stage"] = "started"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я написал 10 людям", callback_data="written_10")],
            [InlineKeyboardButton("📩 Дай скрипт", callback_data="give_script")],
        ])
        await update.message.reply_text(
            "Супер. Твоё первое действие на сегодня:\n\n"
            "Напиши 10 знакомым:\n"
            "«Привет! Я сейчас прохожу систему запуска в онлайн-бизнесе. Можно задам тебе один вопрос?»\n\n"
            "Когда сделаешь — нажми кнопку ниже.",
            reply_markup=keyboard,
        )
        await notify_admin(context, f"🚀 Лид нажал старт: {user_id}")
        return

    if text_low == "команда":
        user["stage"] = "team_ready"
        await update.message.reply_text(
            "Отлично. Первый шаг в команду:\n\n"
            "1. Определи цель на 30 дней\n"
            "2. Напиши 10 знакомым\n"
            "3. Пройди систему 7 дней\n\n"
            "Хочешь мой скрипт приглашения? Напиши: СКРИПТ"
        )
        return

    if text_low == "продукт":
        user["stage"] = "product_ready"
        await update.message.reply_text(
            "Отлично. Чтобы подобрать первый продукт, напиши одним словом твою задачу:\n"
            "энергия / кожа / ЖКТ / иммунитет / вес"
        )
        return

    if text_low == "скрипт":
        await update.message.reply_text(
            "Готовый скрипт 👇\n\n"
            "Привет! Я сейчас прохожу систему запуска в онлайн-бизнесе. "
            "Можно задам тебе один вопрос?"
        )
        return

    if text_low in ["энергия", "кожа", "жкт", "иммунитет", "вес"]:
        user["stage"] = f"product_{text_low}"
        await update.message.reply_text(
            f"Отлично, вижу запрос: {text}.\n"
            "Следующий шаг: я могу дать тебе короткий вариант рекомендации и сторис-подачу.\n"
            "Напиши: РЕКОМЕНДАЦИЯ"
        )
        return

    if text_low == "рекомендация":
        await update.message.reply_text(
            "Шаблон рекомендации:\n\n"
            "Я сейчас тестирую экологичный подход к поддержке здоровья. "
            "Если тебе интересно, могу показать, с чего начать мягко и без перегруза."
        )
        return

    if text_low == "/stats":
        if ADMIN_ID and str(user_id) == str(ADMIN_ID):
            total = len(users)
            income = sum(1 for u in users.values() if u.get("segment") == "income")
            team = sum(1 for u in users.values() if u.get("segment") == "team")
            product = sum(1 for u in users.values() if u.get("segment") == "product")
            started = sum(1 for u in users.values() if u.get("stage") in ["started", "written_10", "hot_lead"])
            await update.message.reply_text(
                f"📊 Статистика:\n"
                f"Всего лидов: {total}\n"
                f"Доход: {income}\n"
                f"Команда: {team}\n"
                f"Продукт: {product}\n"
                f"Стартовали: {started}"
            )
        return

    await update.message.reply_text(
        "Я тебя понял 👍\n\n"
        "Выбери, что тебе сейчас нужно:\n"
        "🚀 Хочу доход\n"
        "📘 Хочу систему\n"
        "👥 Хочу в команду\n"
        "🛍 Хочу продукт"
    )


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)
    user["last_action"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    if query.data == "start_now":
        user["stage"] = "started"
        await query.edit_message_text(
            "🔥 Отлично. Твоё первое действие:\n\n"
            "Напиши 10 людям:\n"
            "«Привет! Я сейчас прохожу систему запуска в онлайн-бизнесе. Можно задам тебе один вопрос?»\n\n"
            "После этого нажми кнопку «Я написал 10 людям» ниже в чате."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я написал 10 людям", callback_data="written_10")],
            [InlineKeyboardButton("📩 Дай скрипт", callback_data="give_script")],
        ])
        await context.bot.send_message(
            chat_id=user_id,
            text="Когда выполнишь — жми:",
            reply_markup=keyboard,
        )
        await notify_admin(context, f"🚀 Лид начал действия: {user_id}")
        return

    if query.data == "give_script":
        await query.edit_message_text(
            "📩 Готовый скрипт:\n\n"
            "Привет! Я сейчас прохожу систему запуска в онлайн-бизнесе. Можно задам тебе один вопрос?"
        )
        return

    if query.data == "written_10":
        user["stage"] = "written_10"
        user["contacts_written"] = 10
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Да, был интерес", callback_data="has_interest")],
            [InlineKeyboardButton("😐 Пока без ответа", callback_data="no_reply")],
        ])
        await query.edit_message_text(
            "Супер! Ты уже сделал главное действие 🔥\n\n"
            "Скажи, кто-то проявил интерес?",
            reply_markup=keyboard,
        )
        await notify_admin(context, f"✅ Лид написал 10 людям: {user_id}")
        return

    if query.data == "has_interest":
        user["stage"] = "hot_lead"
        await query.edit_message_text(
            "Отлично! Следующий шаг:\n\n"
            "Напиши человеку:\n"
            "«Супер, тогда я коротко покажу тебе систему / продукт, и ты решишь, интересно тебе это или нет».\n\n"
            "Если хочешь, я могу дальше дать тебе сообщение для дожима. Напиши: ДОЖИМ"
        )
        await notify_admin(context, f"🔥 У лида появился интерес: {user_id}")
        return

    if query.data == "no_reply":
        user["stage"] = "follow_up"
        await query.edit_message_text(
            "Нормально 👍 Это часть процесса.\n\n"
            "Следующий шаг — через 24 часа сделать мягкий дожим:\n"
            "«Привет, возвращаюсь к сообщению выше. Интересно тебе посмотреть короткую систему запуска?»\n\n"
            "Хочешь — я дам ещё 5 идей, кому написать. Напиши: ИДЕИ"
        )
        return


if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("TOKEN не найден в Environment Variables")

    threading.Thread(target=run_dummy_server, daemon=True).start()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(CallbackQueryHandler(callback))

    print("Bot running...")
    app.run_polling()
