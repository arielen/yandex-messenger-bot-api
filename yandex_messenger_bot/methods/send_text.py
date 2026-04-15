from __future__ import annotations

from typing import Any, ClassVar, Self

from pydantic import model_validator

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.base import YaBotObject
from yandex_messenger_bot.types.button import SuggestButtons


class SendTextResult(YaBotObject):
    message_id: int


class SendText(YaBotMethod[SendTextResult]):
    """Send a text message to a chat or user."""

    __api_path__: ClassVar[str] = "/bot/v1/messages/sendText/"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SendTextResult

    chat_id: str | None = None
    login: str | None = None
    text: str
    payload_id: str | None = None
    reply_message_id: int | None = None
    disable_notification: bool = False
    important: bool = False
    disable_web_page_preview: bool = False
    thread_id: int | None = None
    inline_keyboard: list[dict[str, Any]] | None = None
    suggest_buttons: SuggestButtons | None = None

    @model_validator(mode="after")
    def _check_recipient(self) -> Self:
        if not self.chat_id and not self.login:
            raise ValueError("Either 'chat_id' or 'login' must be provided")
        if self.chat_id and self.login:
            raise ValueError("Provide either 'chat_id' or 'login', not both")
        return self
