# Telegram-OpenAI Bot с бизнес-ассистентами и системой регистрации

Этот бот предоставляет доступ к четырем специализированным бизнес-ассистентам через Telegram с интегрированной системой регистрации пользователей.

## Новые функции

### 🔐 Система регистрации пользователей
- **Два статуса пользователей**: обычный пользователь и зарегистрированный пользователь
- **База данных SQLite** для хранения информации о пользователях
- **Telegram Mini App** с интерфейсом регистрации
- **Отображение информации о пользователе** в правом верхнем углу Mini App
- **Контроль доступа**: только зарегистрированные пользователи могут использовать ассистентов

### 👤 Информация о пользователе
- Отображение никнейма/имени пользователя в Mini App
- Статус регистрации (✅ зарегистрирован / ⏳ требуется регистрация)
- Аватар с инициалами пользователя
- Команда `/profile` для просмотра детальной информации

## Функциональность

### 🤖 Бизнес-ассистенты
- **/market** - Анализ рынка и конкурентный анализ
- **/founder** - Обсуждение идей фаундера
- **/business** - Составление бизнес-модели
- **/adapter** - Адаптатор идей из кейсов

### 🛠 Управление
- Завершение разговора через команду **/end** или кнопку "🛑 Остановить обсуждение"
- Сохранение контекста разговора для каждого пользователя
- Интеллектуальная обработка длинных ответов с разбиением на несколько сообщений

### 📱 Telegram Mini App
- Современный интерфейс для выбора ассистентов
- Интегрированная система регистрации
- Адаптивный дизайн под тему Telegram
- Поддержка как light, так и dark режимов

## Технологии

- **Backend**: Python, python-telegram-bot, OpenAI Assistants API
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, JavaScript, Telegram WebApp API
- **Hosting**: Backend на Render.com, Frontend на GitHub Pages
- **Security**: Валидация данных Telegram WebApp с HMAC-SHA256

## Процесс использования

### Для новых пользователей:
1. Найдите бота в Telegram
2. Отправьте команду `/start`
3. Нажмите кнопку "🎮 Выбрать ассистента"
4. **Пройдите быструю регистрацию** в Mini App
5. Выберите нужного ассистента
6. Начните общение!

### Для зарегистрированных пользователей:
1. Нажмите "🎮 Выбрать ассистента"
2. Выберите нужного ассистента в Mini App
3. Начните общение с выбранным ассистентом
4. Используйте "🛑 Остановить обсуждение" для завершения

## Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку по использованию
- `/status` - Узнать, какой ассистент активен
- `/profile` - Показать информацию о профиле пользователя

## Переменные окружения

Для запуска бота требуются следующие переменные окружения:

### Обязательные:
- `TELEGRAM_BOT_TOKEN`: токен вашего Telegram бота
- `OPENAI_API_KEY`: ключ API OpenAI

### ID ассистентов (обязательные):
- `OPENAI_ASSISTANT_ID_MARKET`: ID ассистента для анализа рынка
- `OPENAI_ASSISTANT_ID_FOUNDER`: ID ассистента для обсуждения идей фаундера
- `OPENAI_ASSISTANT_ID_BUSINESS`: ID ассистента для составления бизнес-модели
- `OPENAI_ASSISTANT_ID_ADAPTER`: ID ассистента для адаптации идей из кейсов

## База данных

Бот автоматически создает SQLite базу данных `users.db` со следующей структурой:

```sql
CREATE TABLE users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    status TEXT DEFAULT 'user',
    registered_at TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Статусы пользователей:
- `user` - обычный пользователь (только запустил бота)
- `registered` - зарегистрированный пользователь (может использовать ассистентов)

## API Endpoints

Бот предоставляет следующие API endpoints:

- `GET /` - Health check (возвращает "Bot is running!")
- `POST /api/register` - Регистрация пользователя (с валидацией Telegram данных)

## Безопасность

- **Валидация данных Telegram WebApp** с использованием HMAC-SHA256
- **Проверка подлинности** всех запросов из Mini App
- **Контроль доступа** к ассистентам только для зарегистрированных пользователей
- **Безопасное хранение** пользовательских данных в базе данных

## Развертывание

### Backend (Render.com):
1. Создайте аккаунт на Render.com
2. Подключите ваш GitHub репозиторий
3. Настройте переменные окружения
4. Бот автоматически развернется и будет доступен

### Frontend (GitHub Pages):
1. Разместите файлы `index.html`, `styles.css`, `app.js`, `version.js` в репозитории
2. Включите GitHub Pages в настройках репозитория
3. Mini App будет доступно по адресу `https://username.github.io/repository-name/`

## Структура проекта

```
├── simple_bot.py          # Основной файл бота с API
├── requirements.txt       # Python зависимости
├── Procfile              # Конфигурация для Render.com
├── index.html            # Mini App - главная страница
├── styles.css            # Стили для Mini App
├── app.js                # JavaScript логика Mini App
├── version.js            # Система версионирования
├── .env-example          # Пример переменных окружения
└── README.md             # Документация
```

## Особенности реализации

### Telegram Mini App Integration:
- Поддержка `keyboard button` и `menu button` режимов запуска
- Автоматическое определение способа запуска
- Fallback инструкции для разных типов запуска

### Database Management:
- Автоматическое создание таблиц при первом запуске
- Отслеживание активности пользователей
- Миграции базы данных (при необходимости)

### Error Handling:
- Graceful обработка ошибок API
- Retry логика для OpenAI запросов
- Логирование всех важных событий

## Лицензия и поддержка

Проект разработан для демонстрации интеграции Telegram Bot API, OpenAI Assistants API и Telegram Mini Apps с системой регистрации пользователей.

Для поддержки и вопросов создайте issue в GitHub репозитории.
