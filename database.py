#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с базой данных SQLite
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с SQLite базой данных"""
    
    def __init__(self, db_path: str = "/app/backend/bot_users.db"):
        """Инициализация базы данных"""
        self.db_path = db_path
    
    def init_db(self):
        """Создание таблицы пользователей"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создаем таблицу пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("База данных инициализирована успешно")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
    
    def add_user(self, user_id: int, username: str):
        """Добавление или обновление пользователя"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем, существует ли пользователь
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Обновляем время последней активности
                cursor.execute(
                    "UPDATE users SET last_active = CURRENT_TIMESTAMP, username = ? WHERE user_id = ?",
                    (username, user_id)
                )
            else:
                # Добавляем нового пользователя
                cursor.execute(
                    "INSERT INTO users (user_id, username) VALUES (?, ?)",
                    (user_id, username)
                )
            
            conn.commit()
            conn.close()
            logger.info(f"Пользователь {user_id} ({username}) добавлен/обновлен")
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя: {e}")
    
    def get_total_users(self) -> int:
        """Получение общего количества пользователей"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return 0
