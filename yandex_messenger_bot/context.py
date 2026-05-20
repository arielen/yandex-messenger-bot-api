"""Request-scoped context for the active :class:`~yandex_messenger_bot.client.bot.Bot`.

Set by :meth:`~yandex_messenger_bot.dispatcher.dispatcher.Dispatcher.feed_update`
so handlers can call :meth:`~yandex_messenger_bot.types.update.Update.reply` without
passing ``bot`` explicitly.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

# ``Bot`` is not imported here — avoids an import cycle with ``client.bot`` /
# ``types.update`` during package startup. Callers treat the value as ``Bot``.

_current_bot: ContextVar[Any] = ContextVar(
    "yandex_messenger_bot_current_bot",
    default=None,
)


def get_current_bot() -> Any:
    """Return the bot for the current update (inside ``feed_update``)."""
    bot = _current_bot.get()
    if bot is None:
        msg = (
            "No bot in context. Call Update.reply() only while handling an update "
            "(Dispatcher.feed_update / polling / webhook), or pass bot= explicitly."
        )
        raise RuntimeError(msg)
    return bot


def set_current_bot(bot: Any) -> Token[Any]:
    """Bind *bot* for the current async task; return a token for :func:`reset_current_bot`."""
    return _current_bot.set(bot)


def reset_current_bot(token: Token[Any]) -> None:
    """Restore the previous bot binding (call in ``finally`` after :func:`set_current_bot`)."""
    _current_bot.reset(token)
