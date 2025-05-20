import os
import logging
import asyncio
from typing import Dict, Any

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from openai import OpenAI

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Хранение активных разговоров
active_threads: Dict[int, str] = {}

# Получение ID ассистента
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
if not ASSISTANT_ID:
    # Создание ассистента, если ID не указан
    assistant = client.beta.assistants.create(
        name="Telegram Bot Assistant",
        instructions="Вы — полезный ассистент, который предоставляет информацию и помощь через Telegram бота.",
        model="gpt-4-turbo",  # Можете изменить на нужную модель
    )
    ASSISTANT_ID = assistant.id
    logger.info(f"Создан новый ассистент с ID: {ASSISTANT_ID}")
else:
    logger.info(f"Используется существующий ассистент с ID: {ASSISTANT_ID}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка приветственного сообщения по команде /start."""
    await update.message.reply_text(
        "👋 Привет! Я ваш AI ассистент. Используйте /chat чтобы начать разговор со мной."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка справочного сообщения по команде /help."""
    help_text = (
        "Вот команды, которые вы можете использовать:\n\n"
        "/start - Запустить бота\n"
        "/help - Показать это справочное сообщение\n"
        "/chat - Начать разговор с AI ассистентом\n"
        "/end - Завершить текущий разговор\n"
    )
    await update.message.reply_text(help_text)

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало нового разговора с ассистентом."""
    user_id = update.effective_user.id
    
    # Завершение существующего чата, если есть
    if user_id in active_threads:
        # Удаление предыдущего потока
        try:
            client.beta.threads.delete(active_threads[user_id])
        except Exception as e:
            logger.error(f"Ошибка при удалении потока: {e}")
    
    # Создание нового потока
    thread = client.beta.threads.create()
    active_threads[user_id] = thread.id
    
    await update.message.reply_text(
        "🤖 Я готов! Отправьте мне сообщение, и я отвечу. Используйте /end когда закончите."
    )
    
    logger.info(f"Начат новый чат для пользователя {user_id} с потоком {thread.id}")

async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завершение текущего разговора с ассистентом."""
    user_id = update.effective_user.id
    
    if user_id in active_threads:
        thread_id = active_threads[user_id]
        
        # Удаление потока
        try:
            client.beta.threads.delete(thread_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении потока: {e}")
        
        # Удаление из активных разговоров
        del active_threads[user_id]
        
        await update.message.reply_text(
            "👋 Чат завершен. Используйте /chat чтобы начать новый разговор в любое время!"
        )
        logger.info(f"Завершен чат для пользователя {user_id}")
    else:
        await update.message.reply_text(
            "У вас нет активного разговора. Используйте /chat чтобы начать."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка входящих сообщений от пользователя."""
    user_id = update.effective_user.id
    
    # Проверка наличия активного разговора
    if user_id not in active_threads:
        keyboard = [
            [InlineKeyboardButton("Начать чат", callback_data="start_chat")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "У вас нет активного разговора. Хотите начать?",
            reply_markup=reply_markup
        )
        return
    
    # Получение сообщения пользователя
    user_message = update.message.text
    thread_id = active_threads[user_id]
    
    # Отправка действия "набирает текст"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Добавление сообщения пользователя в поток
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )
        
        # Запуск ассистента в потоке
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
        )
        
        # Ожидание ответа
        response = await poll_run(thread_id, run.id)
        
        # Отправка ответа ассистента
        if response:
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("Не удалось сформировать ответ. Пожалуйста, попробуйте снова.")
            
    except Exception as e:
        logger.error(f"Ошибка в разговоре: {e}")
        await update.message.reply_text(
            "Извините, возникла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз или начните новый разговор с /chat."
        )

async def poll_run(thread_id: str, run_id: str) -> str:
    """Ожидание завершения выполнения и возврат ответа ассистента."""
    max_attempts = 60  # Максимальное количество попыток опроса
    for _ in range(max_attempts):
        await asyncio.sleep(1)  # Ожидание 1 секунду между опросами
        
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        
        if run.status == "completed":
            # Получение сообщений из потока
            messages = client.beta.threads.messages.list(
                thread_id=thread_id
            )
            
            # Получение последнего сообщения ассистента
            for message in messages.data:
                if message.role == "assistant":
                    content = ""
                    for content_part in message.content:
                        if content_part.type == "text":
                            content += content_part.text.value
                    
                    return content
            
            return "Нет ответа от ассистента."
        
        if run.status in ["failed", "cancelled", "expired"]:
            logger.error(f"Выполнение завершилось со статусом: {run.status}")
            return "Извините, я не смог выполнить запрос."
    
    # Если превышено максимальное количество попыток
    return "Ответ занимает слишком много времени. Пожалуйста, попробуйте позже."

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатий на кнопки."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "start_chat":
        # Вызов функции start_chat
        await query.edit_message_text(text="Начинаю новый чат...")
        await start_chat(update, context)

def main() -> None:
    """Запуск бота."""
    # Получение токена Telegram из переменной окружения
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Переменная окружения TELEGRAM_BOT_TOKEN не установлена!")
        return
    
    # Создание приложения
    application = Application.builder().token(token).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("chat", start_chat))
    application.add_handler(CommandHandler("end", end_chat))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
