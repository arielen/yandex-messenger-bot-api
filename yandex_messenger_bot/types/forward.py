from __future__ import annotations

from pydantic import Field

from yandex_messenger_bot.types.base import YaBotObject
from yandex_messenger_bot.types.chat import Chat
from yandex_messenger_bot.types.user import User


class ForwardedMessage(YaBotObject):
    """A single forwarded message — a subset of Update fields."""

    message_id: int | None = None
    timestamp: int | None = None
    chat: Chat | None = None
    from_user: User | None = Field(None, alias="from")
    text: str | None = None


# Keep the old name as an alias for backward compatibility
ForwardInfo = ForwardedMessage
