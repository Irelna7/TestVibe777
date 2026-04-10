# File: main.py — основной бот FAQ-Telegram-бот (логика Telegram-бота, меню, заявки)

import os
import csv
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackContext,
)

# ========== Загрузка .env ==========
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not TELEGRAM_TOKEN or not ADMIN_CHAT_ID:
    raise ValueError(
        "Ошибка: переменные TELEGRAM_TOKEN и ADMIN_CHAT_ID должны быть заданы в файле .env"
    )

# ========== Константы ==========
# Состояния для ConversationHandler
FAQ_STATE = 1
NAME_STATE = 2
CONTACT_STATE = 3

# Словарь FAQ (ключевое слово -> ответ)
FAQ_DICT = {
    "цена": "Наши услуги стоят от 1000 до 5000 рублей. Точную стоимость уточните у менеджера.",
    "доставка": "Доставка занимает 2-3 дня. Стоимость — 300 рублей.",
    "оплата": "Принимаем карты, СБП и наличные курьеру.",
    "возврат": "Вы можете вернуть товар в течение 14 дней, если он не использован.",
    "график": "Работаем с 10:00 до 20:00 без выходных.",
}

# ========== Вспомогательные функции ==========
def save_lead_to_csv(name: str, contact: str, user_id: int, username: str) -> None:
    """Сохраняет заявку в файл leads.csv (создаёт заголовки, если файла нет)."""
    file_exists = os.path.isfile("leads.csv")
    with open("leads.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["created_at", "name", "contact", "tg_user_id", "tg_username"])
        writer.writerow([
            datetime.now().isoformat(),
            name,
            contact,
            user_id,
            username or "нет username",
        ])

# ========== Главное меню ==========
def get_main_keyboard():
    """Возвращает клавиатуру главного меню."""
    buttons = [
        [KeyboardButton("FAQ")],
        [KeyboardButton("Оставить заявку")],
        [KeyboardButton("Позвать человека")],
        [KeyboardButton("В меню")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ========== Обработчики ==========
async def start(update: Update, context: CallbackContext) -> None:
    """Команда /start — приветствие и показ меню."""
    await update.message.reply_text(
        "👋 Здравствуйте! Я FAQ-бот. Я отвечу на частые вопросы и помогу оставить заявку.\n\n"
        "Используйте кнопки меню:",
        reply_markup=get_main_keyboard(),
    )

async def faq_start(update: Update, context: CallbackContext) -> int:
    """Нажали FAQ — просим ввести ключевое слово."""
    await update.message.reply_text(
        "🔍 Напишите ключевое слово или короткий вопрос.\n"
        "Примеры: цена, доставка, оплата, возврат, график.\n\n"
        "Или нажмите «В меню», чтобы вернуться.",
        reply_markup=get_main_keyboard(),
    )
    return FAQ_STATE

async def faq_handle(update: Update, context: CallbackContext) -> int:
    """Получили ключевое слово — ищем в словаре."""
    keyword = update.message.text.strip().lower()
    answer = FAQ_DICT.get(keyword)

    if answer:
        await update.message.reply_text(f"📌 {answer}", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text(
            "❌ Не нашёл ответа на ваш вопрос.\n"
            "Вы можете оставить заявку, и наш специалист свяжется с вами.\n\n"
            "Нажмите «Оставить заявку» в меню.",
            reply_markup=get_main_keyboard(),
        )
    return ConversationHandler.END

async def application_start(update: Update, context: CallbackContext) -> int:
    """Нажали «Оставить заявку» — спрашиваем имя."""
    await update.message.reply_text(
        "📝 Пожалуйста, введите ваше имя:",
        reply_markup=get_main_keyboard(),
    )
    return NAME_STATE

async def get_name(update: Update, context: CallbackContext) -> int:
    """Получили имя — сохраняем в context.user_data и спрашиваем контакт."""
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Имя не может быть пустым. Введите имя:")
        return NAME_STATE
    context.user_data["lead_name"] = name
    await update.message.reply_text(
        "Теперь введите контакт (телефон, Telegram @username или email):",
        reply_markup=get_main_keyboard(),
    )
    return CONTACT_STATE

async def get_contact(update: Update, context: CallbackContext) -> int:
    """Получили контакт — сохраняем заявку, уведомляем админа и пользователя."""
    contact = update.message.text.strip()
    if not contact:
        await update.message.reply_text("Контакт не может быть пустым. Введите контакт:")
        return CONTACT_STATE

    name = context.user_data["lead_name"]
    user_id = update.effective_user.id
    username = update.effective_user.username

    # Сохраняем в CSV
    save_lead_to_csv(name, contact, user_id, username)

    # Отправляем админу
    admin_message = (
        f"🆕 Новая заявка!\n"
        f"👤 Имя: {name}\n"
        f"📞 Контакт: {contact}\n"
        f"🆔 User ID: {user_id}\n"
        f"👾 Username: @{username}" if username else "нет username"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_message)
    except Exception as e:
        print(f"Не удалось отправить уведомление админу: {e}")

    # Подтверждение пользователю
    await update.message.reply_text(
        "✅ Заявка принята! Наш специалист свяжется с вами в ближайшее время.\n"
        "Вернуться в меню можно по кнопке «В меню».",
        reply_markup=get_main_keyboard(),
    )

    # Очищаем временные данные
    context.user_data.clear()
    return ConversationHandler.END

async def call_human(update: Update, context: CallbackContext) -> None:
    """Обработчик кнопки «Позвать человека»."""
    user = update.effective_user
    username = f"@{user.username}" if user.username else f"ID {user.id}"

    # Ответ пользователю
    await update.message.reply_text(
        "👨‍💼 Ок, передал команде. Скоро с вами свяжется оператор.\n"
        "А пока можете воспользоваться FAQ или оставить заявку.",
        reply_markup=get_main_keyboard(),
    )

    # Уведомление админу
    admin_text = f"🔔 Пользователь {username} попросил позвать человека."
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
    except Exception as e:
        print(f"Не удалось отправить уведомление админу: {e}")

async def back_to_menu(update: Update, context: CallbackContext) -> int:
    """Обработчик кнопки «В меню» — завершает все диалоги и показывает меню."""
    await update.message.reply_text(
        "🏠 Возвращаемся в главное меню.",
        reply_markup=get_main_keyboard(),
    )
    # Если активен какой-либо диалог — завершаем его
    current_state = context.user_data.get("conversation_state")
    if current_state:
        context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    """Завершает разговор (аналог back_to_menu для ConversationHandler)."""
    await update.message.reply_text(
        "Действие отменено. Вы в главном меню.",
        reply_markup=get_main_keyboard(),
    )
    context.user_data.clear()
    return ConversationHandler.END

# ========== Основная функция ==========
def main() -> None:
    """Запуск бота (polling)."""
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # ConversationHandler для FAQ
    faq_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^FAQ$"), faq_start)],
        states={
            FAQ_STATE: [MessageHandler(filters.TEXT & ~filters.Regex("^В меню$"), faq_handle)],
        },
        fallbacks=[MessageHandler(filters.Regex("^В меню$"), back_to_menu)],
    )

    # ConversationHandler для заявки
    application_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Оставить заявку$"), application_start)],
        states={
            NAME_STATE: [MessageHandler(filters.TEXT & ~filters.Regex("^В меню$"), get_name)],
            CONTACT_STATE: [MessageHandler(filters.TEXT & ~filters.Regex("^В меню$"), get_contact)],
        },
        fallbacks=[MessageHandler(filters.Regex("^В меню$"), back_to_menu)],
    )

    # Обработчики команд и кнопок
    app.add_handler(CommandHandler("start", start))
    app.add_handler(faq_conv)
    app.add_handler(application_conv)
    app.add_handler(MessageHandler(filters.Regex("^Позвать человека$"), call_human))
    # Кнопка «В меню» глобально
    app.add_handler(MessageHandler(filters.Regex("^В меню$"), back_to_menu))

    print("Бот запущен и работает (polling)...")
    app.run_polling()

if __name__ == "__main__":
    main()