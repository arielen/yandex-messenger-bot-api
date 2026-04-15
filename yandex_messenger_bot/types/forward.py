from __future__ import annotations

from pydantic import Field

from yandex_messenger_bot.types.base import YaBotObject
from yandex_messenger_bot.types.chat import Chat
from yandex_messenger_bot.types.user import User


class ForwardInfo(YaBotObject):
    """Information about a forwarded message."""

    from_user: User | None = Field(None, alias="from")
    chat: Chat | None = None
    message_id: int | None = None
