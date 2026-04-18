from __future__ import annotations

from pydantic import Field

from yandex_messenger_bot.types.base import YaBotObject


class BotSelf(YaBotObject):
    """Bot info returned by self/update endpoint."""

    id: str
    display_name: str | None = None
    webhook_url: str | None = None
    organizations: list[int] = Field(default_factory=list)
    login: str | None = None
