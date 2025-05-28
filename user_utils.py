#!/usr/bin/env python3
"""
User Management Utilities for Telegram Bot
Версия: 2.0.0
Дата: 2025-01-28

Утилиты для управления пользователями и анализа данных.
"""

import sqlite3
import json
import csv
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@dataclass
class User:
    """Класс для представления пользователя."""
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    status: str
    registered_at: Optional[str]
    last_activity: str
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует пользователя в словарь."""
        return {
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'status': self.status,
            'registered_at': self.registered_at,
            'last_activity': self.last_activity,
            'created_at': self.created_at
        }
    
    def get_display_name(self) -> str:
        """Возвращает отображаемое имя пользователя."""
        if self.first_name:
            name = self.first_name
            if self.last_name:
                name += f" {self.last_name}"
            return name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"User_{self.telegram_id}"
    
    def is_registered(self) -> bool:
        """Проверяет, зарегистрирован ли пользователь."""
        return self.status == 'registered'
    
    def days_since_registration(self) -> Optional[int]:
        """Возвращает количество дней с момента регистрации."""
        if not self.registered_at:
            return None
        
        try:
            reg_date = datetime.fromisoformat(self.registered_at.replace('Z', '+00:00'))
            return (datetime.now() - reg_date).days
        except:
            return None
    
    def days_since_last_activity(self) -> int:
        """Возвращает количество дней с последней активности."""
        try:
            activity_date = datetime.fromisoformat(self.last_activity.replace('Z', '+00:00'))
            return (datetime.now() - activity_date).days
        except:
            return 0

class UserManager:
    """Класс для управления пользователями."""
    
    def __init__(self, db_path: str = 'users.db'):
        self.db_path = db_path
    
    def get_user(self, telegram_id: int) -> Optional[User]:
        """Получает пользователя по Telegram ID."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT telegram_id, username, first_name, last_name, 
                       status, registered_at, last_activity, created_at
                FROM users WHERE telegram_id = ?
            ''', (telegram_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return User(*row)
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя {telegram_id}: {e}")
            return None
    
    def get_all_users(self, status: Optional[str] = None) -> List[User]:
        """Получает всех пользователей с опциональной фильтрацией по статусу."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if status:
                cursor.execute('''
                    SELECT telegram_id, username, first_name, last_name, 
                           status, registered_at, last_activity, created_at
                    FROM users WHERE status = ?
                    ORDER BY created_at DESC
                ''', (status,))
            else:
                cursor.execute('''
                    SELECT telegram_id, username, first_name, last_name, 
                           status, registered_at, last_activity, created_at
                    FROM users ORDER BY created_at DESC
                ''')
            
            users = [User(*row) for row in cursor.fetchall()]
            conn.close()
            
            return users
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}")
            return []
    
    def update_user_status(self, telegram_id: int, new_status: str) -> bool:
        """Обновляет статус пользователя."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET status = ?, last_activity = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            ''', (new_status, telegram_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                logger.info(f"Статус пользователя {telegram_id} изменен на {new_status}")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса пользователя {telegram_id}: {e}")
            return False
    
    def register_user(self, telegram_id: int) -> bool:
        """Регистрирует пользователя."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users 
                SET status = 'registered', 
                    registered_at = CURRENT_TIMESTAMP,
                    last_activity = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            ''', (telegram_id,))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                logger.info(f"Пользователь {telegram_id} зарегистрирован")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя {telegram_id}: {e}")
            return False
    
    def delete_user(self, telegram_id: int) -> bool:
        """Удаляет пользователя из базы данных."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM users WHERE telegram_id = ?', (telegram_id,))
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                logger.info(f"Пользователь {telegram_id} удален")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка при удалении пользователя {telegram_id}: {e}")
            return False
    
    def get_inactive_users(self, days: int = 30) -> List[User]:
        """Получает пользователей, неактивных более указанного количества дней."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT telegram_id, username, first_name, last_name, 
                       status, registered_at, last_activity, created_at
                FROM users 
                WHERE last_activity < ?
                ORDER BY last_activity ASC
            ''', (cutoff_date.isoformat(),))
            
            users = [User(*row) for row in cursor.fetchall()]
            conn.close()
            
            return users
            
        except Exception as e:
            logger.error(f"Ошибка при получении неактивных пользователей: {e}")
            return []
    
    def get_registration_stats(self) -> Dict[str, Any]:
        """Получает статистику регистрации пользователей."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE status = ?', ('registered',))
            registered_users = cursor.fetchone()[0]
            
            # Статистика по дням
            cursor.execute('''
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM users
                WHERE created_at > datetime('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            ''')
            daily_registrations = dict(cursor.fetchall())
            
            # Статистика по регистрации
            cursor.execute('''
                SELECT DATE(registered_at) as date, COUNT(*) as count
                FROM users
                WHERE registered_at > datetime('now', '-30 days')
                GROUP BY DATE(registered_at)
                ORDER BY date DESC
            ''')
            daily_activations = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total_users': total_users,
                'registered_users': registered_users,
                'unregistered_users': total_users - registered_users,
                'registration_rate': round((registered_users / total_users * 100) if total_users > 0 else 0, 2),
                'daily_registrations': daily_registrations,
                'daily_activations': daily_activations
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики регистрации: {e}")
            return {}
    
    def export_users(self, format: str = 'json', status: Optional[str] = None) -> str:
        """Экспортирует пользователей в указанном формате."""
        users = self.get_all_users(status)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format.lower() == 'json':
            filename = f"users_export_{timestamp}.json"
            data = [user.to_dict() for user in users]
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        elif format.lower() == 'csv':
            filename = f"users_export_{timestamp}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Заголовки
                writer.writerow([
                    'telegram_id', 'username', 'first_name', 'last_name',
                    'status', 'registered_at', 'last_activity', 'created_at',
                    'display_name', 'is_registered', 'days_since_registration'
                ])
                
                # Данные
                for user in users:
                    writer.writerow([
                        user.telegram_id, user.username, user.first_name, user.last_name,
                        user.status, user.registered_at, user.last_activity, user.created_at,
                        user.get_display_name(), user.is_registered(), user.days_since_registration()
                    ])
        
        else:
            raise ValueError(f"Неподдерживаемый формат: {format}")
        
        logger.info(f"Экспортировано {len(users)} пользователей в файл {filename}")
        return filename
    
    def cleanup_old_users(self, days: int = 90, dry_run: bool = True) -> int:
        """Удаляет старых неактивных пользователей."""
        inactive_users = self.get_inactive_users(days)
        
        if dry_run:
            logger.info(f"DRY RUN: Будет удалено {len(inactive_users)} пользователей")
            for user in inactive_users[:10]:  # Показываем первых 10
                logger.info(f"  - {user.get_display_name()} (ID: {user.telegram_id}, последняя активность: {user.last_activity})")
            return len(inactive_users)
        
        deleted_count = 0
        for user in inactive_users:
            if self.delete_user(user.telegram_id):
                deleted_count += 1
        
        logger.info(f"Удалено {deleted_count} неактивных пользователей")
        return deleted_count

def main():
    """Главная функция для CLI интерфейса."""
    import sys
    
    manager = UserManager()
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python user_utils.py list [status]          - список пользователей")
        print("  python user_utils.py show <telegram_id>     - информация о пользователе")
        print("  python user_utils.py register <telegram_id> - зарегистрировать пользователя")
        print("  python user_utils.py stats                  - статистика регистрации")
        print("  python user_utils.py export <format>        - экспорт (json/csv)")
        print("  python user_utils.py inactive [days]        - неактивные пользователи")
        print("  python user_utils.py cleanup <days>         - очистка старых пользователей")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        status = sys.argv[2] if len(sys.argv) > 2 else None
        users = manager.get_all_users(status)
        
        print(f"\n{'='*80}")
        print(f"СПИСОК ПОЛЬЗОВАТЕЛЕЙ" + (f" (статус: {status})" if status else ""))
        print(f"{'='*80}")
        print(f"{'ID':<12} {'Имя':<25} {'Username':<20} {'Статус':<12} {'Создан':<12}")
        print(f"{'-'*80}")
        
        for user in users:
            print(f"{user.telegram_id:<12} {user.get_display_name()[:24]:<25} "
                  f"{'@' + user.username if user.username else '-':<20} "
                  f"{user.status:<12} {user.created_at[:10]:<12}")
        
        print(f"\nВсего: {len(users)} пользователей")
        
    elif command == 'show':
        if len(sys.argv) < 3:
            print("Ошибка: укажите Telegram ID пользователя")
            return
        
        telegram_id = int(sys.argv[2])
        user = manager.get_user(telegram_id)
        
        if user:
            print(f"\n{'='*50}")
            print(f"ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ")
            print(f"{'='*50}")
            print(f"Telegram ID: {user.telegram_id}")
            print(f"Имя: {user.get_display_name()}")
            print(f"Username: {'@' + user.username if user.username else 'Не указан'}")
            print(f"Статус: {user.status}")
            print(f"Зарегистрирован: {'Да' if user.is_registered() else 'Нет'}")
            print(f"Дата регистрации: {user.registered_at or 'Не зарегистрирован'}")
            print(f"Последняя активность: {user.last_activity}")
            print(f"Дата создания: {user.created_at}")
            
            if user.is_registered():
                days = user.days_since_registration()
                print(f"Дней с регистрации: {days if days is not None else 'Неизвестно'}")
            
            print(f"Дней с последней активности: {user.days_since_last_activity()}")
        else:
            print(f"Пользователь с ID {telegram_id} не найден")
    
    elif command == 'register':
        if len(sys.argv) < 3:
            print("Ошибка: укажите Telegram ID пользователя")
            return
        
        telegram_id = int(sys.argv[2])
        if manager.register_user(telegram_id):
            print(f"Пользователь {telegram_id} успешно зарегистрирован")
        else:
            print(f"Ошибка при регистрации пользователя {telegram_id}")
    
    elif command == 'stats':
        stats = manager.get_registration_stats()
        
        print(f"\n{'='*50}")
        print(f"СТАТИСТИКА РЕГИСТРАЦИИ")
        print(f"{'='*50}")
        print(f"Всего пользователей: {stats['total_users']}")
        print(f"Зарегистрированных: {stats['registered_users']}")
        print(f"Незарегистрированных: {stats['unregistered_users']}")
        print(f"Коэффициент регистрации: {stats['registration_rate']}%")
        
        print(f"\nРегистрации за последние 30 дней:")
        for date, count in list(stats['daily_registrations'].items())[:10]:
            print(f"  {date}: {count}")
    
    elif command == 'export':
        format_type = sys.argv[2] if len(sys.argv) > 2 else 'json'
        filename = manager.export_users(format_type)
        print(f"Данные экспортированы в файл: {filename}")
    
    elif command == 'inactive':
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        users = manager.get_inactive_users(days)
        
        print(f"\nПользователи, неактивные более {days} дней:")
        for user in users[:20]:  # Показываем первых 20
            print(f"  {user.get_display_name()} (ID: {user.telegram_id}) - {user.last_activity[:10]}")
        
        if len(users) > 20:
            print(f"  ... и еще {len(users) - 20} пользователей")
        
        print(f"\nВсего неактивных: {len(users)}")
    
    elif command == 'cleanup':
        if len(sys.argv) < 3:
            print("Ошибка: укажите количество дней")
            return
        
        days = int(sys.argv[2])
        confirm = input(f"Удалить всех пользователей, неактивных более {days} дней? (y/N): ")
        
        if confirm.lower() == 'y':
            deleted = manager.cleanup_old_users(days, dry_run=False)
            print(f"Удалено {deleted} пользователей")
        else:
            # Показываем, что будет удалено
            count = manager.cleanup_old_users(days, dry_run=True)
            print(f"Отменено. Могло быть удалено: {count} пользователей")
    
    else:
        print(f"Неизвестная команда: {command}")

if __name__ == '__main__':
    main()
