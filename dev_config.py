#!/usr/bin/env python3
"""
Development Configuration and Setup Script
Версия: 2.0.0
Дата: 2025-01-28

Скрипт для настройки среды разработки и создания тестовых данных.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import secrets
import string

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DevConfig:
    """Класс для управления конфигурацией разработки."""
    
    def __init__(self):
        self.config_file = 'dev_config.json'
        self.env_file = '.env'
        self.test_db = 'test_users.db'
        
    def create_env_file(self, force: bool = False) -> bool:
        """Создает файл .env с примером конфигурации."""
        if os.path.exists(self.env_file) and not force:
            logger.info(f"Файл {self.env_file} уже существует")
            return False
        
        env_content = f"""# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# OpenAI Assistant IDs (создайте их в OpenAI Dashboard)
OPENAI_ASSISTANT_ID_MARKET=your_market_analysis_assistant_id
OPENAI_ASSISTANT_ID_FOUNDER=your_founder_ideas_assistant_id
OPENAI_ASSISTANT_ID_BUSINESS=your_business_model_assistant_id
OPENAI_ASSISTANT_ID_ADAPTER=your_case_adapter_assistant_id

# Development Settings
DEBUG=true
LOG_LEVEL=INFO

# Mini App URL (замените на ваш GitHub Pages URL)
MINI_APP_URL=https://yourusername.github.io/your-repo-name/

# Database Configuration
DATABASE_URL=sqlite:///users.db

# Auto-generated on {datetime.now().isoformat()}
"""
        
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
            
            logger.info(f"Создан файл {self.env_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при создании {self.env_file}: {e}")
            return False
    
    def create_config_file(self) -> bool:
        """Создает файл конфигурации для разработки."""
        config = {
            "app": {
                "name": "Telegram Business Assistant Bot",
                "version": "2.0.0",
                "description": "Bot with business assistants and user registration system"
            },
            "development": {
                "debug": True,
                "auto_reload": True,
                "test_mode": True,
                "mock_telegram_data": True,
                "skip_openai_validation": False
            },
            "database": {
                "test_db_path": self.test_db,
                "auto_migrate": True,
                "backup_on_startup": True,
                "create_test_data": True
            },
            "telegram": {
                "webhook_mode": False,
                "polling_timeout": 30,
                "allowed_updates": ["message", "callback_query", "inline_query"],
                "rate_limit": {
                    "messages_per_second": 30,
                    "messages_per_minute": 100
                }
            },
            "mini_app": {
                "local_url": "http://localhost:8000",
                "github_pages_url": "https://ai4business-ai.github.io/front-bot-repo/",
                "enable_cors": True,
                "allow_http": True  # Только для тестирования
            },
            "registration": {
                "require_validation": True,
                "auto_register_test_users": True,
                "test_telegram_ids": [123456789, 987654321],
                "registration_rate_limit": {
                    "max_per_hour": 100,
                    "max_per_day": 1000
                }
            },
            "logging": {
                "level": "INFO",
                "file": "bot_dev.log",
                "max_file_size": "10MB",
                "backup_count": 5,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "testing": {
                "create_mock_users": True,
                "mock_user_count": 50,
                "simulate_activity": True,
                "test_all_assistants": True
            }
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Создан файл конфигурации {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при создании конфигурации: {e}")
            return False
    
    def load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из файла."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Файл конфигурации {self.config_file} не найден")
            return {}
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {e}")
            return {}
    
    def create_test_database(self) -> bool:
        """Создает тестовую базу данных с примерными данными."""
        try:
            # Удаляем существующую тестовую БД
            if os.path.exists(self.test_db):
                os.remove(self.test_db)
            
            # Создаем новую БД
            conn = sqlite3.connect(self.test_db)
            cursor = conn.cursor()
            
            # Создаем таблицу пользователей
            cursor.execute('''
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
            ''')
            
            # Создаем таблицу истории миграций
            cursor.execute('''
            CREATE TABLE migration_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT TRUE
            )
            ''')
            
            # Добавляем тестовых пользователей
            test_users = self.generate_test_users(50)
            
            for user in test_users:
                cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name, last_name, 
                                 status, registered_at, last_activity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', user)
            
            # Добавляем запись о миграции
            cursor.execute('''
            INSERT INTO migration_history (version, description)
            VALUES ('2.0.0', 'Создание тестовой базы данных')
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info(f"Создана тестовая база данных {self.test_db} с {len(test_users)} пользователями")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при создании тестовой БД: {e}")
            return False
    
    def generate_test_users(self, count: int = 50) -> List[tuple]:
        """Генерирует тестовых пользователей."""
        users = []
        base_time = datetime.now()
        
        # Список примерных имен
        first_names = [
            "Александр", "Мария", "Дмитрий", "Анна", "Сергей", "Елена", "Андрей", "Ольга",
            "Владимир", "Татьяна", "Алексей", "Наталья", "Евгений", "Ирина", "Николай",
            "Светлана", "Денис", "Юлия", "Артем", "Екатерина", "Максим", "Виктория"
        ]
        
        last_names = [
            "Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", "Попов", "Васильев",
            "Соколов", "Михайлов", "Новиков", "Федоров", "Морозов", "Волков", "Алексеев",
            "Лебедев", "Семенов", "Егоров", "Павлов", "Козлов", "Степанов", "Николаев"
        ]
        
        for i in range(count):
            telegram_id = 1000000000 + i
            
            # Случайно выбираем имя и фамилию
            first_name = secrets.choice(first_names)
            last_name = secrets.choice(last_names)
            
            # Генерируем username (не для всех)
            username = None
            if secrets.randbelow(3) == 0:  # 33% вероятность
                username = f"{first_name.lower()}{secrets.randbelow(1000)}"
            
            # Определяем статус (70% зарегистрированных)
            status = 'registered' if secrets.randbelow(10) < 7 else 'user'
            
            # Время создания (в течение последних 30 дней)
            days_ago = secrets.randbelow(30)
            created_at = (base_time - timedelta(days=days_ago)).isoformat()
            
            # Время регистрации (если зарегистрирован)
            registered_at = None
            if status == 'registered':
                reg_days_ago = secrets.randbelow(days_ago + 1)
                registered_at = (base_time - timedelta(days=reg_days_ago)).isoformat()
            
            # Последняя активность (в течение последних 7 дней для активных)
            activity_days_ago = secrets.randbelow(7) if secrets.randbelow(5) < 4 else secrets.randbelow(30)
            last_activity = (base_time - timedelta(days=activity_days_ago)).isoformat()
            
            users.append((
                telegram_id, username, first_name, last_name,
                status, registered_at, last_activity, created_at
            ))
        
        return users
    
    def create_development_scripts(self) -> bool:
        """Создает полезные скрипты для разработки."""
        scripts = {
            "run_dev.py": '''#!/usr/bin/env python3
"""Скрипт для запуска бота в режиме разработки."""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Устанавливаем переменные окружения для разработки
    os.environ['DEBUG'] = 'true'
    os.environ['DATABASE_URL'] = 'sqlite:///test_users.db'
    
    # Запускаем бота
    try:
        subprocess.run([sys.executable, 'simple_bot.py'], check=True)
    except KeyboardInterrupt:
        print("\\nЗавершение работы...")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    main()
''',
            
            "test_mini_app.py": '''#!/usr/bin/env python3
"""Локальный сервер для тестирования Mini App."""

import http.server
import socketserver
import webbrowser
import os

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    PORT = 8000
    
    with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
        print(f"Сервер запущен на http://localhost:{PORT}")
        print("Для тестирования Mini App откройте браузер...")
        
        webbrowser.open(f'http://localhost:{PORT}')
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\nСервер остановлен")

if __name__ == '__main__':
    main()
''',
            
            "check_config.py": '''#!/usr/bin/env python3
"""Проверка конфигурации проекта."""

import os
import json
from dotenv import load_dotenv

def check_env_variables():
    """Проверяет переменные окружения."""
    load_dotenv()
    
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'OPENAI_API_KEY',
        'OPENAI_ASSISTANT_ID_MARKET',
        'OPENAI_ASSISTANT_ID_FOUNDER',
        'OPENAI_ASSISTANT_ID_BUSINESS',
        'OPENAI_ASSISTANT_ID_ADAPTER'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Отсутствуют переменные окружения:")
        for var in missing_vars:
            print(f"  - {var}")
        return False
    else:
        print("✅ Все переменные окружения настроены")
        return True

def check_files():
    """Проверяет наличие необходимых файлов."""
    required_files = [
        'simple_bot.py',
        'index.html',
        'styles.css',
        'app.js',
        'version.js',
        'requirements.txt'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Отсутствуют файлы:")
        for file in missing_files:
            print(f"  - {file}")
        return False
    else:
        print("✅ Все необходимые файлы присутствуют")
        return True

def main():
    print("🔍 Проверка конфигурации проекта...")
    print("=" * 50)
    
    env_ok = check_env_variables()
    files_ok = check_files()
    
    print("=" * 50)
    if env_ok and files_ok:
        print("✅ Проект готов к запуску!")
    else:
        print("❌ Исправьте ошибки перед запуском")

if __name__ == '__main__':
    main()
'''
        }
        
        try:
            for filename, content in scripts.items():
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Делаем скрипты исполняемыми в Unix-системах
                if hasattr(os, 'chmod'):
                    os.chmod(filename, 0o755)
            
            logger.info(f"Созданы скрипты разработки: {', '.join(scripts.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при создании скриптов: {e}")
            return False
    
    def setup_development_environment(self) -> bool:
        """Настраивает полную среду разработки."""
        logger.info("Настройка среды разработки...")
        
        success = True
        
        # Создаем .env файл
        if not os.path.exists(self.env_file):
            success &= self.create_env_file()
        
        # Создаем файл конфигурации
        success &= self.create_config_file()
        
        # Создаем тестовую базу данных
        success &= self.create_test_database()
        
        # Создаем скрипты разработки
        success &= self.create_development_scripts()
        
        # Создаем директории для логов
        os.makedirs('logs', exist_ok=True)
        os.makedirs('backups', exist_ok=True)
        
        if success:
            logger.info("✅ Среда разработки успешно настроена!")
            print("\n" + "="*60)
            print("🚀 СРЕДА РАЗРАБОТКИ ГОТОВА!")
            print("="*60)
            print("📁 Созданные файлы:")
            print("  • dev_config.json - конфигурация разработки")
            print("  • .env - переменные окружения (настройте токены)")
            print("  • test_users.db - тестовая база данных")
            print("  • run_dev.py - запуск в режиме разработки")
            print("  • test_mini_app.py - локальный сервер для Mini App")
            print("  • check_config.py - проверка конфигурации")
            print("\n📝 Следующие шаги:")
            print("  1. Отредактируйте .env файл с вашими токенами")
            print("  2. Запустите: python check_config.py")
            print("  3. Запустите: python run_dev.py")
            print("  4. Для тестирования Mini App: python test_mini_app.py")
            print("="*60)
        else:
            logger.error("❌ Ошибка при настройке среды разработки")
        
        return success

def main():
    """Главная функция CLI."""
    import sys
    
    config = DevConfig()
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python dev_config.py setup     - полная настройка среды разработки")
        print("  python dev_config.py env       - создать .env файл")
        print("  python dev_config.py config    - создать конфигурацию")
        print("  python dev_config.py testdb    - создать тестовую БД")
        print("  python dev_config.py scripts   - создать скрипты разработки")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'setup':
        config.setup_development_environment()
    elif command == 'env':
        config.create_env_file(force=True)
    elif command == 'config':
        config.create_config_file()
    elif command == 'testdb':
        config.create_test_database()
    elif command == 'scripts':
        config.create_development_scripts()
    else:
        print(f"Неизвестная команда: {command}")

if __name__ == '__main__':
    main()
