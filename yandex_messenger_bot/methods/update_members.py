from __future__ import annotations

from typing import ClassVar

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.base import YaBotObject


class UpdateMembersResult(YaBotObject):
    ok: bool = True


class UpdateMembers(YaBotMethod[UpdateMembersResult]):
    """Add or remove members/admins/subscribers from a chat or channel."""

    __api_path__: ClassVar[str] = "/bot/v1/chats/updateMembers/"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = UpdateMembersResult

    chat_id: str
    members_add: list[str] | None = None
    members_remove: list[str] | None = None
    admins_add: list[str] | None = None
    admins_remove: list[str] | None = None
    subscribers_add: list[str] | None = None
    subscribers_remove: list[str] | None = None
