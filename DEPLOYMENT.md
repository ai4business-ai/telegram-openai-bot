# 🚀 Руководство по развертыванию Telegram Bot с системой регистрации

Это подробное руководство поможет вам развернуть Telegram бота с бизнес-ассистентами и системой регистрации пользователей.

## 📋 Предварительные требования

### 1. Аккаунты и токены
- **Telegram Bot Token**: получите у [@BotFather](https://t.me/botfather)
- **OpenAI API Key**: создайте в [OpenAI Dashboard](https://platform.openai.com/)
- **GitHub Account**: для размещения frontend
- **Render.com Account**: для размещения backend

### 2. OpenAI Assistants
Создайте 4 ассистента в OpenAI Dashboard:

#### 📊 Анализ рынка
```
Название: Market Analysis Assistant
Инструкции: Ты эксперт по анализу рынка и конкурентов. Помогаешь проанализировать рыночные ниши, изучить конкурентов и найти возможности для развития бизнеса. Отвечай структурированно с конкретными рекомендациями.
```

#### 💡 Идеи фаундера
```
Название: Founder Ideas Assistant  
Инструкции: Ты ментор для основателей бизнеса. Помогаешь обсуждать и прорабатывать бизнес-идеи, находить слабые места и возможности для улучшения. Задавай уточняющие вопросы и давай практические советы.
```

#### 📝 Бизнес-модель
```
Название: Business Model Assistant
Инструкции: Ты эксперт по бизнес-моделированию. Помогаешь создавать и анализировать бизнес-модели, рассчитывать юнит-экономику и планировать источники доходов. Используй фреймворки как Business Model Canvas.
```

#### 🔄 Адаптатор идей
```
Название: Case Adapter Assistant
Инструкции: Ты эксперт по адаптации успешных бизнес-кейсов. Помогаешь изучать лучшие практики из различных индустрий и адаптировать их под конкретный бизнес пользователя. Давай практические примеры реализации.
```

## 🏗️ Пошаговое развертывание

### Шаг 1: Подготовка проекта

1. **Клонируйте репозиторий**:
```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```

2. **Настройте среду разработки** (опционально):
```bash
python dev_config.py setup
```

3. **Создайте .env файл**:
```bash
cp .env-example .env
```

4. **Заполните переменные окружения**:
```env
TELEGRAM_BOT_TOKEN=1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
OPENAI_API_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyz
OPENAI_ASSISTANT_ID_MARKET=asst_1234567890abcdef
OPENAI_ASSISTANT_ID_FOUNDER=asst_abcdef1234567890
OPENAI_ASSISTANT_ID_BUSINESS=asst_xyz1234567890abc
OPENAI_ASSISTANT_ID_ADAPTER=asst_def1234567890xyz
```

### Шаг 2: Развертывание Frontend (GitHub Pages)

1. **Подготовьте frontend файлы**:
   - `index.html`
   - `styles.css`
   - `app.js`
   - `version.js`

2. **Обновите URL в коде**:
   В `simple_bot.py` измените:
   ```python
   MINI_APP_URL = "https://your-username.github.io/your-repo-name/"
   ```

3. **Настройте GitHub Pages**:
   - Перейдите в Settings → Pages
   - Source: Deploy from a branch
   - Branch: main / root
   - Сохраните изменения

4. **Проверьте доступность**:
   ```
   https://your-username.github.io/your-repo-name/
   ```

### Шаг 3: Развертывание Backend (Render.com)

1. **Подготовьте файлы для Render**:
   - `simple_bot.py`
   - `requirements.txt`
   - `Procfile`

2. **Создайте новый Web Service на Render**:
   - Connect repository
   - Name: `telegram-business-bot`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python simple_bot.py`

3. **Настройте переменные окружения в Render**:
   ```
   TELEGRAM_BOT_TOKEN=your_token
   OPENAI_API_KEY=your_key
   OPENAI_ASSISTANT_ID_MARKET=your_id
   OPENAI_ASSISTANT_ID_FOUNDER=your_id
   OPENAI_ASSISTANT_ID_BUSINESS=your_id
   OPENAI_ASSISTANT_ID_ADAPTER=your_id
   ```

4. **Разверните сервис**:
   - Нажмите "Deploy"
   - Дождитесь завершения деплоя

### Шаг 4: Настройка Telegram Bot

1. **Настройте команды бота**:
   Отправьте @BotFather:
   ```
   /setcommands
   start - Начать работу с ботом
   help - Показать справку
   status - Узнать активного ассистента
   profile - Информация о профиле
   ```

2. **Настройте описание бота**:
   ```
   /setdescription
   Бот с 4 бизнес-ассистентами на базе ИИ. Помогает с анализом рынка, идеями фаундера, бизнес-моделью и адаптацией успешных кейсов. Требуется быстрая регистрация.
   ```

3. **Настройте короткое описание**:
   ```
   /setabouttext
   ИИ-ассистенты для бизнеса: анализ рынка, идеи, бизнес-модели, кейсы
   ```

4. **Включите inline режим** (опционально):
   ```
   /setinline
   ```

5. **Настройте кнопку меню**:
   ```
   /setmenubutton
   ```
   Выберите "Configure menu button" и укажите URL Mini App.

## 🔧 Настройка базы данных

### Автоматическая инициализация
Бот автоматически создаст SQLite базу при первом запуске.

### Ручная инициализация (опционально)
```bash
python db_migration.py migrate
python db_migration.py status
```

### Создание тестовых данных
```bash
python dev_config.py testdb
```

## 🧪 Тестирование

### 1. Проверка конфигурации
```bash
python check_config.py
```

### 2. Локальное тестирование
```bash
python run_dev.py
```

### 3. Тестирование Mini App
```bash
python test_mini_app.py
```

### 4. Проверка регистрации
1. Запустите бота в Telegram
2. Отправьте `/start`
3. Нажмите "🎮 Выбрать ассистента"
4. Пройдите регистрацию
5. Выберите ассистента
6. Отправьте тестовое сообщение

## 📊 Мониторинг и управление

### Просмотр статистики пользователей
```bash
python user_utils.py stats
python db_migration.py stats
```

### Управление пользователями
```bash
# Список всех пользователей
python user_utils.py list

# Зарегистрированные пользователи
python user_utils.py list registered

# Информация о пользователе
python user_utils.py show 123456789

# Регистрация пользователя
python user_utils.py register 123456789
```

### Экспорт данных
```bash
# JSON экспорт
python user_utils.py export json

# CSV экспорт  
python user_utils.py export csv
```

### Очистка неактивных пользователей
```bash
# Просмотр кандидатов на удаление
python user_utils.py inactive 90

# Удаление неактивных (осторожно!)
python user_utils.py cleanup 90
```

## 🔄 Обновления и миграции

### Проверка версии базы данных
```bash
python db_migration.py status
```

### Применение миграций
```bash
python db_migration.py migrate
```

### Откат к предыдущей версии
```bash
# Откат кода
./rollback.sh rollback 1.0.1

# Откат базы данных
python db_migration.py rollback 1.0.0
```

### Создание новой версии
```bash
./rollback.sh create 2.1.0
```

## 🐛 Устранение неисправностей

### Проблемы с регистрацией

**Ошибка: "Необходима регистрация"**
- Проверьте, что пользователь прошел процесс регистрации в Mini App
- Проверьте статус в базе: `python user_utils.py show USER_ID`
- Принудительно зарегистрируйте: `python user_utils.py register USER_ID`

**Mini App не открывается**
- Проверьте URL в переменной `MINI_APP_URL`
- Убедитесь, что GitHub Pages настроен и работает
- Проверьте HTTPS (обязательно для продакшена)

### Проблемы с ассистентами

**Ошибка: "Ассистент недоступен"**
- Проверьте правильность ID ассистентов в .env
- Убедитесь, что ассистенты существуют в OpenAI Dashboard
- Проверьте лимиты OpenAI API

**Долгие ответы ассистентов**
- Проверьте инструкции ассистентов (слишком сложные задачи)
- Увеличьте timeout в коде
- Проверьте загрузку OpenAI API

### Проблемы с базой данных

**Файл базы не создается**
- Проверьте права на запись в директорию
- Убедитесь, что SQLite установлен
- Запустите миграции: `python db_migration.py migrate`

**Ошибки миграций**
- Проверьте целостность существующей базы
- Создайте резервную копию
- Удалите базу и пересоздайте с нуля

### Логи и отладка

**Включение отладочного режима**
```python
# В simple_bot.py
logging.getLogger().setLevel(logging.DEBUG)
```

**Просмотр логов на Render**
- Перейдите в Render Dashboard → Logs
- Используйте фильтры для поиска ошибок

**Локальная отладка**
```bash
# Запуск с подробными логами
DEBUG=true python simple_bot.py
```

## 📈 Масштабирование

### При росте количества пользователей

1. **Переход на PostgreSQL**:
   - Обновите `DATABASE_URL` в переменных окружения
   - Адаптируйте SQL запросы при необходимости

2. **Оптимизация производительности**:
   - Добавьте индексы в базу данных
   - Используйте connection pooling
   - Кешируйте часто запрашиваемые данные

3. **Мониторинг**:
   - Настройте алерты на Render.com
   - Используйте внешние сервисы мониторинга
   - Отслеживайте метрики OpenAI API

### Резервное копирование

**Автоматическое резервное копирование**:
```bash
# Создайте cron job для ежедневного бэкапа
0 2 * * * /path/to/backup_script.sh
```

**Ручное резервное копирование**:
```bash
# Экспорт данных пользователей
python user_utils.py export json

# Копия базы данных
cp users.db backups/users_$(date +%Y%m%d).db
```

## 🔐 Безопасность

### Рекомендации по безопасности

1. **Переменные окружения**:
   - Никогда не коммитьте .env файлы
   - Используйте secure environment variables на Render

2. **Валидация данных**:
   - Все данные от Telegram WebApp проходят HMAC валидацию
   - Проверяйте права доступа перед выполнением операций

3. **Регулярные обновления**:
   - Обновляйте зависимости Python
   - Следите за уведомлениями безопасности OpenAI
   - Мониторьте активность ботов

4. **Лимиты запросов**:
   - Настройте rate limiting
   - Мониторьте использование OpenAI API
   - Установите лимиты на количество сообщений

## 📞 Поддержка

При возникновении проблем:

1. Проверьте раздел "Устранение неисправностей"
2. Изучите логи бота и Render.com
3. Проверьте статус сервисов OpenAI и Telegram
4. Создайте issue в GitHub репозитории

---

**Версия руководства**: 2.0.0  
**Дата обновления**: 28 января 2025  
**Поддерживаемые версии**: Python 3.8+, Telegram Bot API 7.0+
