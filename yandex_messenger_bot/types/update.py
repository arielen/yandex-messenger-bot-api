from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from yandex_messenger_bot.types.base import YaBotObject
from yandex_messenger_bot.types.bot_request import BotRequest
from yandex_messenger_bot.types.chat import Chat
from yandex_messenger_bot.types.file import Document, Image, Sticker
from yandex_messenger_bot.types.forward import ForwardedMessage
from yandex_messenger_bot.types.user import User


class Update(YaBotObject):
    """A single update from Yandex Messenger Bot API.

    This is a flat object — all fields come at the same level.
    An update may contain text, document, images, sticker,
    bot_request, forwarded_messages, etc. simultaneously.
    """

    update_id: int
    message_id: int
    timestamp: int
    chat: Chat
    from_user: User | None = Field(None, alias="from")
    text: str | None = None
    thread_id: int | None = None

    # Attachments (not mutually exclusive)
    forwarded_messages: list[ForwardedMessage] | None = None
    sticker: Sticker | None = None
    image: Image | None = None
    images: list[list[Image]] | None = None
    document: Document | None = None
    file: Document | None = None

    # Bot request (from button directives)
    bot_request: BotRequest | None = None

    # ------------------------------------------------------------------
    # Defensive validators: the Yandex docs are inconsistent about the
    # wire format of some fields.  These validators normalise both known
    # shapes so that parsing never fails regardless of what the API sends.
    # See docs/api-inconsistencies.md for details.
    # ------------------------------------------------------------------

    @field_validator("images", mode="before")
    @classmethod
    def _normalize_images(cls, v: Any) -> Any:
        """Accept both Image[] (flat) and Image[][] (nested) from the API.

        The data-types page documents ``Image[]``, but the polling response
        examples show ``Image[][]`` (outer = images, inner = size variants).
        """
        if v and isinstance(v, list) and v and isinstance(v[0], dict):
            return [v]  # flat → wrap in outer list
        return v

    @field_validator("forwarded_messages", mode="before")
    @classmethod
    def _normalize_forwarded(cls, v: Any) -> Any:
        """Accept both a single object and an array."""
        if isinstance(v, dict):
            return [v]
        return v
