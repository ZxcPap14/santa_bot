import json
import random
from pathlib import Path
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----- База -----
DB_FILE = Path("participants.json")

def load_db():
    if DB_FILE.exists():
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

participants = load_db()

# ----- Меню -----
def user_menu():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🎄 Участвовать")]],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🎁 Распределить")],
            [KeyboardButton("📜 Список участников")],
            [KeyboardButton("🗑 Очистить список")],
            [KeyboardButton("❌ Удалить участника")]
        ],
        resize_keyboard=True
    )

# ----- START -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = context.bot_data.get("admin_id")
    user = update.effective_user

    if user.id == admin_id:
        await update.message.reply_text(
            "Админ панель:", reply_markup=admin_menu()
        )
    else:
        await update.message.reply_text(
            "Добро пожаловать в Тайного Санту! 🎅\n"
            "Нажми кнопку ниже, чтобы участвовать.",
            reply_markup=user_menu()
        )

# ----- Участвовать -----
async def participate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    participants[str(user.id)] = user.username or user.full_name
    save_db(participants)

    await update.message.reply_text(
        "🎉 Ты зарегистрирован! Жди распределения."
    )

# ----- Удалить 1 участника (админ) -----
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def delete_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = context.bot_data.get("admin_id")
    user = update.effective_user

    if user.id != admin_id:
        return await update.message.reply_text("❌ У вас нет прав.")

    if not participants:
        return await update.message.reply_text("Список пуст — удалять некого.")

    keyboard = []
    for user_id, name in participants.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"del:{user_id}")])

    await update.message.reply_text(
        "Выберите участника для удаления:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
async def delete_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if not data.startswith("del:"):
        return

    user_id = data.split(":")[1]

    # Удаляем
    if user_id in participants:
        deleted_name = participants[user_id]
        del participants[user_id]
        save_db(participants)

        await query.edit_message_text(
            f"❌ Участник <b>{deleted_name}</b> удалён.",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text("❗ Пользователь уже удалён.")


# ----- Очистка участников (админ) -----
async def clear_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = context.bot_data.get("admin_id")
    user = update.effective_user

    if user.id != admin_id:
        return await update.message.reply_text("❌ У вас нет прав.")

    # очищаем память
    participants.clear()

    # очищаем файл
    save_db(participants)

    await update.message.reply_text("🗑 Список участников успешно очищен!")

# ----- Список участников (админ) -----
import html

async def show_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = context.bot_data.get("admin_id")
    user = update.effective_user

    if user.id != admin_id:
        return await update.message.reply_text("❌ У вас нет прав.")

    if not participants:
        return await update.message.reply_text("Пока никого нет.")

    text = "📜 <b>Список участников:</b>\n\n"
    for i, (user_id, name) in enumerate(participants.items(), start=1):
        safe_name = html.escape(name)  # ← ЭКРАНИРУЕМ ИМЯ
        text += f"{i}. {safe_name}\n"

    await update.message.reply_text(text, parse_mode="HTML")

# ----- Распределить -----
async def distribute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = context.bot_data.get("admin_id")
    user = update.effective_user

    if user.id != admin_id:
        return await update.message.reply_text("❌ У вас нет прав.")

    if len(participants) < 2:
        return await update.message.reply_text("Нужны минимум 2 участника!")

    ids = list(participants.keys())
    receivers = ids.copy()
    random.shuffle(receivers)

    # чтобы никто не получил себя
    for i in range(len(ids)):
        if ids[i] == receivers[i]:
            random.shuffle(receivers)
            return await distribute(update, context)

    await update.message.reply_text("🎁 Рассылаю результаты...")

    for giver_id, receiver_id in zip(ids, receivers):
        giver_id = int(giver_id)
        receiver_name = participants[receiver_id]

        try:
            await context.bot.send_message(
                chat_id=giver_id,
                text=f"🎄 Ты даришь подарок: @*{receiver_name}* 🎁",
                parse_mode="Markdown"
            )
        except:
            await update.message.reply_text(
                f"⚠ Не могу написать участнику {participants[str(giver_id)]}. "
                "Он не начал диалог с ботом."
            )

    await update.message.reply_text("Готово! 🎉 Все получили свои пары!")

# ----- MAIN -----
def main():
    TOKEN = "8469655156:AAFkddq21nGYD92dOhhdWQEhwrk7QgYBvuc"
    ADMIN_ID = 7302033371  # <-- ВСТАВЬ СЮДА СВОЙ TELEGRAM ID !!!

    app = ApplicationBuilder().token(TOKEN).build()
    app.bot_data["admin_id"] = ADMIN_ID

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^🎄 Участвовать$"), participate))
    app.add_handler(MessageHandler(filters.Regex("^📜 Список участников$"), show_list))
    app.add_handler(MessageHandler(filters.Regex("^🎁 Распределить$"), distribute))
    app.add_handler(MessageHandler(filters.Regex("^❌ Удалить участника$"), delete_user_menu))
    app.add_handler(MessageHandler(filters.Regex("^🗑 Очистить список$"), clear_list))

    # ВАЖНО: callback handler
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(delete_user_callback))

    app.run_polling()

if __name__ == "__main__":
    main()
