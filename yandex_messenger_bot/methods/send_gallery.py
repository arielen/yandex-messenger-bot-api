from __future__ import annotations

from typing import ClassVar, Self

from pydantic import Field, model_validator

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.base import YaBotObject
from yandex_messenger_bot.types.button import SuggestButtons
from yandex_messenger_bot.types.input_file import InputFile


class SendGalleryResult(YaBotObject):
    message_id: int


class SendGallery(YaBotMethod[SendGalleryResult]):
    """Send a gallery of images (up to 10) via multipart upload."""

    __api_path__: ClassVar[str] = "/bot/v1/messages/sendGallery/"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SendGalleryResult
    __multipart__: ClassVar[bool] = True

    chat_id: str | None = None
    login: str | None = None
    images: list[InputFile] = Field(exclude=True)
    text: str | None = None
    thread_id: int | None = None
    suggest_buttons: SuggestButtons | None = None

    @model_validator(mode="after")
    def _check_recipient(self) -> Self:
        if not self.chat_id and not self.login:
            raise ValueError("Either 'chat_id' or 'login' must be provided")
        if self.chat_id and self.login:
            raise ValueError("Provide either 'chat_id' or 'login', not both")
        return self
