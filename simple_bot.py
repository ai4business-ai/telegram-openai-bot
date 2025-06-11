import os
import logging
import asyncio
import sqlite3
import json
from typing import Dict, Tuple
from signal import signal, SIGINT, SIGTERM
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from dotenv import load_dotenv
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from openai import OpenAI

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
MINI_APP_URL = "https://ai4business-ai.github.io/front-bot-repo/"
MAX_MESSAGE_LENGTH = 4096
DATABASE_NAME = "users.db"

# Инициализация клиента OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID ассистентов
ASSISTANTS = {
    "market": os.getenv("OPENAI_ASSISTANT_ID_MARKET"),
    "founder": os.getenv("OPENAI_ASSISTANT_ID_FOUNDER"),
    "business": os.getenv("OPENAI_ASSISTANT_ID_BUSINESS"),
    "adapter": os.getenv("OPENAI_ASSISTANT_ID_ADAPTER")
}

ASSISTANT_NAMES = {
    "market": "📊 Анализ рынка",
    "founder": "💡 Идеи фаундера", 
    "business": "📝 Бизнес-модель",
    "adapter": "🔄 Адаптатор идей"
}

# Глобальные переменные
active_threads: Dict[int, Tuple[str, str, str]] = {}
application = None  # Глобальная переменная для экземпляра Application

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server(port=8080):
    """Запуск HTTP сервера для health checks"""
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Health check server running on port {port}")
    server.serve_forever()

def init_database():
    """Инициализация базы данных."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            status TEXT DEFAULT 'user',
            registered_at TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()

def add_or_update_user(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Добавление или обновление пользователя."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.execute('''
        INSERT OR REPLACE INTO users 
        (telegram_id, username, first_name, last_name, last_activity)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (telegram_id, username, first_name, last_name))
        conn.commit()

def get_user_status(telegram_id: int) -> str:
    """Получение статуса пользователя."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.execute('SELECT status FROM users WHERE telegram_id = ?', (telegram_id,))
        result = cursor.fetchone()
        return result[0] if result else 'new'

def register_user(telegram_id: int):
    """Регистрация пользователя."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.execute('''
        UPDATE users 
        SET status = 'registered', registered_at = CURRENT_TIMESTAMP
        WHERE telegram_id = ?
        ''', (telegram_id,))
        conn.commit()

def get_main_keyboard():
    """Клавиатура с кнопкой Mini App."""
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎮 Выбрать ассистента", web_app=WebAppInfo(url=MINI_APP_URL))],
        [KeyboardButton("🛑 Остановить обсуждение")],
        [KeyboardButton("👤 Профиль")]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start."""
    user = update.effective_user
    add_or_update_user(user.id, user.username, user.first_name, user.last_name)
    
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "🤖 Я бот с бизнес-ассистентами на базе ИИ.\n\n"
        "🎮 Используй кнопку ниже, чтобы выбрать ассистента:"
    )
    
    await update.message.reply_text(text, reply_markup=get_main_keyboard())

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка данных из Mini App."""
    try:
        data = json.loads(update.message.web_app_data.data)
        
        if data.get('action') == 'register_user':
            register_user(update.effective_user.id)
            await update.message.reply_text(
                "✅ Регистрация завершена!",
                reply_markup=get_main_keyboard()
            )
        elif data.get('action') == 'select_assistant':
            await start_assistant(
                update, 
                context, 
                data.get('assistant_type')
            )
            
    except Exception as e:
        logger.error(f"WebApp error: {e}")
        await update.message.reply_text(
            "❌ Ошибка обработки запроса",
            reply_markup=get_main_keyboard()
        )

async def start_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE, assistant_type: str):
    """Запуск ассистента."""
    user_id = update.effective_user.id
    
    if user_id in active_threads:
        _, thread_id, _ = active_threads[user_id]
        try:
            client.beta.threads.delete(thread_id)
        except Exception:
            pass
    
    assistant_id = ASSISTANTS.get(assistant_type)
    if not assistant_id:
        await update.message.reply_text(
            "❌ Ассистент недоступен",
            reply_markup=get_main_keyboard()
        )
        return
    
    thread = client.beta.threads.create()
    active_threads[user_id] = (assistant_id, thread.id, assistant_type)
    
    await update.message.reply_text(
        f"✅ Выбран ассистент: {ASSISTANT_NAMES[assistant_type]}\n\n"
        "💬 Теперь можете задавать вопросы",
        reply_markup=get_main_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "🎮 Выбрать ассистента":
        await update.message.reply_text(
            "Откройте Mini App для выбора ассистента:",
            reply_markup=get_main_keyboard()
        )
        return
        
    if text == "🛑 Остановить обсуждение":
        if user_id in active_threads:
            del active_threads[user_id]
            await update.message.reply_text(
                "🗑️ Диалог завершен",
                reply_markup=get_main_keyboard()
            )
        return
    
    if user_id not in active_threads:
        await update.message.reply_text(
            "❌ Сначала выберите ассистента",
            reply_markup=get_main_keyboard()
        )
        return
    
    await process_assistant_response(update, context)

async def process_assistant_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса к ассистенту."""
    user_id = update.effective_user.id
    assistant_id, thread_id, _ = active_threads[user_id]
    
    await context.bot.send_chat_action(user_id, "typing")
    
    try:
        # Добавление сообщения в thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=update.message.text
        )
        
        # Запуск ассистента
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        
        # Ожидание ответа
        response = await wait_for_assistant_response(thread_id, run.id)
        
        # Отправка ответа
        if response:
            await update.message.reply_text(
                response[:MAX_MESSAGE_LENGTH],
                reply_markup=get_main_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Assistant error: {e}")
        await update.message.reply_text(
            "❌ Ошибка обработки запроса",
            reply_markup=get_main_keyboard()
        )

async def wait_for_assistant_response(thread_id: str, run_id: str) -> str:
    """Ожидание ответа ассистента."""
    for _ in range(30):  # 30 попыток с интервалом 1 сек
        await asyncio.sleep(1)
        
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id)
            for msg in messages.data:
                if msg.role == "assistant":
                    return msg.content[0].text.value
        
        if run.status in ["failed", "cancelled"]:
            return "❌ Ошибка обработки запроса"
    
    return "⏳ Ответ занимает больше времени, чем ожидалось"

def shutdown_handler(signum, frame):
    """Обработчик сигналов завершения работы."""
    logger.info("Получен сигнал завершения...")
    if application:
        application.stop()
    exit(0)

def main():
    """Основная функция запуска бота."""
    global application
    
    # Инициализация БД
    init_database()
    
    # Проверка токена
    if not (token := os.getenv("TELEGRAM_BOT_TOKEN")):
        logger.error("Токен бота не найден!")
        return
    
    # Запуск health check сервера в отдельном потоке
    port = int(os.getenv("PORT", 8080))
    health_thread = Thread(target=run_health_server, args=(port,), daemon=True)
    health_thread.start()
    
    # Создание приложения Telegram бота
    application = Application.builder().token(token).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    # Регистрация обработчиков сигналов
    signal(SIGINT, shutdown_handler)
    signal(SIGTERM, shutdown_handler)
    
    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
