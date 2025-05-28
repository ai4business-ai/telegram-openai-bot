#!/usr/bin/env python3
"""
Database Migration Script for Telegram Bot
Версия: 2.0.0
Дата: 2025-01-28

Этот скрипт управляет миграциями базы данных для системы регистрации пользователей.
"""

import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Класс для управления миграциями базы данных."""
    
    def __init__(self, db_path: str = 'users.db'):
        self.db_path = db_path
        self.migrations = self._get_migrations()
    
    def _get_migrations(self) -> List[Dict[str, Any]]:
        """Возвращает список всех миграций."""
        return [
            {
                'version': '1.0.0',
                'description': 'Создание таблицы пользователей',
                'sql': '''
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    status TEXT DEFAULT 'user',
                    registered_at TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                ''',
                'rollback': 'DROP TABLE IF EXISTS users;'
            },
            {
                'version': '1.1.0',
                'description': 'Создание таблицы версий миграций',
                'sql': '''
                CREATE TABLE IF NOT EXISTS migration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    description TEXT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    success BOOLEAN DEFAULT TRUE
                );
                ''',
                'rollback': 'DROP TABLE IF EXISTS migration_history;'
            },
            {
                'version': '2.0.0',
                'description': 'Добавление индексов для производительности',
                'sql': '''
                CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
                CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity);
                CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
                ''',
                'rollback': '''
                DROP INDEX IF EXISTS idx_users_status;
                DROP INDEX IF EXISTS idx_users_last_activity;
                DROP INDEX IF EXISTS idx_users_created_at;
                '''
            },
            {
                'version': '2.1.0',
                'description': 'Добавление таблицы сессий пользователей',
                'sql': '''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    assistant_type TEXT,
                    thread_id TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    message_count INTEGER DEFAULT 0,
                    FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_telegram_id ON user_sessions(telegram_id);
                CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON user_sessions(started_at);
                ''',
                'rollback': 'DROP TABLE IF EXISTS user_sessions;'
            }
        ]
    
    def get_current_version(self) -> str:
        """Получает текущую версию базы данных."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, существует ли таблица migration_history
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='migration_history'
            ''')
            
            if not cursor.fetchone():
                conn.close()
                return '0.0.0'
            
            # Получаем последнюю примененную миграцию
            cursor.execute('''
                SELECT version FROM migration_history 
                WHERE success = TRUE 
                ORDER BY applied_at DESC 
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else '0.0.0'
            
        except Exception as e:
            logger.error(f"Ошибка при получении версии БД: {e}")
            return '0.0.0'
    
    def record_migration(self, version: str, description: str, success: bool = True):
        """Записывает информацию о миграции в историю."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO migration_history (version, description, success)
                VALUES (?, ?, ?)
            ''', (version, description, success))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Ошибка при записи миграции: {e}")
    
    def apply_migration(self, migration: Dict[str, Any]) -> bool:
        """Применяет одну миграцию."""
        try:
            logger.info(f"Применение миграции {migration['version']}: {migration['description']}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Выполняем SQL команды
            for sql_command in migration['sql'].split(';'):
                sql_command = sql_command.strip()
                if sql_command:
                    cursor.execute(sql_command)
            
            conn.commit()
            conn.close()
            
            # Записываем успешную миграцию
            self.record_migration(migration['version'], migration['description'], True)
            
            logger.info(f"Миграция {migration['version']} успешно применена")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при применении миграции {migration['version']}: {e}")
            self.record_migration(migration['version'], migration['description'], False)
            return False
    
    def rollback_migration(self, migration: Dict[str, Any]) -> bool:
        """Откатывает миграцию."""
        try:
            logger.info(f"Откат миграции {migration['version']}: {migration['description']}")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Выполняем команды отката
            for sql_command in migration['rollback'].split(';'):
                sql_command = sql_command.strip()
                if sql_command:
                    cursor.execute(sql_command)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Откат миграции {migration['version']} успешно выполнен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при откате миграции {migration['version']}: {e}")
            return False
    
    def migrate_up(self, target_version: str = None) -> bool:
        """Применяет миграции до указанной версии."""
        current_version = self.get_current_version()
        logger.info(f"Текущая версия БД: {current_version}")
        
        if target_version is None:
            target_version = self.migrations[-1]['version']
        
        logger.info(f"Целевая версия: {target_version}")
        
        # Находим миграции для применения
        migrations_to_apply = []
        for migration in self.migrations:
            if self._version_greater(migration['version'], current_version):
                migrations_to_apply.append(migration)
                if migration['version'] == target_version:
                    break
        
        if not migrations_to_apply:
            logger.info("Нет миграций для применения")
            return True
        
        # Применяем миграции
        success = True
        for migration in migrations_to_apply:
            if not self.apply_migration(migration):
                success = False
                break
        
        if success:
            logger.info("Все миграции успешно применены")
        else:
            logger.error("Ошибка при применении миграций")
        
        return success
    
    def migrate_down(self, target_version: str) -> bool:
        """Откатывает миграции до указанной версии."""
        current_version = self.get_current_version()
        logger.info(f"Текущая версия БД: {current_version}")
        logger.info(f"Целевая версия для отката: {target_version}")
        
        # Находим миграции для отката
        migrations_to_rollback = []
        for migration in reversed(self.migrations):
            if self._version_greater(migration['version'], target_version) and \
               not self._version_greater(migration['version'], current_version):
                migrations_to_rollback.append(migration)
        
        if not migrations_to_rollback:
            logger.info("Нет миграций для отката")
            return True
        
        # Откатываем миграции
        success = True
        for migration in migrations_to_rollback:
            if not self.rollback_migration(migration):
                success = False
                break
        
        if success:
            logger.info("Откат миграций успешно выполнен")
        else:
            logger.error("Ошибка при откате миграций")
        
        return success
    
    def _version_greater(self, version1: str, version2: str) -> bool:
        """Сравнивает версии. Возвращает True, если version1 > version2."""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        # Дополняем до одинаковой длины
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        return v1_parts > v2_parts
    
    def show_status(self):
        """Показывает статус базы данных и миграций."""
        current_version = self.get_current_version()
        latest_version = self.migrations[-1]['version']
        
        print(f"\n{'='*50}")
        print(f"СТАТУС БАЗЫ ДАННЫХ")
        print(f"{'='*50}")
        print(f"Файл БД: {self.db_path}")
        print(f"Существует: {'Да' if os.path.exists(self.db_path) else 'Нет'}")
        print(f"Текущая версия: {current_version}")
        print(f"Последняя версия: {latest_version}")
        print(f"Требуется обновление: {'Да' if self._version_greater(latest_version, current_version) else 'Нет'}")
        
        # Показываем доступные миграции
        print(f"\nДОСТУПНЫЕ МИГРАЦИИ:")
        for migration in self.migrations:
            status = "✅" if not self._version_greater(migration['version'], current_version) else "⏳"
            print(f"{status} {migration['version']}: {migration['description']}")
        
        print(f"{'='*50}\n")
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Возвращает статистику пользователей."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Общее количество пользователей
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            # Количество зарегистрированных пользователей
            cursor.execute('SELECT COUNT(*) FROM users WHERE status = ?', ('registered',))
            registered_users = cursor.fetchone()[0]
            
            # Количество пользователей за последние 24 часа
            cursor.execute('''
                SELECT COUNT(*) FROM users 
                WHERE created_at > datetime('now', '-1 day')
            ''')
            recent_users = cursor.fetchone()[0]
            
            # Количество активных пользователей за последние 24 часа
            cursor.execute('''
                SELECT COUNT(*) FROM users 
                WHERE last_activity > datetime('now', '-1 day')
            ''')
            active_users = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_users': total_users,
                'registered_users': registered_users,
                'unregistered_users': total_users - registered_users,
                'recent_users_24h': recent_users,
                'active_users_24h': active_users,
                'registration_rate': round((registered_users / total_users * 100) if total_users > 0 else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {}

def main():
    """Главная функция для CLI интерфейса."""
    import sys
    
    migrator = DatabaseMigrator()
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python db_migration.py status          - показать статус БД")
        print("  python db_migration.py migrate         - применить все миграции")
        print("  python db_migration.py migrate 2.0.0   - применить миграции до версии 2.0.0")
        print("  python db_migration.py rollback 1.0.0  - откатить до версии 1.0.0")
        print("  python db_migration.py stats           - показать статистику пользователей")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'status':
        migrator.show_status()
        
    elif command == 'migrate':
        target_version = sys.argv[2] if len(sys.argv) > 2 else None
        migrator.migrate_up(target_version)
        
    elif command == 'rollback':
        if len(sys.argv) < 3:
            print("Ошибка: укажите целевую версию для отката")
            return
        target_version = sys.argv[2]
        migrator.migrate_down(target_version)
        
    elif command == 'stats':
        stats = migrator.get_user_stats()
        print(f"\n{'='*50}")
        print(f"СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ")
        print(f"{'='*50}")
        print(f"Всего пользователей: {stats.get('total_users', 0)}")
        print(f"Зарегистрированных: {stats.get('registered_users', 0)}")
        print(f"Незарегистрированных: {stats.get('unregistered_users', 0)}")
        print(f"Коэффициент регистрации: {stats.get('registration_rate', 0)}%")
        print(f"Новых за 24ч: {stats.get('recent_users_24h', 0)}")
        print(f"Активных за 24ч: {stats.get('active_users_24h', 0)}")
        print(f"{'='*50}\n")
        
    else:
        print(f"Неизвестная команда: {command}")

if __name__ == '__main__':
    main()
