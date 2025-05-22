import os
import logging
import asyncio
import textwrap
from typing import Dict, Any, Tuple

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
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

# Максимальная длина сообщения Telegram
MAX_MESSAGE_LENGTH = 4096

# URL Mini App для выбора ассистента
MINI_APP_URL = "https://ai4business-ai.github.io/front-bot-repo/"

# Хранение активных разговоров: user_id -> (assistant_id, thread_id, assistant_type)
active_threads: Dict[int, Tuple[str, str, str]] = {}

# ID ассистентов из переменных окружения
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

def get_main_keyboard():
    """Создание основной клавиатуры с кнопками управления."""
    keyboard = [
        [KeyboardButton("🎮 Выбрать ассистента", web_app=WebAppInfo(url=MINI_APP_URL))],
        [KeyboardButton("🛑 Остановить обсуждение")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, persistent=True)

def get_assistant_selection_keyboard():
    """Создание inline клавиатуры для выбора ассистента."""
    keyboard = []
    for assistant_type, name in ASSISTANT_NAMES.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"select_{assistant_type}")])
    
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка приветственного сообщения по команде /start."""
    help_text = (
        "👋 Привет! Я бот с бизнес-ассистентами на базе ИИ.\n\n"
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
    
    await update.message.reply_text(help_text, reply_markup=get_main_keyboard())

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
        "🛑 Остановить обсуждение - завершить текущий разговор\n\n"
        "💡 **Совет:** После выбора ассистента просто пишите свои вопросы, и он ответит!"
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
            "Нажмите кнопку \"Выбрать ассистента\" для начала.",
            reply_markup=get_main_keyboard()
        )

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка данных из Mini App."""
    # Когда пользователь выбирает ассистента в Mini App, отправляем сообщение с выбором
    await send_assistant_selection_message(update, context)

async def send_assistant_selection_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка сообщения с выбором ассистента."""
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
        reply_markup=get_assistant_selection_keyboard()
    )

async def start_chat_with_type(update: Update, context: ContextTypes.DEFAULT_TYPE, assistant_type: str) -> None:
    """Начало нового разговора с ассистентом указанного типа."""
    user_id = update.effective_user.id
    
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
        f"✅ **Запущен ассистент: {ASSISTANT_NAMES[assistant_type]}**\n\n"
        f"📝 {ASSISTANT_DESCRIPTIONS[assistant_type]}\n\n"
        "💬 Теперь можете отправлять мне свои вопросы, и я отвечу!\n\n"
        "🔄 Используйте кнопку \"Выбрать ассистента\" для смены ассистента\n"
        "🛑 Используйте кнопку \"Остановить обсуждение\" для завершения"
    )
    
    logger.info(f"Начат новый чат для пользователя {user_id} с ассистентом '{ASSISTANT_NAMES[assistant_type]}' (ID: {assistant_id}) в потоке {thread.id}")

async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завершение текущего разговора с ассистентом."""
    user_id = update.effective_user.id
    
    if user_id in active_threads:
        _, thread_id, assistant_type = active_threads[user_id]
        
        # Удаление потока
        try:
            client.beta.threads.delete(thread_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении потока: {e}")
        
        # Удаление из активных разговоров
        del active_threads[user_id]
        
        await update.message.reply_text(
            f"👋 Разговор с ассистентом **{ASSISTANT_NAMES[assistant_type]}** завершен.\n\n"
            "🎮 Вы всегда можете начать новое общение, нажав кнопку \"Выбрать ассистента\"",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"Завершен чат для пользователя {user_id}")
    else:
        await update.message.reply_text(
            "❌ У вас нет активного разговора.\n\n"
            "🎮 Нажмите кнопку \"Выбрать ассистента\" для начала нового общения.",
            reply_markup=get_main_keyboard()
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка входящих сообщений от пользователя."""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    # Обработка кнопок клавиатуры
    if message_text == "🎮 Выбрать ассистента":
        await send_assistant_selection_message(update, context)
        return
    elif message_text == "🛑 Остановить обсуждение":
        await stop_chat(update, context)
        return
    
    # Проверка наличия активного разговора для обычных сообщений
    if user_id not in active_threads:
        await update.message.reply_text(
            "❌ У вас нет активного разговора с ассистентом.\n\n"
            "🎮 Нажмите кнопку \"Выбрать ассистента\" для начала общения.",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Получение информации об активном ассистенте
    assistant_id, thread_id, assistant_type = active_threads[user_id]
    
    # Отправка действия "набирает текст"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        # Добавление сообщения пользователя в поток
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_text
        )
        
        # Запуск ассистента в потоке
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
        )
        
        # Ожидание ответа
        response = await poll_run(thread_id, run.id)
        
        # Отправка ответа ассистента
        if response:
            # Разбиваем длинный ответ на части и отправляем их по очереди
            for message_chunk in split_response(response):
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                await update.message.reply_text(message_chunk, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(
                "❌ Не удалось сформировать ответ. Пожалуйста, попробуйте снова.",
                reply_markup=get_main_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Ошибка в разговоре: {e}")
        await update.message.reply_text(
            "❌ Извините, возникла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.",
            reply_markup=get_main_keyboard()
        )

def split_response(response: str) -> list:
    """Разбивает длинный ответ на части, не превышающие максимальную длину сообщения Telegram."""
    if len(response) <= MAX_MESSAGE_LENGTH:
        return [response]
    
    # Разбиваем по параграфам, чтобы не разрывать текст в середине предложения
    chunks = []
    current_chunk = ""
    
    # Разбиваем текст на параграфы
    paragraphs = response.split('\n\n')
    
    for paragraph in paragraphs:
        # Если параграф слишком длинный, разбиваем его по предложениям
        if len(paragraph) > MAX_MESSAGE_LENGTH:
            sentences = paragraph.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 2 <= MAX_MESSAGE_LENGTH:
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                else:
                    chunks.append(current_chunk)
                    current_chunk = sentence
        else:
            # Проверяем, поместится ли параграф в текущий фрагмент
            if len(current_chunk) + len(paragraph) + 2 <= MAX_MESSAGE_LENGTH:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                chunks.append(current_chunk)
                current_chunk = paragraph
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

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
    """Обработка нажатий на inline кнопки."""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем тип ассистента из callback_data
    if query.data.startswith("select_"):
        assistant_type = query.data[7:]  # Убираем "select_"
        
        if assistant_type in ASSISTANTS:
            await start_chat_with_type(update, context, assistant_type)

def main() -> None:
    """Запуск бота."""
    # Получение токена Telegram из переменной окружения
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Переменная окружения TELEGRAM_BOT_TOKEN не установлена!")
        return
    
    # Проверка наличия ID ассистентов
    missing_assistants = [name for name, aid in ASSISTANTS.items() if not aid]
    if missing_assistants:
        logger.error(f"Не указаны ID для ассистентов: {missing_assistants}")
        logger.error("Проверьте переменные окружения OPENAI_ASSISTANT_ID_*")
        return
    
    # Создание приложения
    application = Application.builder().token(token).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Обработка текстовых сообщений (включая кнопки клавиатуры)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработка данных из Web App
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    # Обработка нажатий на inline кнопки
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запуск бота
    logger.info("Запуск бота")
    
    try:
        # Пробуем использовать run_polling с drop_pending_updates, если доступно
        application.run_polling(drop_pending_updates=True)
    except TypeError:
        # Если drop_pending_updates недоступен, используем обычный run_polling
        logger.info("Параметр drop_pending_updates недоступен, запуск стандартного polling")
        application.run_polling()

if __name__ == "__main__":
    main()
