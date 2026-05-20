from __future__ import annotations

from typing import Any

from magic_filter import MagicFilter

F: Any = MagicFilter()
"""Shortcut for building attribute-access filter expressions.

Example::

    from yandex_messenger_bot.filters.magic import F

    @router.message(F.text.startswith("hello"))
    async def greet(update: Update) -> None:
        ...
"""

__all__ = ["F", "MagicFilter"]
