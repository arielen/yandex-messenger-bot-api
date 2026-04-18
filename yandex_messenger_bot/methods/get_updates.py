from __future__ import annotations

from typing import ClassVar

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.base import YaBotObject
from yandex_messenger_bot.types.update import Update


class GetUpdatesResult(YaBotObject):
    updates: list[Update]


class GetUpdates(YaBotMethod[GetUpdatesResult]):
    """Fetch pending updates via long polling."""

    __api_path__: ClassVar[str] = "/bot/v1/messages/getUpdates/"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = GetUpdatesResult

    offset: int = 0
    limit: int = 100
