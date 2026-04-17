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
ADMIN_ID = os.getenv("ADMIN_ID")  # необязательно
SHOP_URL = os.getenv("SHOP_URL")  # ссылка на магазин
TEAM_URL = os.getenv("TEAM_URL")  # ссылка на команду / чат / анкету, если захочешь использовать позже

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
            "segment": None,              # product / income / career / team
            "goal": None,
            "income_goal": None,
            "time_commitment": None,
            "career_reason": None,
            "career_deadline": None,
            "need": None,
            "contacts_written": 0,
            "lead_score": 0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "last_action": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    return users[user_id]


def update_score(user: dict):
    score = 0

    segment = user.get("segment")
    if segment == "product":
        score += 20
    elif segment == "income":
        score += 35
    elif segment == "career":
        score += 50
    elif segment == "team":
        score += 30

    if user.get("goal"):
        score += 10
    if user.get("income_goal"):
        score += 10
    if user.get("time_commitment"):
        score += 10
    if user.get("career_reason"):
        score += 10
    if user.get("career_deadline"):
        score += 10
    if user.get("need"):
        score += 5
    if user.get("contacts_written", 0) >= 10:
        score += 15

    user["lead_score"] = score


async def notify_admin(context: ContextTypes.DEFAULT_TYPE, text: str):
    if ADMIN_ID:
        try:
            await context.bot.send_message(chat_id=int(ADMIN_ID), text=text)
        except Exception:
            pass


async def send_lead_card(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    user = get_user(user_id)
    update_score(user)

    text = (
        "📌 CRM-лид\n\n"
        f"ID: {user_id}\n"
        f"Сегмент: {user.get('segment') or '-'}\n"
        f"Цель: {user.get('goal') or '-'}\n"
        f"Доход: {user.get('income_goal') or '-'}\n"
        f"Время: {user.get('time_commitment') or '-'}\n"
        f"Причина смены формата: {user.get('career_reason') or '-'}\n"
        f"Срок: {user.get('career_deadline') or '-'}\n"
        f"Потребность: {user.get('need') or '-'}\n"
        f"Написал 10 людям: {'да' if user.get('contacts_written', 0) >= 10 else 'нет'}\n"
        f"Score: {user.get('lead_score')}"
    )

    await notify_admin(context, text)


async def send_day_message(bot, chat_id: int, day: int):
    messages = {
        1: "День 1️⃣\n\nГлавное сегодня — не перегружаться. Один шаг лучше, чем 10 незаконченных. Хочешь начать действие — напиши: СТАРТ",
        2: "День 2️⃣\n\nПервые сообщения = первые деньги в будущем. Нужен готовый скрипт? Напиши: СКРИПТ",
        3: "День 3️⃣\n\nСегодня день продукта. Люди покупают не товар, а решение своей задачи. Выбери: энергия / кожа / ЖКТ / иммунитет / вес",
        4: "День 4️⃣\n\nОдин урок = одно действие. Не смотри всё подряд. Напиши: УРОК",
        5: "День 5️⃣\n\nСегодня день дожима. Нужен готовый текст? Напиши: ДОЖИМ",
        6: "День 6️⃣\n\nЕсли хочешь доход через людей, а не только через продукт — напиши: КОМАНДА",
        7: "День 7️⃣\n\nПодведём итог. Напиши: ИТОГ, и я помогу понять следующий шаг."
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
            name=f"day_{day}_{chat_id}",
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    user["stage"] = "welcome"
    user["last_action"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    keyboard = [
        ["🚀 Старт", "📘 Хочу систему"],
        ["👥 Хочу в команду", "🛍 Хочу продукт"],
    ]

    await update.message.reply_text(
        "Привет 👋\n\n"
        "Я помогу тебе пройти путь понятнее и быстрее.\n\n"
        "Выбери, что тебе сейчас ближе:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )

    await notify_admin(context, f"🆕 Новый лид: {user_id}")
    await schedule_day_messages(context, user_id)


async def show_system_flow(update: Update):
    await update.message.reply_text(
        "📘 Система запуска на 7 дней:\n\n"
        "1 день — включение\n"
        "2 день — первые сообщения\n"
        "3 день — продукт\n"
        "4 день — обучение\n"
        "5 день — дожим\n"
        "6 день — команда\n"
        "7 день — итог\n\n"
        "Чтобы включиться — напиши: СТАРТ"
    )


async def show_team_flow(update: Update):
    keyboard = None
    if TEAM_URL:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("👥 Перейти", url=TEAM_URL)]]
        )

    await update.message.reply_text(
        "👥 Команда — это путь для тех, кто хочет расти не только через продажи, но и через людей.\n\n"
        "Напиши: КОМАНДА\n"
        "И я дам следующий ориентир.",
        reply_markup=keyboard,
    )


async def show_product_flow(update: Update):
    keyboard = [
        ["⚡ Энергия", "✨ Кожа"],
        ["🧠 ЖКТ", "🛡 Иммунитет"],
        ["⚖️ Вес", "💬 Личный подбор"],
    ]

    await update.message.reply_text(
        "🛍 Давай подберём продукт под задачу.\n\n"
        "Выбери, что сейчас актуально:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )


async def show_income_flow(update: Update):
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔥 Начать сейчас", callback_data="start_now")],
            [InlineKeyboardButton("📩 Дай скрипт", callback_data="give_script")],
        ]
    )

    await update.message.reply_text(
        "💸 Если тебе интересна подработка, начнём с простого:\n"
        "первые действия → первые ответы → первые деньги.\n\n"
        "Сейчас я задам пару коротких вопросов, чтобы понять твой формат.",
        reply_markup=keyboard,
    )


async def show_career_flow(update: Update):
    await update.message.reply_text(
        "🚀 Если ты рассматриваешь это как основную работу — важно сразу понять мотивацию, срок и готовность к действиям.\n\n"
        "Я задам несколько коротких вопросов и покажу, как начать системно."
    )


async def ask_goal(update: Update):
    await update.message.reply_text(
        "Напиши коротко:\n\n"
        "Какая у тебя сейчас главная цель?\n"
        "Например:\n"
        "• закрыть кредит\n"
        "• выйти на свой доход\n"
        "• помочь семье\n"
        "• перестать зависеть от найма"
    )


async def ask_income_goal(update: Update):
    keyboard = [
        ["10-30 тыс"],
        ["30-50 тыс"],
        ["50-100 тыс"],
        ["100+ тыс"],
    ]
    await update.message.reply_text(
        "Какой доход тебе был бы интересен на первом этапе?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )


async def ask_time_commitment(update: Update):
    keyboard = [
        ["1 час в день"],
        ["2-3 часа в день"],
        ["Полноценная занятость"],
    ]
    await update.message.reply_text(
        "Сколько времени ты реально готов(а) уделять?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )


async def ask_career_reason(update: Update):
    await update.message.reply_text(
        "Почему ты рассматриваешь это как основную работу?\n\n"
        "Напиши коротко одним сообщением."
    )


async def ask_career_deadline(update: Update):
    keyboard = [
        ["1-3 месяца"],
        ["3-6 месяцев"],
        ["6-12 месяцев"],
        ["Готов(а) идти столько, сколько нужно"],
    ]
    await update.message.reply_text(
        "За какой срок ты хочешь выйти на новый уровень дохода?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
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
            "Супер, давай поймём, что тебе сейчас ближе 👇\n\n"
            "Выбери один вариант:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return

    if text == "📘 Хочу систему":
        user["stage"] = "system"
        await show_system_flow(update)
        return

    if text == "👥 Хочу в команду":
        user["stage"] = "team"
        user["segment"] = "team"
        await show_team_flow(update)
        await send_lead_card(context, user_id)
        return

    if text == "🛍 Хочу продукт":
        user["stage"] = "product"
        user["segment"] = "product"
        await show_product_flow(update)
        await send_lead_card(context, user_id)
        return

    if text == "🛍 Просто купить продукт":
        user["stage"] = "product"
        user["segment"] = "product"
        await show_product_flow(update)
        await send_lead_card(context, user_id)
        return

    if text == "💸 Хочу подзаработать":
        user["stage"] = "collect_goal"
        user["segment"] = "income"
        await show_income_flow(update)
        await ask_goal(update)
        return

    if text == "🚀 Ищу основную работу":
        user["stage"] = "collect_career_reason"
        user["segment"] = "career"
        await show_career_flow(update)
        await ask_career_reason(update)
        return

    if user.get("stage") == "collect_goal":
        user["goal"] = text
        user["stage"] = "collect_income_goal"
        await ask_income_goal(update)
        return

    if user.get("stage") == "collect_income_goal":
        user["income_goal"] = text
        user["stage"] = "collect_time_commitment"
        await ask_time_commitment(update)
        return

    if user.get("stage") == "collect_time_commitment":
        user["time_commitment"] = text
        user["stage"] = "qualified_income"
        update_score(user)
        await update.message.reply_text(
            "Отлично 👌\n\n"
            f"Твоя цель: {user['goal']}\n"
            f"Доход: {user['income_goal']}\n"
            f"Время: {user['time_commitment']}\n\n"
            "Теперь следующий шаг — включиться в действия.\n"
            "Напиши: СТАРТ"
        )
        await send_lead_card(context, user_id)
        return

    if user.get("stage") == "collect_career_reason":
        user["career_reason"] = text
        user["stage"] = "collect_career_goal"
        await ask_goal(update)
        return

    if user.get("stage") == "collect_career_goal":
        user["goal"] = text
        user["stage"] = "collect_career_income"
        await ask_income_goal(update)
        return

    if user.get("stage") == "collect_career_income":
        user["income_goal"] = text
        user["stage"] = "collect_career_time"
        await ask_time_commitment(update)
        return

    if user.get("stage") == "collect_career_time":
        user["time_commitment"] = text
        user["stage"] = "collect_career_deadline"
        await ask_career_deadline(update)
        return

    if user.get("stage") == "collect_career_deadline":
        user["career_deadline"] = text
        user["stage"] = "qualified_career"
        update_score(user)
        await update.message.reply_text(
            "Сильная заявка 🔥\n\n"
            f"Почему ищешь новый формат: {user['career_reason']}\n"
            f"Цель: {user['goal']}\n"
            f"Доход: {user['income_goal']}\n"
            f"Время: {user['time_commitment']}\n"
            f"Срок: {user['career_deadline']}\n\n"
            "Это уже не про «попробовать», а про систему.\n"
            "Следующий шаг — включиться в действия.\n"
            "Напиши: СТАРТ"
        )
        await send_lead_card(context, user_id)
        return

    if text_low == "старт":
        user["stage"] = "started"
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Я написал(а) 10 людям", callback_data="written_10")],
                [InlineKeyboardButton("📩 Дай скрипт", callback_data="give_script")],
            ]
        )
        await update.message.reply_text(
            "Супер. Твоё первое действие:\n\n"
            "Напиши 10 знакомым:\n"
            "«Привет! Я сейчас запускаюсь в новом проекте. Можно задам тебе один вопрос?»\n\n"
            "Когда сделаешь — нажми кнопку ниже.",
            reply_markup=keyboard,
        )
        return

    if text_low == "скрипт":
        await update.message.reply_text(
            "Готовый скрипт 👇\n\n"
            "Привет! Я сейчас запускаюсь в новом проекте. Можно задам тебе один вопрос?"
        )
        return

    if text_low == "дожим":
        await update.message.reply_text(
            "Текст для дожима 👇\n\n"
            "Привет, возвращаюсь к сообщению выше. Интересно тебе посмотреть короткую систему запуска?"
        )
        return

    if text_low == "урок":
        await update.message.reply_text(
            "Правило дня:\n\n"
            "1 урок = 1 действие.\n"
            "Не смотри всё подряд.\n"
            "Сначала узнал(а) → сразу сделал(а) маленький шаг."
        )
        return

    if text_low == "команда":
        await update.message.reply_text(
            "Команда — это следующий уровень.\n\n"
            "Сначала ты включаешь свои действия,\n"
            "потом начинаешь приглашать людей в систему."
        )
        return

    if text_low == "итог":
        await update.message.reply_text(
            "Разбор недели 👇\n\n"
            "1. Сколько людям ты написал(а)?\n"
            "2. Был ли интерес?\n"
            "3. Что было самым сложным?\n"
            "4. Хочешь идти дальше в продукт, продажи или команду?\n\n"
            "Ответь одним сообщением."
        )
        user["stage"] = "week_result"
        return

    if user.get("stage") == "week_result":
        await update.message.reply_text(
            "Супер. Это уже база для следующего этапа.\n\n"
            "Теперь важно закрепить действия и не остановиться."
        )
        await notify_admin(context, f"📊 Итог недели от {user_id}:\n{text}")
        return

    if "энерг" in text_low:
        user["need"] = "энергия"
        await update.message.reply_text(
            f"⚡ Для энергии обычно ищут решение для восстановления ресурса.\n\n"
            f"Каталог:\n{SHOP_URL}\n\n"
            "Если хочешь точнее — напиши: ПОДБОР"
        )
        await send_lead_card(context, user_id)
        return

    if "кожа" in text_low:
        user["need"] = "кожа"
        await update.message.reply_text(
            f"✨ Для кожи важен мягкий и системный подход.\n\n"
            f"Каталог:\n{SHOP_URL}\n\n"
            "Если хочешь точнее — напиши: ПОДБОР"
        )
        await send_lead_card(context, user_id)
        return

    if "жкт" in text_low:
        user["need"] = "жкт"
        await update.message.reply_text(
            f"🧠 ЖКТ — это база самочувствия.\n\n"
            f"Каталог:\n{SHOP_URL}\n\n"
            "Если хочешь точнее — напиши: ПОДБОР"
        )
        await send_lead_card(context, user_id)
        return

    if "иммун" in text_low:
        user["need"] = "иммунитет"
        await update.message.reply_text(
            f"🛡 Иммунитет — один из самых частых запросов.\n\n"
            f"Каталог:\n{SHOP_URL}\n\n"
            "Если хочешь точнее — напиши: ПОДБОР"
        )
        await send_lead_card(context, user_id)
        return

    if "вес" in text_low:
        user["need"] = "вес"
        await update.message.reply_text(
            f"⚖️ С темой веса важно идти в баланс, а не в жёсткость.\n\n"
            f"Каталог:\n{SHOP_URL}\n\n"
            "Если хочешь точнее — напиши: ПОДБОР"
        )
        await send_lead_card(context, user_id)
        return

    if "личный подбор" in text_low or text_low == "подбор":
        await update.message.reply_text(
            "Супер 👍\n\n"
            "Напиши 3 вещи:\n"
            "1. Возраст\n"
            "2. Главная цель\n"
            "3. Что сейчас беспокоит\n\n"
            "И я помогу подобрать вариант."
        )
        user["stage"] = "personal_selection"
        await send_lead_card(context, user_id)
        return

    if text_low == "/stats":
        if ADMIN_ID and str(user_id) == str(ADMIN_ID):
            total = len(users)
            product = sum(1 for u in users.values() if u.get("segment") == "product")
            income = sum(1 for u in users.values() if u.get("segment") == "income")
            career = sum(1 for u in users.values() if u.get("segment") == "career")
            team = sum(1 for u in users.values() if u.get("segment") == "team")
            hot = sum(1 for u in users.values() if u.get("lead_score", 0) >= 50)

            await update.message.reply_text(
                f"📊 CRM статистика:\n"
                f"Всего лидов: {total}\n"
                f"Продукт: {product}\n"
                f"Подзаработать: {income}\n"
                f"Основная работа: {career}\n"
                f"Команда: {team}\n"
                f"Горячие лиды: {hot}"
            )
        return

    await update.message.reply_text(
        "Я тебя понял 👍\n\n"
        "Выбери, что тебе сейчас нужно:\n"
        "🚀 Старт\n"
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
            "🔥 Отлично.\n\n"
            "Твоё первое действие:\n"
            "Напиши 10 людям:\n"
            "«Привет! Я сейчас запускаюсь в новом проекте. Можно задам тебе один вопрос?»"
        )
        return

    if query.data == "give_script":
        await query.edit_message_text(
            "📩 Готовый скрипт:\n\n"
            "Привет! Я сейчас запускаюсь в новом проекте. Можно задам тебе один вопрос?"
        )
        return

    if query.data == "written_10":
        user["stage"] = "written_10"
        user["contacts_written"] = 10
        update_score(user)

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔥 Да, был интерес", callback_data="has_interest")],
                [InlineKeyboardButton("😐 Пока без ответа", callback_data="no_reply")],
            ]
        )

        await query.edit_message_text(
            "Супер! Ты уже сделал(а) главное действие 🔥\n\n"
            "Скажи, кто-то проявил интерес?",
            reply_markup=keyboard,
        )
        await send_lead_card(context, user_id)
        return

    if query.data == "has_interest":
        user["stage"] = "hot_lead"
        update_score(user)

        await query.edit_message_text(
            "Отлично! Следующий шаг:\n\n"
            "Напиши человеку:\n"
            "«Супер, тогда я коротко покажу тебе систему / продукт, и ты решишь, интересно тебе это или нет». \n\n"
            "Если нужен текст дожима — напиши: ДОЖИМ"
        )
        await send_lead_card(context, user_id)
        return

    if query.data == "no_reply":
        user["stage"] = "follow_up"
        await query.edit_message_text(
            "Нормально 👍 Это часть процесса.\n\n"
            "Следующий шаг — мягкий дожим:\n"
            "«Привет, возвращаюсь к сообщению выше. Интересно тебе посмотреть короткую систему запуска?»"
        )
        return


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
