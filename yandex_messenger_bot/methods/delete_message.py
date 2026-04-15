from __future__ import annotations

from typing import ClassVar

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.base import YaBotObject


class DeleteMessageResult(YaBotObject):
    ok: bool = True


class DeleteMessage(YaBotMethod[DeleteMessageResult]):
    """Delete a message from a chat."""

    __api_path__: ClassVar[str] = "/bot/v1/messages/delete/"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = DeleteMessageResult

    chat_id: str
    message_id: int
