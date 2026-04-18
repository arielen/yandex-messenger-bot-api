from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yandex_messenger_bot.filters.base import BaseFilter
from yandex_messenger_bot.types.update import Update


@dataclass(frozen=True)
class CommandObject:
    """Parsed command data injected into the handler data dict."""

    command: str
    """The command name without the leading ``/``."""
    args: str
    """Everything after the command, stripped of surrounding whitespace."""
    prefix: str = "/"
    """The prefix character (always ``/`` for standard commands)."""


class CommandFilter(BaseFilter):
    """Filter that matches messages starting with one of the given commands.

    On a match the filter injects a :class:`CommandObject` under the key
    ``"command"`` so handlers can receive it::

        @router.message(CommandFilter("start"))
        async def handle_start(update: Update, command: CommandObject) -> None: ...
    """

    def __init__(self, *commands: str, ignore_case: bool = True) -> None:
        self._commands = commands
        self._ignore_case = ignore_case

    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        if not update.text:
            return False

        text = update.text.strip()

        for cmd in self._commands:
            # Normalise: ensure command starts with "/"
            target = cmd if cmd.startswith("/") else f"/{cmd}"

            if self._ignore_case:
                match = text.lower().startswith(target.lower())
            else:
                match = text.startswith(target)

            if match:
                # Ensure the command ends at a word boundary
                after = text[len(target) :]
                if after and not after[0].isspace():
                    continue  # "/starter" should NOT match "/start"
                rest = after.strip()
                return {
                    "command": CommandObject(
                        command=cmd.lstrip("/"),
                        args=rest,
                    )
                }

        return False
