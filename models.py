from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Event:
    id: int
    name: str
    date: str
    time: str
    description: str
    required_people: int
    participants: List[int]  # Все, кто нажал "Буду"
    approved_participants: List[int]  # Те, кого одобрил руководитель

@dataclass
class User:
    id: int
    role: str  # "leader" или "activist"
    name: str

# Хранилище данных (в реальном проекте используйте базу данных)
events: Dict[int, Event] = {}
users: Dict[int, User] = {}


