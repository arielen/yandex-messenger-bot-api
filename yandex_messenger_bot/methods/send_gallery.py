from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from yandex_messenger_bot.methods.base import RecipientMixin, YaBotMethod
from yandex_messenger_bot.types.base import YaBotObject
from yandex_messenger_bot.types.button import SuggestButtons
from yandex_messenger_bot.types.input_file import InputFile


class SendGalleryResult(YaBotObject):
    message_id: int


class SendGallery(RecipientMixin, YaBotMethod[SendGalleryResult]):
    """Send a gallery of images (up to 10) via multipart upload."""

    __api_path__: ClassVar[str] = "/bot/v1/messages/sendGallery/"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = SendGalleryResult
    __multipart__: ClassVar[bool] = True

    images: list[InputFile] = Field(exclude=True)
    text: str | None = None
    thread_id: int | None = None
    suggest_buttons: SuggestButtons | None = None
