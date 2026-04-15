from __future__ import annotations

from enum import StrEnum


class FSMStrategy(StrEnum):
    USER_IN_CHAT = "user_in_chat"  # default: state per user per chat
    CHAT = "chat"  # state per chat (shared)
    GLOBAL_USER = "global_user"  # state per user globally
