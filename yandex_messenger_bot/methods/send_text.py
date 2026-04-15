from __future__ import annotations

from typing import Any, ClassVar

from yandex_messenger_bot.methods.base import RecipientMixin, YaBotMethod
from yandex_messenger_bot.types.base import YaBotObject
from yandex_messenger_bot.types.button import SuggestButtons


class SendTextResult(YaBotObject):
    message_id: int


class SendText(RecipientMixin, YaBotMethod[SendTextResult]):
    """Send a text message to a chat or user."""

    __api_path__: ClassVar[str] = "/bot/v1/messages/sendText/"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SendTextResult

    text: str
    payload_id: str | None = None
    reply_message_id: int | None = None
    disable_notification: bool = False
    important: bool = False
    disable_web_page_preview: bool = False
    thread_id: int | None = None
    inline_keyboard: list[dict[str, Any]] | None = None
    suggest_buttons: SuggestButtons | None = None
