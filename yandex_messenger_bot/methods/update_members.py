from __future__ import annotations

from typing import Annotated, Any, ClassVar

from pydantic import Field, field_serializer

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.base import YaBotObject


class UpdateMembersResult(YaBotObject):
    ok: bool = True


def _logins_to_user_objects(logins: list[str] | None) -> list[dict[str, str]] | None:
    """Convert a list of login strings to API User objects ``{"login": ...}``."""
    if logins is None:
        return None
    return [{"login": login} for login in logins]


class UpdateMembers(YaBotMethod[UpdateMembersResult]):
    """Add or remove members/admins/subscribers from a chat or channel."""

    __api_path__: ClassVar[str] = "/bot/v1/chats/updateMembers/"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = UpdateMembersResult

    chat_id: str
    members: Annotated[list[str] | None, Field(default=None)]
    admins: Annotated[list[str] | None, Field(default=None)]
    subscribers: Annotated[list[str] | None, Field(default=None)]
    remove: Annotated[list[str] | None, Field(default=None)]

    @field_serializer("members", "admins", "subscribers", "remove")
    def _serialize_user_list(self, value: list[str] | None) -> list[dict[str, Any]] | None:
        return _logins_to_user_objects(value)
