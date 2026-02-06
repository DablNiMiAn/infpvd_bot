from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Event:
    id: int
    name: str
    date: str
    time: str
    description: str
    required_people: int
    participants: List[int]  # Список ID активистов, которые согласились

@dataclass
class User:
    id: int
    role: str  # "leader" или "activist"
    name: str
    full_name: Optional[str] = None  # ФИО
    group: Optional[str] = None      # Учебная группа
    username: Optional[str] = None   # @username

# Хранилище данных (в реальном проекте используйте базу данных)
events: Dict[int, Event] = {}
users: Dict[int, User] = {}