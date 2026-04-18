from __future__ import annotations

from yandex_messenger_bot.fsm.storage.base import BaseStorage, StorageKey
from yandex_messenger_bot.fsm.storage.memory import MemoryStorage

__all__ = [
    "BaseStorage",
    "MemoryStorage",
    "StorageKey",
]
