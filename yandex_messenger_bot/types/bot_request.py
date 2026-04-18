from __future__ import annotations

from typing import Any

from pydantic import Field

from yandex_messenger_bot.types.base import YaBotObject


class ServerAction(YaBotObject):
    """A server action from a button click (silent callback)."""

    name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class BotRequestError(YaBotObject):
    """An error reported in a bot request."""

    type: str
    name: str | None = None
    message: str | None = None


class BotRequest(YaBotObject):
    """Bot request data from a button directive callback."""

    server_action: ServerAction | None = None
    element_id: str | None = None
    errors: list[BotRequestError] = Field(default_factory=list)
