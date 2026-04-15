from __future__ import annotations

from pydantic import Field

from yandex_messenger_bot.types.base import YaBotObject
from yandex_messenger_bot.types.bot_request import BotRequest
from yandex_messenger_bot.types.chat import Chat
from yandex_messenger_bot.types.file import Document, Image, Sticker
from yandex_messenger_bot.types.forward import ForwardInfo
from yandex_messenger_bot.types.user import User


class Update(YaBotObject):
    """A single update from Yandex Messenger Bot API.

    This is a flat object — all fields come at the same level.
    An update may contain text, document, images, sticker,
    bot_request, forward, etc. simultaneously.
    """

    update_id: int
    message_id: int
    timestamp: int
    chat: Chat
    from_user: User | None = Field(None, alias="from")
    text: str | None = None
    thread_id: int | None = None

    # Attachments (not mutually exclusive)
    forward: ForwardInfo | None = Field(None, alias="forwarded_messages")
    sticker: Sticker | None = None
    image: Image | None = None
    images: list[list[Image]] | None = None
    document: Document | None = None

    # Bot request (from button directives)
    bot_request: BotRequest | None = None
