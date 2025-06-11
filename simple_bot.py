import os
import logging
import asyncio
import textwrap
import json
import sqlite3
import hashlib
import hmac
from typing import Dict, Any, Tuple, Optional
from threading import Thread
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime
from typing import Dict, Tuple
from signal import signal, SIGINT, SIGTERM

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, InlineQueryHandler
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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Максимальная длина сообщения Telegram
MAX_MESSAGE_LENGTH = 4096

# URL Mini App для выбора ассистента
# Константы
MINI_APP_URL = "https://ai4business-ai.github.io/front-bot-repo/"
MAX_MESSAGE_LENGTH = 4096
DATABASE_NAME = "users.db"

# Хранение активных разговоров: user_id -> (assistant_id, thread_id, assistant_type)
active_threads: Dict[int, Tuple[str, str, str]] = {}
# Инициализация клиента OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ID ассистентов из переменных окружения
# ID ассистентов
ASSISTANTS = {
    "market": os.getenv("OPENAI_ASSISTANT_ID_MARKET"),
    "founder": os.getenv("OPENAI_ASSISTANT_ID_FOUNDER"),
    "business": os.getenv("OPENAI_ASSISTANT_ID_BUSINESS"),
    "adapter": os.getenv("OPENAI_ASSISTANT_ID_ADAPTER")
}

# Названия ассистентов
ASSISTANT_NAMES = {
    "market": "📊 Анализ рынка",
    "founder": "💡 Идеи фаундера",
    "business": "📝 Бизнес-модель",
    "adapter": "🔄 Адаптатор идей"
}

# Описания ассистентов
ASSISTANT_DESCRIPTIONS = {
    "market": "Помогает проанализировать рынок, конкурентов и найти ниши для развития",
    "founder": "Помогает обсудить и проработать идеи основателя бизнеса",
    "business": "Помогает составить и проанализировать бизнес-модель",
    "adapter": "Помогает адаптировать успешные идеи из различных кейсов для вашего бизнеса"
}
# Глобальные переменные
active_threads: Dict[int, Tuple[str, str, str]] = {}
application = None  # Глобальная переменная для экземпляра Application

# Инициализация базы данных
def init_database():
    """Инициализация базы данных пользователей."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        status TEXT DEFAULT 'user',
        registered_at TIMESTAMP,
        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def add_or_update_user(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None, status: str = 'user'):
    """Добавляет или обновляет пользователя в базе данных."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Проверяем, существует ли пользователь
    cursor.execute('SELECT status FROM users WHERE telegram_id = ?', (telegram_id,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        # Обновляем существующего пользователя
        cursor.execute('''
        UPDATE users 
        SET username = ?, first_name = ?, last_name = ?, last_activity = CURRENT_TIMESTAMP
        WHERE telegram_id = ?
        ''', (username, first_name, last_name, telegram_id))
    else:
        # Добавляем нового пользователя
        cursor.execute('''
        INSERT INTO users (telegram_id, username, first_name, last_name, status)
        VALUES (?, ?, ?, ?, ?)
        ''', (telegram_id, username, first_name, last_name, status))
    
    conn.commit()
    conn.close()

def register_user(telegram_id: int):
    """Регистрирует пользователя (меняет статус на 'registered')."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    UPDATE users 
    SET status = 'registered', registered_at = CURRENT_TIMESTAMP
    WHERE telegram_id = ?
    ''', (telegram_id,))
    
    conn.commit()
    conn.close()
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
    """Получает статус пользователя."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT status FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    return result[0] if result else 'new'
    """Получение статуса пользователя."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.execute('SELECT status FROM users WHERE telegram_id = ?', (telegram_id,))
        result = cursor.fetchone()
        return result[0] if result else 'new'

def validate_telegram_data(init_data: str, bot_token: str) -> Optional[dict]:
    """Валидирует данные, полученные от Telegram WebApp."""
    try:
        # Парсим данные
        parsed_data = {}
        for item in init_data.split('&'):
            key, value = item.split('=', 1)
            parsed_data[key] = value
        
        # Извлекаем hash
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            return None
        
        # Создаем строку для проверки
        data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted(parsed_data.items())])
        
        # Создаем secret key
        secret_key = hmac.new(
            'WebAppData'.encode(),
            bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        # Вычисляем hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Проверяем hash
        if calculated_hash == received_hash:
            # Парсим данные пользователя
            if 'user' in parsed_data:
                user_data = json.loads(parsed_data['user'])
                return user_data
        
        return None
    except Exception as e:
        logger.error(f"Ошибка валидации данных Telegram: {e}")
        return None
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
    """Создание основной клавиатуры с кнопками управления."""
    keyboard = [
    """Клавиатура с кнопкой Mini App."""
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎮 Выбрать ассистента", web_app=WebAppInfo(url=MINI_APP_URL))],
        [KeyboardButton("🛑 Остановить обсуждение")],
        [KeyboardButton("👤 Профиль")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_assistant_selection_keyboard():
    """Создание inline клавиатуры для выбора ассистента."""
    keyboard = []
    for assistant_type, name in ASSISTANT_NAMES.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"select_{assistant_type}")])
    
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка приветственного сообщения по команде /start."""
    user = update.effective_user
    
    # Добавляем пользователя в базу данных
    add_or_update_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    user_status = get_user_status(user.id)
    
    if user_status == 'registered':
        help_text = (
            f"👋 Привет, {user.first_name}! Добро пожаловать обратно!\n\n"
            "🤖 Я бот с бизнес-ассистентами на базе ИИ.\n\n"
            "🎮 **Как использовать:**\n"
            "1. Нажмите кнопку \"Выбрать ассистента\" ниже\n"
            "2. В открывшемся приложении выберите нужного ассистента\n"
            "3. Начните общение с выбранным ассистентом\n\n"
            "📱 **Доступные ассистенты:**\n"
            f"• {ASSISTANT_NAMES['market']} - {ASSISTANT_DESCRIPTIONS['market']}\n"
            f"• {ASSISTANT_NAMES['founder']} - {ASSISTANT_DESCRIPTIONS['founder']}\n"
            f"• {ASSISTANT_NAMES['business']} - {ASSISTANT_DESCRIPTIONS['business']}\n"
            f"• {ASSISTANT_NAMES['adapter']} - {ASSISTANT_DESCRIPTIONS['adapter']}\n\n"
            "🛑 Используйте кнопку \"Остановить обсуждение\" для завершения разговора\n"
            "❓ Используйте /help для справки"
        )
    else:
        help_text = (
            f"👋 Привет, {user.first_name}! Добро пожаловать!\n\n"
            "🤖 Я бот с бизнес-ассистентами на базе ИИ.\n\n"
            "📋 **Для начала работы:**\n"
            "1. Нажмите кнопку \"Выбрать ассистента\" ниже\n"
            "2. Пройдите быструю регистрацию в приложении\n"
            "3. Выберите нужного ассистента\n"
            "4. Начните общение!\n\n"
            "📱 **Доступные ассистенты:**\n"
            f"• {ASSISTANT_NAMES['market']} - {ASSISTANT_DESCRIPTIONS['market']}\n"
            f"• {ASSISTANT_NAMES['founder']} - {ASSISTANT_DESCRIPTIONS['founder']}\n"
            f"• {ASSISTANT_NAMES['business']} - {ASSISTANT_DESCRIPTIONS['business']}\n"
            f"• {ASSISTANT_NAMES['adapter']} - {ASSISTANT_DESCRIPTIONS['adapter']}\n\n"
            "❓ Используйте /help для справки"
        )
    
    await update.message.reply_text(help_text, reply_markup=get_main_keyboard())
    ], resize_keyboard=True)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать профиль пользователя."""
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start."""
    user = update.effective_user
    user_status = get_user_status(user.id)
    add_or_update_user(user.id, user.username, user.first_name, user.last_name)

    # Получаем дополнительную информацию о пользователе
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT username, first_name, last_name, status, registered_at, created_at 
    FROM users WHERE telegram_id = ?
    ''', (user.id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        username, first_name, last_name, status, registered_at, created_at = user_data
        
        profile_text = f"👤 **Ваш профиль**\n\n"
        profile_text += f"🆔 **ID:** {user.id}\n"
        
        if first_name:
            profile_text += f"👤 **Имя:** {first_name}"
            if last_name:
                profile_text += f" {last_name}"
            profile_text += "\n"
        
        if username:
            profile_text += f"📱 **Username:** @{username}\n"
        
        status_emoji = "✅" if status == "registered" else "❌"
        status_text = "Зарегистрирован" if status == "registered" else "Не зарегистрирован"
        profile_text += f"{status_emoji} **Статус:** {status_text}\n"
        
        if registered_at:
            profile_text += f"📅 **Дата регистрации:** {registered_at[:19]}\n"
        
        profile_text += f"📅 **Первое посещение:** {created_at[:19]}\n\n"
        
        if status != "registered":
            profile_text += "💡 **Совет:** Пройдите регистрацию для доступа к ассистентам!"
        
    else:
        profile_text = "❌ Информация о профиле недоступна."
    
    await update.message.reply_text(profile_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка справочного сообщения по команде /help."""
    help_text = (
        "📋 **Справка по использованию бота**\n\n"
        "🎮 **Основной способ использования:**\n"
        "Нажмите кнопку \"Выбрать ассистента\" для выбора нужного ассистента\n\n"
        "📱 **Доступные ассистенты:**\n"
        f"• {ASSISTANT_NAMES['market']} - {ASSISTANT_DESCRIPTIONS['market']}\n"
        f"• {ASSISTANT_NAMES['founder']} - {ASSISTANT_DESCRIPTIONS['founder']}\n"
        f"• {ASSISTANT_NAMES['business']} - {ASSISTANT_DESCRIPTIONS['business']}\n"
        f"• {ASSISTANT_NAMES['adapter']} - {ASSISTANT_DESCRIPTIONS['adapter']}\n\n"
        "⚙️ **Команды:**\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/status - Узнать, какой ассистент активен\n\n"
        "🔘 **Кнопки управления:**\n"
        "🎮 Выбрать ассистента - открыть приложение выбора\n"
        "🛑 Остановить обсуждение - завершить текущий разговор\n"
        "👤 Профиль - информация о вашем аккаунте\n\n"
        "💡 **Совет:** После выбора ассистента просто пишите свои вопросы, и он ответит!"
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "🤖 Я бот с бизнес-ассистентами на базе ИИ.\n\n"
        "🎮 Используй кнопку ниже, чтобы выбрать ассистента:"
    )

    await update.message.reply_text(help_text, reply_markup=get_main_keyboard())

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать статус текущего активного ассистента."""
    user_id = update.effective_user.id
    
    if user_id in active_threads:
        _, _, assistant_type = active_threads[user_id]
        assistant_name = ASSISTANT_NAMES[assistant_type]
        await update.message.reply_text(
            f"🤖 **Активный ассистент:** {assistant_name}\n\n"
            f"📝 **Описание:** {ASSISTANT_DESCRIPTIONS[assistant_type]}\n\n"
            "💬 Можете продолжать задавать вопросы или выбрать другого ассистента.",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ У вас нет активного разговора с ассистентом.\n\n"
            "🎮 Нажмите кнопку \"Выбрать ассистента\" для начала.",
            reply_markup=get_main_keyboard()
        )
    await update.message.reply_text(text, reply_markup=get_main_keyboard())

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка данных из Mini App."""
    try:
        # Получаем данные из Mini App
        web_app_data = update.message.web_app_data.data
        data = json.loads(web_app_data)
        
        logger.info(f"Получены данные из Web App: {data}")
        
        # Проверяем тип действия
        action = data.get('action')
        data = json.loads(update.message.web_app_data.data)

        if action == 'register_user':
            # Обработка регистрации пользователя
            user_id = update.effective_user.id
            register_user(user_id)
            
        if data.get('action') == 'register_user':
            register_user(update.effective_user.id)
            await update.message.reply_text(
                "✅ **Регистрация завершена!**\n\n"
                "🎉 Теперь вы можете пользоваться всеми функциями бота!\n"
                "🎮 Выберите ассистента для начала общения.",
                parse_mode='Markdown',
                "✅ Регистрация завершена!",
                reply_markup=get_main_keyboard()
            )
            
        elif action == 'show_specific_assistant':
            # Обработка выбора ассистента
            selected_assistant = data.get('selected_assistant')
            
            # Проверяем статус регистрации
            user_status = get_user_status(update.effective_user.id)
            if user_status != 'registered':
                await update.message.reply_text(
                    "❌ **Необходима регистрация**\n\n"
                    "Для использования ассистентов необходимо пройти регистрацию.\n"
                    "Нажмите кнопку \"Выбрать ассистента\" и пройдите быструю регистрацию.",
                    parse_mode='Markdown',
                    reply_markup=get_main_keyboard()
                )
                return
            
            if selected_assistant and selected_assistant in ASSISTANTS:
                await start_chat_with_assistant_direct(update, context, selected_assistant)
            else:
                await send_general_assistant_selection_message(update, context)
        else:
            # Неизвестное действие
            await send_general_assistant_selection_message(update, context)
        elif data.get('action') == 'select_assistant':
            await start_assistant(
                update, 
                context, 
                data.get('assistant_type')
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке данных Web App: {e}")
        await send_general_assistant_selection_message(update, context)

async def start_chat_with_assistant_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, assistant_type: str) -> None:
    """Прямой запуск ассистента без промежуточного меню (для keyboard button)."""
    user_id = update.effective_user.id
    
    # Проверяем статус регистрации
    user_status = get_user_status(user_id)
    if user_status != 'registered':
        logger.error(f"WebApp error: {e}")
        await update.message.reply_text(
            "❌ **Необходима регистрация**\n\n"
            "Для использования ассистентов необходимо пройти регистрацию.\n"
            "Нажмите кнопку \"Выбрать ассистента\" и пройдите быструю регистрацию.",
            parse_mode='Markdown',
            "❌ Ошибка обработки запроса",
            reply_markup=get_main_keyboard()
        )
        return

async def start_assistant(update: Update, context: ContextTypes.DEFAULT_TYPE, assistant_type: str):
    """Запуск ассистента."""
    user_id = update.effective_user.id

    # Завершение существующего чата, если есть
    if user_id in active_threads:
        _, thread_id, _ = active_threads[user_id]
        try:
            _, thread_id, _ = active_threads[user_id]
            client.beta.threads.delete(thread_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении потока: {e}")
        except Exception:
            pass

    assistant_id = ASSISTANTS.get(assistant_type)
    
    if not assistant_id:
        await update.message.reply_text(
            f"❌ Извините, ассистент '{ASSISTANT_NAMES[assistant_type]}' недоступен в данный момент.",
            "❌ Ассистент недоступен",
            reply_markup=get_main_keyboard()
        )
        return

    # Создание нового потока
    thread = client.beta.threads.create()
    active_threads[user_id] = (assistant_id, thread.id, assistant_type)

    await update.message.reply_text(
        f"✅ *Запущен ассистент: {ASSISTANT_NAMES[assistant_type].replace('📊 ', '').replace('💡 ', '').replace('📝 ', '').replace('🔄 ', '')}*\n\n"
        f"📝 {ASSISTANT_DESCRIPTIONS[assistant_type]}\n\n"
        "💬 Теперь можете отправлять мне свои вопросы, и я отвечу!\n\n"
        "🔄 Используйте кнопку \"Выбрать ассистента\" для смены ассистента\n"
        "🛑 Используйте кнопку \"Остановить обсуждение\" для завершения",
        parse_mode='Markdown',
        f"✅ Выбран ассистент: {ASSISTANT_NAMES[assistant_type]}\n\n"
        "💬 Теперь можете задавать вопросы",
        reply_markup=get_main_keyboard()
    )
    
    logger.info(f"Прямой запуск ассистента для пользователя {user_id} с ассистентом '{ASSISTANT_NAMES[assistant_type]}' (ID: {assistant_id}) в потоке {thread.id}")

async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка inline запросов для поддержки menu button."""
    query = update.inline_query.query
    
    # Проверяем, является ли это запросом от Mini App
    if query.startswith("assistant_selected_"):
        assistant_type = query.replace("assistant_selected_", "")
        
        if assistant_type in ASSISTANTS:
            # Создаем результат для inline запроса
            results = [
                InlineQueryResultArticle(
                    id=f"select_{assistant_type}",
                    title=f"Выбрать {ASSISTANT_NAMES[assistant_type]}",
                    description=ASSISTANT_DESCRIPTIONS[assistant_type],
                    input_message_content=InputTextMessageContent(
                        message_text=f"🤖 Выбран ассистент: *{ASSISTANT_NAMES[assistant_type].replace('📊 ', '').replace('💡 ', '').replace('📝 ', '').replace('🔄 ', '')}*\n\n"
                                   f"📝 {ASSISTANT_DESCRIPTIONS[assistant_type]}\n\n"
                                   "💬 Нажмите кнопку ниже для начала общения:",
                        parse_mode='Markdown'
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            f"🚀 Запустить {ASSISTANT_NAMES[assistant_type].replace('📊 ', '').replace('💡 ', '').replace('📝 ', '').replace('🔄 ', '')}",
                            callback_data=f"select_{assistant_type}"
                        )
                    ]])
                )
            ]
            
            await update.inline_query.answer(results, cache_time=1)
        else:
            await update.inline_query.answer([])
    else:
        await update.inline_query.answer([])

async def send_specific_assistant_message(update: Update, context: ContextTypes.DEFAULT_TYPE, assistant_type: str) -> None:
    """Отправка сообщения для конкретного ассистента."""
    assistant_name = ASSISTANT_NAMES[assistant_type]
    assistant_description = ASSISTANT_DESCRIPTIONS[assistant_type]
    
    emoji_map = {
        'market': '📊',
        'founder': '💡', 
        'business': '📝',
        'adapter': '🔄'
    }
    
    message_text = (
        f"{emoji_map[assistant_type]} **{assistant_name.replace('📊 ', '').replace('💡 ', '').replace('📝 ', '').replace('🔄 ', '')}**\n\n"
        f"📝 {assistant_description}\n\n"
        f"💬 Нажмите кнопку ниже, чтобы начать общение с этим ассистентом:"
    )
    
    keyboard = [[InlineKeyboardButton(f"🚀 Запустить {assistant_name.replace('📊 ', '').replace('💡 ', '').replace('📝 ', '').replace('🔄 ', '')}", callback_data=f"select_{assistant_type}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def send_general_assistant_selection_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка общего сообщения с выбором ассистента (fallback)."""
    user_status = get_user_status(update.effective_user.id)
    
    if user_status != 'registered':
        message_text = (
            "🔐 **Требуется регистрация**\n\n"
            "Для использования ассистентов необходимо пройти быструю регистрацию.\n\n"
            "🎮 Нажмите кнопку \"Выбрать ассистента\" ниже и следуйте инструкциям в приложении."
        )
        await update.message.reply_text(
            message_text,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    message_text = (
        "🤖 **Выберите ассистента для начала общения:**\n\n"
        f"📊 **Анализ рынка** - {ASSISTANT_DESCRIPTIONS['market']}\n\n"
        f"💡 **Идеи фаундера** - {ASSISTANT_DESCRIPTIONS['founder']}\n\n"
        f"📝 **Бизнес-модель** - {ASSISTANT_DESCRIPTIONS['business']}\n\n"
        f"🔄 **Адаптатор идей** - {ASSISTANT_DESCRIPTIONS['adapter']}\n\n"
        "👇 Нажмите на кнопку ниже для выбора:"
    )
    
    await update.message.reply_text(
        message_text,
        reply_markup=get_assistant_selection_keyboard(),
        parse_mode='Markdown'
    )

async def start_chat_with_type(update: Update, context: ContextTypes.DEFAULT_TYPE, assistant_type: str) -> None:
    """Начало нового разговора с ассистентом указанного типа."""
    user_id = update.effective_user.id
    
    # Проверяем статус регистрации
    user_status = get_user_status(user_id)
    if user_status != 'registered':
        await update.callback_query.edit_message_text(
            "❌ **Необходима регистрация**\n\n"
            "Для использования ассистентов необходимо пройти регистрацию.\n"
            "Нажмите кнопку \"Выбрать ассистента\" в главном меню.",
            parse_mode='Markdown'
        )
        return
    
    # Завершение существующего чата, если есть
    if user_id in active_threads:
        try:
            _, thread_id, _ = active_threads[user_id]
            client.beta.threads.delete(thread_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении потока: {e}")
    
    assistant_id = ASSISTANTS.get(assistant_type)
    
    if not assistant_id:
        await update.callback_query.edit_message_text(
            f"❌ Извините, ассистент '{ASSISTANT_NAMES[assistant_type]}' недоступен в данный момент.",
            reply_markup=get_assistant_selection_keyboard()
        )
        return
    
    # Создание нового потока
    thread = client.beta.threads.create()
    active_threads[user_id] = (assistant_id, thread.id, assistant_type)
    
    await update.callback_query.edit_message_text(
        f"✅ *Запущен ассистент: {ASSISTANT_NAMES[assistant_type].replace('📊 ', '').replace('💡 ', '').replace('📝 ', '').replace('🔄 ', '')}*\n\n"
        f"📝 {ASSISTANT_DESCRIPTIONS[assistant_type]}\n\n"
        "💬 Теперь можете отправлять мне свои вопросы, и я отвечу!\n\n"
        "🔄 Используйте кнопку \"Выбрать ассистента\" для смены ассистента\n"
        "🛑 Используйте кнопку \"Остановить обсуждение\" для завершения",
        parse_mode='Markdown'
    )
    
    logger.info(f"Начат новый чат для пользователя {user_id} с ассистентом '{ASSISTANT_NAMES[assistant_type]}' (ID: {assistant_id}) в потоке {thread.id}")

async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завершение текущего разговора с ассистентом."""
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений."""
    user_id = update.effective_user.id
    text = update.message.text

    if user_id in active_threads:
        _, thread_id, assistant_type = active_threads[user_id]
        
        try:
            client.beta.threads.delete(thread_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении потока: {e}")
        
        del active_threads[user_id]
        
    if text == "🎮 Выбрать ассистента":
        await update.message.reply_text(
            f"👋 Разговор с ассистентом *{ASSISTANT_NAMES[assistant_type].replace('📊 ', '').replace('💡 ', '').replace('📝 ', '').replace('🔄 ', '')}* завершен.\n\n"
            "🎮 Вы всегда можете начать новое общение, нажав кнопку \"Выбрать ассистента\"",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        logger.info(f"Завершен чат для пользователя {user_id}")
    else:
        await update.message.reply_text(
            "❌ У вас нет активного разговора.\n\n"
            "🎮 Нажмите кнопку \"Выбрать ассистента\" для начала нового общения.",
            "Откройте Mini App для выбора ассистента:",
            reply_markup=get_main_keyboard()
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка входящих сообщений от пользователя."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Обработка кнопок клавиатуры
    if message_text == "🎮 Выбрать ассистента":
        await send_general_assistant_selection_message(update, context)
        return
    elif message_text == "🛑 Остановить обсуждение":
        await stop_chat(update, context)
        return
    elif message_text == "👤 Профиль":
        await profile_command(update, context)
        return
    
    # Проверка наличия активного разговора для обычных сообщений
    if user_id not in active_threads:
        user_status = get_user_status(user_id)
        if user_status != 'registered':
            await update.message.reply_text(
                "❌ **Необходима регистрация**\n\n"
                "Для использования ассистентов необходимо пройти регистрацию.\n"
                "🎮 Нажмите кнопку \"Выбрать ассистента\" для начала.",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
        else:
        
    if text == "🛑 Остановить обсуждение":
        if user_id in active_threads:
            del active_threads[user_id]
            await update.message.reply_text(
                "❌ У вас нет активного разговора с ассистентом.\n\n"
                "🎮 Нажмите кнопку \"Выбрать ассистента\" для начала общения.",
                "🗑️ Диалог завершен",
                reply_markup=get_main_keyboard()
            )
        return

    # Получение информации об активном ассистенте
    assistant_id, thread_id, assistant_type = active_threads[user_id]
    if user_id not in active_threads:
        await update.message.reply_text(
            "❌ Сначала выберите ассистента",
            reply_markup=get_main_keyboard()
        )
        return

    # Отправка действия "набирает текст"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await process_assistant_response(update, context)

async def process_assistant_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка запроса к ассистенту."""
    user_id = update.effective_user.id
    assistant_id, thread_id, _ = active_threads[user_id]
    
    await context.bot.send_chat_action(user_id, "typing")

    try:
        # Добавление сообщения пользователя в поток
        # Добавление сообщения в thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_text
            content=update.message.text
        )

        # Запуск ассистента в потоке
        # Запуск ассистента
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            assistant_id=assistant_id
        )

        # Ожидание ответа
        response = await poll_run(thread_id, run.id)
        response = await wait_for_assistant_response(thread_id, run.id)

        # Отправка ответа ассистента
        # Отправка ответа
        if response:
            for message_chunk in split_response(response):
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                await update.message.reply_text(
                    message_chunk, 
                    reply_markup=get_main_keyboard(),
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                "❌ Не удалось сформировать ответ. Пожалуйста, попробуйте снова.",
                response[:MAX_MESSAGE_LENGTH],
                reply_markup=get_main_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка в разговоре: {e}")
        logger.error(f"Assistant error: {e}")
        await update.message.reply_text(
            "❌ Извините, возникла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.",
            "❌ Ошибка обработки запроса",
            reply_markup=get_main_keyboard()
        )

def clean_markdown_formatting(text: str) -> str:
    """Очищает и исправляет markdown форматирование для Telegram."""
    import re
    
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    text = re.sub(r'###\s*(.*?)(?=\n|$)', r'*\1*', text)
    text = re.sub(r'##\s*(.*?)(?=\n|$)', r'*\1*', text)
    text = re.sub(r'#\s*(.*?)(?=\n|$)', r'*\1*', text)
    text = re.sub(r'^\s*[\-\*]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'\*{3,}', '**', text)
    
    return text

def split_response(response: str) -> list:
    """Разбивает длинный ответ на части, не превышающие максимальную длину сообщения Telegram."""
    response = clean_markdown_formatting(response)
    
    if len(response) <= MAX_MESSAGE_LENGTH:
        return [response]
    
    chunks = []
    current_chunk = ""
    
    paragraphs = response.split('\n\n')
    
    for paragraph in paragraphs:
        if len(paragraph) > MAX_MESSAGE_LENGTH:
            sentences = paragraph.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 2 <= MAX_MESSAGE_LENGTH:
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence
        else:
            if len(current_chunk) + len(paragraph) + 2 <= MAX_MESSAGE_LENGTH:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

async def poll_run(thread_id: str, run_id: str) -> str:
    """Ожидание завершения выполнения и возврат ответа ассистента."""
    max_attempts = 60
    for _ in range(max_attempts):
async def wait_for_assistant_response(thread_id: str, run_id: str) -> str:
    """Ожидание ответа ассистента."""
    for _ in range(30):  # 30 попыток с интервалом 1 сек
        await asyncio.sleep(1)

        run = client.beta.threads.runs.retrieve(
@@ -756,163 +257,50 @@ async def poll_run(thread_id: str, run_id: str) -> str:
        )

        if run.status == "completed":
            messages = client.beta.threads.messages.list(
                thread_id=thread_id
            )
            
            for message in messages.data:
                if message.role == "assistant":
                    content = ""
                    for content_part in message.content:
                        if content_part.type == "text":
                            content += content_part.text.value
                    
                    return content
            
            return "Нет ответа от ассистента."
            messages = client.beta.threads.messages.list(thread_id)
            for msg in messages.data:
                if msg.role == "assistant":
                    return msg.content[0].text.value

        if run.status in ["failed", "cancelled", "expired"]:
            logger.error(f"Выполнение завершилось со статусом: {run.status}")
            return "Извините, я не смог выполнить запрос."
        if run.status in ["failed", "cancelled"]:
            return "❌ Ошибка обработки запроса"

    return "Ответ занимает слишком много времени. Пожалуйста, попробуйте позже."
    return "⏳ Ответ занимает больше времени, чем ожидалось"

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатий на inline кнопки."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("select_"):
        assistant_type = query.data[7:]
        
        if assistant_type in ASSISTANTS:
            await start_chat_with_type(update, context, assistant_type)
def shutdown_handler(signum, frame):
    """Обработчик сигналов завершения работы."""
    logger.info("Получен сигнал завершения...")
    if application:
        application.stop()
    exit(0)

# HTTP сервер для API и health check
class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Bot is running!')
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/register':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                # Валидируем данные Telegram
                init_data = data.get('initData')
                bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                
                user_data = validate_telegram_data(init_data, bot_token)
                
                if user_data:
                    # Регистрируем пользователя
                    register_user(user_data['id'])
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    response = {'success': True, 'message': 'Пользователь зарегистрирован'}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    response = {'success': False, 'message': 'Неверные данные'}
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    
            except Exception as e:
                logger.error(f"Ошибка API регистрации: {e}")
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {'success': False, 'message': 'Ошибка сервера'}
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
def main():
    """Основная функция запуска бота."""
    global application

    def log_message(self, format, *args):
        pass

def run_api_server(port):
    """Запуск HTTP сервера для API и health check."""
    server = HTTPServer(('0.0.0.0', port), APIHandler)
    logger.info(f"API сервер запущен на порту {port}")
    server.serve_forever()

def main() -> None:
    """Запуск бота."""
    # Инициализация базы данных
    # Инициализация БД
    init_database()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Переменная окружения TELEGRAM_BOT_TOKEN не установлена!")
        return
    
    missing_assistants = [name for name, aid in ASSISTANTS.items() if not aid]
    if missing_assistants:
        logger.error(f"Не указаны ID для ассистентов: {missing_assistants}")
        logger.error("Проверьте переменные окружения OPENAI_ASSISTANT_ID_*")
    # Проверка токена
    if not (token := os.getenv("TELEGRAM_BOT_TOKEN")):
        logger.error("Токен бота не найден!")
        return

    # Создание приложения
    application = Application.builder().token(token).build()

    # Добавление обработчиков
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    application.add_handler(InlineQueryHandler(handle_inline_query))
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Запуск бота")
    # Регистрация обработчиков сигналов
    signal(SIGINT, shutdown_handler)
    signal(SIGTERM, shutdown_handler)

    port = os.environ.get("PORT")
    if port:
        api_thread = Thread(target=run_api_server, args=(int(port),), daemon=True)
        api_thread.start()
        logger.info(f"API сервер запущен на порту {port}")
        
        logger.info("Запуск в polling режиме с API сервером")
        try:
            application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Ошибка при запуске polling: {e}")
            logger.info("Пытаемся запустить без drop_pending_updates")
            application.run_polling()
    else:
        logger.info("Запуск в polling режиме")
        try:
            application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Ошибка при запуске polling: {e}")
            logger.info("Пытаемся запустить без drop_pending_updates")
            application.run_polling()
    # Запуск бота
    logger.info("Бот запущен")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
