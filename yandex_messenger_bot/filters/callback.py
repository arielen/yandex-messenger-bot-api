from __future__ import annotations

from typing import Any

from yandex_messenger_bot.filters.base import BaseFilter
from yandex_messenger_bot.types.update import Update


class ServerActionFilter(BaseFilter):
    """Filter that matches updates containing a ``bot_request.server_action``
    whose name is one of the given *action_names*.

    On a match the matched :class:`~yandex_messenger_bot.types.bot_request.ServerAction`
    object is injected under the key ``"server_action"``::

        @router.bot_request(ServerActionFilter("submit_form"))
        async def handle_submit(update: Update, server_action: ServerAction) -> None:
            payload = server_action.payload
            ...
    """

    def __init__(self, *action_names: str) -> None:
        self._names: frozenset[str] = frozenset(action_names)

    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        if update.bot_request is None:
            return False
        action = update.bot_request.server_action
        if action is None:
            return False
        if not self._names or action.name in self._names:
            return {"server_action": action}
        return False
