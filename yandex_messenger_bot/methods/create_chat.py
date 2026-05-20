from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.base import YaBotObject


class CreateChatResult(YaBotObject):
    chat_id: str


class CreateChat(YaBotMethod[CreateChatResult]):
    """Create a new group chat or channel."""

    __api_path__: ClassVar[str] = "/bot/v1/chats/create/"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = CreateChatResult

    name: str
    description: str = ""
    avatar_url: str | None = None
    members: list[dict[str, str]] | None = None
    admins: list[dict[str, str]] | None = None
    subscribers: list[dict[str, str]] | None = None
    is_channel: bool = Field(False, alias="channel")
