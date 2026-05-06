
import json
import os
import asyncio
import logging
from datetime import datetime, timedelta

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


TOKEN = "8426948357:AAF4mFDDvvp0_xyds5V5dsJ-3_yehZ8Na64"
DATA_FILE = "reminders.json"


keyboard = [
    ["📋 Команды"],
    ["➕ Добавить", "🔔 Мои напоминания"]
]

markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= ХРАНЕНИЕ =================

def load_reminders():
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        reminders = json.load(f)

    
    for i, r in enumerate(reminders):
        if "id" not in r:
            r["id"] = i + 1

    return reminders


def save_reminders(reminders):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)

# ================= КОМАНДЫ =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот напоминаний", reply_markup=markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/add 2026-01-20 18:30 текст\n"
        "/add 10m текст\n"
        "/list\n"
        "/delete ID"
    )



async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) < 2:
        await update.message.reply_text("❌ Неверный формат")
        return

    reminders = load_reminders()
    reminder_id = max([r.get("id", 0) for r in reminders], default=0) + 1

    if context.args[0].endswith("m"):

        minutes = int(context.args[0][:-1])
        remind_at = datetime.now() + timedelta(minutes=minutes)
        text = " ".join(context.args[1:])

    else:

        if len(context.args) < 3:
            await update.message.reply_text("❌ Неверный формат")
            return

        try:
            remind_at = datetime.strptime(
                f"{context.args[0]} {context.args[1]}",
                "%Y-%m-%d %H:%M"
            )
        except:
            await update.message.reply_text("❌ Ошибка даты")
            return

        text = " ".join(context.args[2:])

    reminders.append({
        "id": reminder_id,
        "chat_id": update.effective_chat.id,
        "text": text,
        "time": remind_at.isoformat(),
        "sent": False
    })

    save_reminders(reminders)

    await update.message.reply_text(f"✅ Добавлено (ID {reminder_id})")



async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):

    reminders = load_reminders()
    chat_id = update.effective_chat.id

    user = [r for r in reminders if r["chat_id"] == chat_id and not r["sent"]]

    if not user:
        await update.message.reply_text("📭 Нет напоминаний")
        return

    text = "🔔 Напоминания:\n\n"

    for r in user:
        time = datetime.fromisoformat(r["time"]).strftime("%Y-%m-%d %H:%M")
        text += f"ID {r['id']} | {time}\n{r['text']}\n\n"

    await update.message.reply_text(text)



async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("/delete ID")
        return

    rid = int(context.args[0])

    reminders = load_reminders()
    chat_id = update.effective_chat.id

    new = []
    deleted = False

    for r in reminders:
        if r["id"] == rid and r["chat_id"] == chat_id:
            deleted = True
            continue
        new.append(r)

    if not deleted:
        await update.message.reply_text("❌ Не найдено")
        return

    save_reminders(new)
    await update.message.reply_text("🗑 Удалено")

# ================= КНОПКИ =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.text == "📋 Команды":
        await help_command(update, context)

    elif update.message.text == "🔔 Мои напоминания":
        await list_reminders(update, context)

    elif update.message.text == "➕ Добавить":
        await update.message.reply_text("/add 2026-01-20 18:30 текст")

# ================= НАПОМИНАНИЯ =================

async def reminder_job(context: ContextTypes.DEFAULT_TYPE):

    reminders = load_reminders()
    now = datetime.now()
    changed = False

    for r in reminders:
        if not r["sent"]:
            t = datetime.fromisoformat(r["time"])

            if t <= now:
                await context.bot.send_message(
                    chat_id=r["chat_id"],
                    text=f"⏰ {r['text']}"
                )
                r["sent"] = True
                changed = True

    if changed:
        save_reminders(reminders)

# ================= ЗАПУСК =================

def main():

    logging.basicConfig(level=logging.INFO)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_reminders))
    app.add_handler(CommandHandler("delete", delete))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, buttons))

    
    app.job_queue.run_repeating(reminder_job, interval=30, first=10)

    print("🤖 Бот запущен")

    app.run_polling()


if __name__ == "__main__":
    main()

