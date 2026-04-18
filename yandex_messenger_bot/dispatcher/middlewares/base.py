from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from yandex_messenger_bot.types.update import Update


class BaseMiddleware(ABC):
    """Abstract base class for update middlewares.

    Subclass and implement :meth:`__call__` to intercept updates before they
    reach a handler.  Call *next_handler* to pass the update downstream::

        class LoggingMiddleware(BaseMiddleware):
            async def __call__(self, handler, update, data):
                print(f"Incoming update {update.update_id}")
                result = await handler(update, data)
                print(f"Handler returned {result!r}")
                return result

    Register on an observer::

        router.message.middleware(LoggingMiddleware())
        # or for outer (wraps the whole observer):
        router.message.outer_middleware(LoggingMiddleware())
    """

    @abstractmethod
    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        update: Update,
        data: dict[str, Any],
    ) -> Any:
        """Process the update, calling *handler* to continue the chain."""
