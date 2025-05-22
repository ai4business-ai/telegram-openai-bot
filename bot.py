import os
import logging
import asyncio
import textwrap
from typing import Dict, Any, Tuple
import uuid

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultsButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, InlineQueryHandler
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

# URL Mini App для выбора ассистента (замените на URL вашего мини-приложения)
MINI_APP_URL = "https://ai4business-ai.github.io/front-bot-repo/"

# Хранение активных разговоров: user_id -> (assistant_id, thread_id, assistant_type)
active_threads: Dict[int, Tuple[str, str, str]] = {}

# Типы ассистентов и их команды
ASSISTANT_TYPES = {
    "market": "market",     # Анализ рынка и конкурентный анализ
    "founder": "founder",   # Обсуждение идей фаундера
    "business": "business", # Составление бизнес-модели
    "adapter": "adapter"    # Адаптатор идей из кейсов
}

# Получение ID ассистентов из переменных окружения или создание новых
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

# Инструкции для ассистентов
ASSISTANT_INSTRUCTIONS = {
    "market": "Вы — специалист по анализу рынка и конкурентов. Помогайте пользователям анализировать рыночные ниши, изучать конкурентов, выявлять тренды и находить возможности для развития. Давайте структурированные ответы с конкретными рекомендациями на основе информации, предоставленной пользователем.",
    
    "founder": "Вы — опытный консультант для основателей бизнеса. Помогайте фаундерам обсуждать, анализировать и улучшать их бизнес-идеи. Задавайте уточняющие вопросы, предлагайте альтернативные подходы и помогайте выявить сильные и слабые стороны концепций. Ваша цель — помочь превратить идеи в жизнеспособные бизнес-проекты.",
    
    "business": "Вы — эксперт по бизнес-моделированию. Помогайте пользователям составлять структурированные бизнес-модели, определять источники доходов, структуру расходов, ценностные предложения и другие ключевые элементы. Работайте в формате Canvas и других методологий по запросу. Давайте практические советы по улучшению бизнес-модели для достижения устойчивого роста.",
    
    "adapter": "Вы — эксперт по бизнес-кейсам. Помогайте пользователям адаптировать успешные идеи и стратегии из известных бизнес-кейсов для их конкретных проектов. Анализируйте ключевые факторы успеха в разных кейсах и предлагайте, как их можно применить в других контекстах. Обращайте внимание на особенности отрасли, масштаб бизнеса и уникальные характеристики ситуации пользователя."
}

# Проверка и создание ассистентов, если необходимо
for assistant_type, assistant_id in ASSISTANTS.items():
    if not assistant_id:
        try:
            assistant = client.beta.assistants.create(
                name=ASSISTANT_NAMES[assistant_type],
                instructions=ASSISTANT_INSTRUCTIONS[assistant_type],
                model="gpt-4-turbo",
            )
            ASSISTANTS[assistant_type] = assistant.id
            logger.info(f"Создан новый ассистент '{ASSISTANT_NAMES[assistant_type]}' с ID: {assistant.id}")
        except Exception as e:
            logger.error(f"Ошибка при создании ассистента '{ASSISTANT_NAMES[assistant_type]}': {e}")
            # Если не удалось создать первый ассистент, используем существующие
            existing_assistants = [aid for aid in ASSISTANTS.values() if aid]
            if existing_assistants:
                ASSISTANTS[assistant_type] = existing_assistants[0]
                logger.info(f"Используется существующий ассистент для '{ASSISTANT_NAMES[assistant_type]}'")
            else:
                logger.error(f"Не удалось создать ассистента '{ASSISTANT_NAMES[assistant_type]}' и нет запасного варианта")
    else:
        logger.info(f"Используется существующий ассистент '{ASSISTANT_NAMES[assistant_type]}' с ID: {assistant_id}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка приветственного сообщения по команде /start."""
    help_text = (
        "👋 Привет! Я бот с несколькими AI ассистентами.\n\n"
        "🔧 **Как использовать:**\n"
        "1. Напишите `@" + context.bot.username + "` в любом чате\n"
        "2. Выберите ассистента в мини-приложении\n"
        "3. Начните общение с выбранным ассистентом\n\n"
        "📱 **Доступные ассистенты:**\n"
        f"• {ASSISTANT_NAMES['market']} - {ASSISTANT_DESCRIPTIONS['market']}\n"
        f"• {ASSISTANT_NAMES['founder']} - {ASSISTANT_DESCRIPTIONS['founder']}\n"
        f"• {ASSISTANT_NAMES['business']} - {ASSISTANT_DESCRIPTIONS['business']}\n"
        f"• {ASSISTANT_NAMES['adapter']} - {ASSISTANT_DESCRIPTIONS['adapter']}\n\n"
        "ℹ️ Используйте /end для завершения текущего разговора\n"
        "❓ Используйте /help для справки"
    )
    
    await update.message.reply_text(help_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка справочного сообщения по команде /help."""
    help_text = (
        "📋 **Справка по использованию бота**\n\n"
        "🔧 **Основной способ использования:**\n"
        f"Напишите `@{context.bot.username}` в любом чате, затем выберите ассистента\n\n"
        "📱 **Доступные ассистенты:**\n"
        f"• {ASSISTANT_NAMES['market']} - {ASSISTANT_DESCRIPTIONS['market']}\n"
        f"• {ASSISTANT_NAMES['founder']} - {ASSISTANT_DESCRIPTIONS['founder']}\n"
        f"• {ASSISTANT_NAMES['business']} - {ASSISTANT_DESCRIPTIONS['business']}\n"
        f"• {ASSISTANT_NAMES['adapter']} - {ASSISTANT_DESCRIPTIONS['adapter']}\n\n"
        "⚙️ **Команды:**\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/end - Завершить текущий разговор\n"
        "/status - Узнать, какой ассистент активен\n\n"
        "💡 **Совет:** После выбора ассистента просто пишите свои вопросы, и он ответит!"
    )
    
    await update.message.reply_text(help_text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать статус текущего активного ассистента."""
    user_id = update.effective_user.id
    
    if user_id in active_threads:
        _, _, assistant_type = active_threads[user_id]
        assistant_name = ASSISTANT_NAMES[assistant_type]
        await update.message.reply_text(
            f"🤖 **Активный ассистент:** {assistant_name}\n\n"
            f"📝 **Описание:** {ASSISTANT_DESCRIPTIONS[assistant_type]}\n\n"
            "💬 Можете продолжать задавать вопросы или использовать /end для завершения разговора."
        )
    else:
        await update.message.reply_text(
            "❌ У вас нет активного разговора с ассистентом.\n\n"
            f"Для выбора ассистента напишите `@{context.bot.username}` в любом чате."
        )

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка inline запросов."""
    query = update.inline_query.query.lower()
    
    # Создаем результаты для каждого ассистента
    results = []
    
    for assistant_type, assistant_name in ASSISTANT_NAMES.items():
        # Фильтруем результаты по запросу, если он есть
        if not query or query in assistant_name.lower() or query in ASSISTANT_DESCRIPTIONS[assistant_type].lower():
            result = InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=assistant_name,
                description=ASSISTANT_DESCRIPTIONS[assistant_type],
                input_message_content=InputTextMessageContent(
                    message_text=f"🤖 Запускаю ассистента: {assistant_name}\n\nОтправьте мне ваш вопрос, и я отвечу!"
                ),
                # Добавляем данные для обработки выбора
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 Начать общение", callback_data=f"start_{assistant_type}")]
                ])
            )
            results.append(result)
    
    # Добавляем кнопку для открытия Mini App
    button = InlineQueryResultsButton(
        text="🎮 Выбрать через Mini App",
        web_app=WebAppInfo(url=f"{MINI_APP_URL}?mode=inline")
    )
    
    await update.inline_query.answer(results, button=button, cache_time=1)

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
        await update.message.reply_text(
            f"❌ Извините, ассистент '{ASSISTANT_NAMES[assistant_type]}' недоступен в данный момент."
        )
        return
    
    # Создание нового потока
    thread = client.beta.threads.create()
    active_threads[user_id] = (assistant_id, thread.id, assistant_type)
    
    await update.message.reply_text(
        f"✅ Запущен ассистент: **{ASSISTANT_NAMES[assistant_type]}**\n\n"
        f"📝 {ASSISTANT_DESCRIPTIONS[assistant_type]}\n\n"
        "💬 Отправьте мне ваш вопрос, и я отвечу!\n"
        "⚙️ Используйте /end для завершения разговора"
    )
    
    logger.info(f"Начат новый чат для пользователя {user_id} с ассистентом '{ASSISTANT_NAMES[assistant_type]}' (ID: {assistant_id}) в потоке {thread.id}")

async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            f"Для выбора нового ассистента напишите `@{context.bot.username}` в любом чате."
        )
        logger.info(f"Завершен чат для пользователя {user_id}")
    else:
        await update.message.reply_text(
            "❌ У вас нет активного разговора.\n\n"
            f"Для выбора ассистента напишите `@{context.bot.username}` в любом чате."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка входящих сообщений от пользователя."""
    user_id = update.effective_user.id
    
    # Проверка наличия активного разговора
    if user_id not in active_threads:
        await update.message.reply_text(
            "❌ У вас нет активного разговора с ассистентом.\n\n"
            f"Для выбора ассистента напишите `@{context.bot.username}` в любом чате и выберите нужного ассистента."
        )
        return
    
    # Получение сообщения пользователя
    user_message = update.message.text
    assistant_id, thread_id, assistant_type = active_threads[user_id]
    
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
            assistant_id=assistant_id,
        )
        
        # Ожидание ответа
        response = await poll_run(thread_id, run.id)
        
        # Отправка ответа ассистента
        if response:
            # Разбиваем длинный ответ на части и отправляем их по очереди
            for message_chunk in split_response(response):
                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                await update.message.reply_text(message_chunk)
        else:
            await update.message.reply_text("❌ Не удалось сформировать ответ. Пожалуйста, попробуйте снова.")
            
    except Exception as e:
        logger.error(f"Ошибка в разговоре: {e}")
        await update.message.reply_text(
            "❌ Извините, возникла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз или начните новый разговор."
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
    """Обработка нажатий на кнопки."""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем тип ассистента из callback_data
    if query.data.startswith("start_"):
        assistant_type = query.data[6:]  # Убираем "start_"
        
        if assistant_type in ASSISTANT_TYPES:
            await query.edit_message_text(
                text=f"🤖 Запускаю ассистента: {ASSISTANT_NAMES[assistant_type]}..."
            )
            await start_chat_with_type(update, context, assistant_type)

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
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("end", end_chat))
    
    # Добавляем обработчик inline запросов
    application.add_handler(InlineQueryHandler(inline_query))
    
    # Обработка текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработка нажатий на кнопки
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
