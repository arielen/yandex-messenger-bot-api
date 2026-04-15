from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from yandex_messenger_bot.dispatcher.router import Router
from yandex_messenger_bot.fsm.context import FSMContext
from yandex_messenger_bot.fsm.storage.base import BaseStorage, StorageKey
from yandex_messenger_bot.fsm.storage.memory import MemoryStorage
from yandex_messenger_bot.loggers import dispatcher as logger
from yandex_messenger_bot.polling.polling import run_polling

if TYPE_CHECKING:
    from yandex_messenger_bot.client.bot import Bot
    from yandex_messenger_bot.types.update import Update


class Dispatcher(Router):
    """Top-level dispatcher that owns the bot and drives update processing.

    Extends :class:`Router` with:

    * FSM storage integration.
    * A dependency-injection registry (``dp.dependency(T, factory=…)``).
    * A long-polling entry point (:meth:`run_polling` / :meth:`start_polling`).

    Usage::

        dp = Dispatcher()


        @dp.message(CommandFilter("start"))
        async def start(update: Update, bot: Bot) -> None:
            await bot.send_text(chat_id=update.chat.id, text="Hello!")


        if __name__ == "__main__":
            dp.run_polling(Bot(token="…"))
    """

    def __init__(self, storage: BaseStorage | None = None) -> None:
        super().__init__(name="__dispatcher__")
        self.storage: BaseStorage = storage or MemoryStorage()
        self._dependencies: dict[type, Callable[..., Any]] = {}

    # ------------------------------------------------------------------ #
    # Dependency injection                                                 #
    # ------------------------------------------------------------------ #

    def dependency(self, type_: type, *, factory: Callable[..., Any]) -> None:
        """Register a *factory* that produces instances of *type_*.

        The factory may be:

        * A plain coroutine function — called once per update.
        * An async generator — yields one value; cleanup runs after the handler.
        * A sync callable — called once per update.

        Example::

            async def get_db() -> AsyncGenerator[Database, None]:
                async with Database.connect() as db:
                    yield db


            dp.dependency(Database, factory=get_db)
        """
        self._dependencies[type_] = factory

    # ------------------------------------------------------------------ #
    # Core update processing                                               #
    # ------------------------------------------------------------------ #

    async def feed_update(self, bot: Bot, update: Update) -> None:
        """Process a single *update* through the middleware and router chain.

        Builds the data dict with built-in dependencies (``bot``, ``update``,
        ``chat``, ``user``, ``state``, ``dispatcher``), resolves any custom
        DI registrations, then calls :meth:`propagate`.
        """
        bot_id = hashlib.sha256(bot.token.encode()).hexdigest()[:16]
        key = StorageKey(
            bot_id=bot_id,
            chat_id=update.chat.id,
            user_id=update.from_user.id or "" if update.from_user else "",
        )
        state = FSMContext(storage=self.storage, key=key)

        data: dict[str, Any] = {
            "bot": bot,
            "update": update,
            "chat": update.chat,
            "state": state,
            "dispatcher": self,
            "__dependencies__": self._dependencies,
        }
        if update.from_user is not None:
            data["user"] = update.from_user

        try:
            await self.propagate(update, data)
        except Exception:
            logger.exception("Unhandled error processing update %d", update.update_id)

    # ------------------------------------------------------------------ #
    # Polling entry points                                                 #
    # ------------------------------------------------------------------ #

    async def start_polling(
        self,
        bot: Bot,
        *,
        limit: int = 100,
        poll_interval: float = 1.0,
    ) -> None:
        """Start the long-polling loop (async), including lifecycle callbacks."""
        await self._emit_startup()
        try:
            await run_polling(
                self,
                bot,
                limit=limit,
                poll_interval=poll_interval,
            )
        finally:
            await self._emit_shutdown()

    def run_polling(
        self,
        bot: Bot,
        *,
        limit: int = 100,
        poll_interval: float = 1.0,
    ) -> None:
        """Synchronous entry point — blocks until the polling loop stops."""

        async def _main() -> None:
            async with bot:
                await self.start_polling(bot, limit=limit, poll_interval=poll_interval)

        asyncio.run(_main())

    # ------------------------------------------------------------------ #
    # Lifecycle helpers                                                    #
    # ------------------------------------------------------------------ #

    async def _emit_startup(self) -> None:
        """Call all startup callbacks registered on this dispatcher and
        all descendant routers (depth-first)."""
        for router in self._collect_routers():
            for cb in router._startup_callbacks:
                await cb()

    async def _emit_shutdown(self) -> None:
        """Call all shutdown callbacks registered on this dispatcher and
        all descendant routers (depth-first), then close FSM storage."""
        for router in self._collect_routers():
            for cb in router._shutdown_callbacks:
                await cb()
        try:
            await self.storage.close()
        except Exception:
            logger.exception("Error closing FSM storage")
