from __future__ import annotations

from typing import ClassVar

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.user_link import UserLink


class GetUserLink(YaBotMethod[UserLink]):
    """Get chat and call links for a user by login."""

    __api_path__: ClassVar[str] = "/bot/v1/users/getUserLink/"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = UserLink

    login: str
