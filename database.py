import sqlite3
import aiosqlite
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Создаем таблицу пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    role TEXT NOT NULL,
                    name TEXT NOT NULL,
                    full_name TEXT,
                    user_group TEXT,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Создаем таблицу мероприятий
            await db.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    description TEXT NOT NULL,
                    required_people INTEGER NOT NULL,
                    participants TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Создаем таблицу ответов на мероприятия
            await db.execute('''
                CREATE TABLE IF NOT EXISTS event_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    status TEXT NOT NULL, -- 'confirmed', 'declined', 'pending', 'maybe'
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            await db.commit()

    async def add_user(self, user_id: int, role: str, name: str,
                       full_name: Optional[str] = None,
                       user_group: Optional[str] = None,
                       username: Optional[str] = None) -> bool:
        """Добавление пользователя в БД"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO users (id, role, name, full_name, user_group, username)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, role, name, full_name, user_group, username))
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при добавлении пользователя: {e}")
            return False

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM users WHERE id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'role': row[1],
                        'name': row[2],
                        'full_name': row[3],
                        'group': row[4],
                        'username': row[5],
                        'created_at': row[6]
                    }
                return None

    async def update_user(self, user_id: int, **kwargs) -> bool:
        """Обновление данных пользователя"""
        if not kwargs:
            return False

        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ['full_name', 'user_group', 'username']:
                fields.append(f"{key} = ?")
                values.append(value)

        if not fields:
            return False

        values.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(query, values)
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при обновлении пользователя: {e}")
            return False

    async def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('DELETE FROM users WHERE id = ?', (user_id,))
                await db.execute('DELETE FROM event_responses WHERE user_id = ?', (user_id,))
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при удалении пользователя: {e}")
            return False

    async def get_all_activists(self) -> List[Dict]:
        """Получение всех активистов"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM users WHERE role = "activist" ORDER BY created_at DESC') as cursor:
                rows = await cursor.fetchall()
                activists = []
                for row in rows:
                    activists.append({
                        'id': row[0],
                        'role': row[1],
                        'name': row[2],
                        'full_name': row[3],
                        'group': row[4],
                        'username': row[5],
                        'created_at': row[6]
                    })
                return activists

    async def add_event(self, name: str, date: str, time: str,
                        description: str, required_people: int) -> int:
        """Добавление мероприятия"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute('''
                    INSERT INTO events (name, date, time, description, required_people)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, date, time, description, required_people))
                await db.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Ошибка при добавлении мероприятия: {e}")
            return -1

    async def get_event(self, event_id: int) -> Optional[Dict]:
        """Получение мероприятия по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM events WHERE id = ?', (event_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'date': row[2],
                        'time': row[3],
                        'description': row[4],
                        'required_people': row[5],
                        'participants': json.loads(row[6]) if row[6] else [],
                        'created_at': row[7]
                    }
                return None

    async def get_all_events(self) -> List[Dict]:
        """Получение всех мероприятий"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM events ORDER BY created_at DESC') as cursor:
                rows = await cursor.fetchall()
                events = []
                for row in rows:
                    events.append({
                        'id': row[0],
                        'name': row[1],
                        'date': row[2],
                        'time': row[3],
                        'description': row[4],
                        'required_people': row[5],
                        'participants': json.loads(row[6]) if row[6] else [],
                        'created_at': row[7]
                    })
                return events

    async def update_event_participants(self, event_id: int, participants: List[int]) -> bool:
        """Обновление списка участников мероприятия"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    UPDATE events 
                    SET participants = ? 
                    WHERE id = ?
                ''', (json.dumps(participants), event_id))
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при обновлении участников мероприятия: {e}")
            return False

    async def add_event_response(self, event_id: int, user_id: int,
                                 status: str, reason: Optional[str] = None) -> bool:
        """Добавление ответа на мероприятие"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Удаляем предыдущий ответ пользователя на это мероприятие
                await db.execute('''
                    DELETE FROM event_responses 
                    WHERE event_id = ? AND user_id = ?
                ''', (event_id, user_id))

                # Добавляем новый ответ
                await db.execute('''
                    INSERT INTO event_responses (event_id, user_id, status, reason)
                    VALUES (?, ?, ?, ?)
                ''', (event_id, user_id, status, reason))

                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка при добавлении ответа на мероприятие: {e}")
            return False

    async def get_event_responses(self, event_id: int) -> List[Dict]:
        """Получение всех ответов на мероприятие"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('''
                SELECT er.*, u.full_name, u.user_group, u.username
                FROM event_responses er
                LEFT JOIN users u ON er.user_id = u.id
                WHERE er.event_id = ?
                ORDER BY er.created_at DESC
            ''', (event_id,)) as cursor:
                rows = await cursor.fetchall()
                responses = []
                for row in rows:
                    responses.append({
                        'id': row[0],
                        'event_id': row[1],
                        'user_id': row[2],
                        'status': row[3],
                        'reason': row[4],
                        'created_at': row[5],
                        'full_name': row[6],
                        'group': row[7],
                        'username': row[8]
                    })
                return responses


# Создаем глобальный экземпляр базы данных
db = Database()