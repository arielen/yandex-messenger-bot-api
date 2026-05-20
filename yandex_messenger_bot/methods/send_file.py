from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from yandex_messenger_bot.methods.base import RecipientMixin, YaBotMethod
from yandex_messenger_bot.types.base import YaBotObject
from yandex_messenger_bot.types.button import SuggestButtons
from yandex_messenger_bot.types.input_file import InputFile


class SendFileResult(YaBotObject):
    message_id: int


class SendFile(RecipientMixin, YaBotMethod[SendFileResult]):
    """Send a file (document) to a chat or user via multipart upload."""

    __api_path__: ClassVar[str] = "/bot/v1/messages/sendFile/"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SendFileResult
    __multipart__: ClassVar[bool] = True

    document: InputFile = Field(exclude=True)
    thread_id: int | None = None
    suggest_buttons: SuggestButtons | None = None
