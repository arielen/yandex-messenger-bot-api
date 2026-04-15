from __future__ import annotations

from collections.abc import Callable
from typing import Any

from yandex_messenger_bot.dispatcher.event_observer import _UNHANDLED, EventObserver
from yandex_messenger_bot.types.update import Update


class Router:
    """Groups handlers and sub-routers together.

    A :class:`Router` has two built-in :class:`EventObserver` attributes:

    * ``message`` — fires for updates that carry text, a document, an image,
      a sticker, a forward, etc.
    * ``bot_request`` — fires for updates that have a ``bot_request`` field.

    Sub-routers are traversed depth-first after the parent's own observers.

    Usage::

        router = Router(name="my_feature")


        @router.message(CommandFilter("help"))
        async def handle_help(update: Update, bot: Bot) -> None:
            await bot.send_text(chat_id=update.chat.id, text="Help!")
    """

    def __init__(self, name: str | None = None) -> None:
        self.name = name

        # ---- Built-in event observers ----------------------------------------
        self.message: EventObserver = EventObserver()
        """Observer for general message updates (text, file, image, sticker…)."""
        self.bot_request: EventObserver = EventObserver()
        """Observer for bot_request updates (button callbacks)."""

        # ---- Routing tree --------------------------------------------------------
        self._sub_routers: list[Router] = []

        # ---- Lifecycle callbacks -------------------------------------------------
        self._startup_callbacks: list[Callable[..., Any]] = []
        self._shutdown_callbacks: list[Callable[..., Any]] = []

    # ------------------------------------------------------------------ #
    # Sub-router management                                               #
    # ------------------------------------------------------------------ #

    def include_router(self, router: Router) -> None:
        """Attach *router* as a child of this router."""
        self._sub_routers.append(router)

    def _collect_routers(self) -> list[Router]:
        """Collect this router and all descendant routers, depth-first."""
        result: list[Router] = [self]
        for sub in self._sub_routers:
            result.extend(sub._collect_routers())
        return result

    # ------------------------------------------------------------------ #
    # Convenience decorators                                              #
    # ------------------------------------------------------------------ #

    def on_message(self, *filters: Any) -> Callable[..., Any]:
        """Shortcut for ``@router.message(*filters)``."""
        return self.message(*filters)

    def on_bot_request(self, *filters: Any) -> Callable[..., Any]:
        """Shortcut for ``@router.bot_request(*filters)``."""
        return self.bot_request(*filters)

    def on_startup(self) -> Callable[..., Any]:
        """Register a startup callback.  Usage::

        @router.on_startup()
        async def setup() -> None:
            ...
        """

        def decorator(callback: Callable[..., Any]) -> Callable[..., Any]:
            self._startup_callbacks.append(callback)
            return callback

        return decorator

    def on_shutdown(self) -> Callable[..., Any]:
        """Register a shutdown callback.  Usage::

        @router.on_shutdown()
        async def teardown() -> None:
            ...
        """

        def decorator(callback: Callable[..., Any]) -> Callable[..., Any]:
            self._shutdown_callbacks.append(callback)
            return callback

        return decorator

    # ------------------------------------------------------------------ #
    # Dispatch                                                             #
    # ------------------------------------------------------------------ #

    async def propagate(self, update: Update, data: dict[str, Any]) -> Any:
        """Route *update* through this router and its sub-routers (depth-first).

        The routing order is:

        1. ``bot_request`` observer — only if the update has a ``bot_request``.
        2. ``message`` observer — always attempted.
        3. Each sub-router, in registration order.

        Returns the first non-*None* handler result, or *None* if nothing
        matched.
        """
        # 1. bot_request observer
        if update.bot_request is not None:
            result = await self.bot_request.trigger(update, data)
            if result is not _UNHANDLED:
                return result

        # 2. message observer
        result = await self.message.trigger(update, data)
        if result is not _UNHANDLED:
            return result

        # 3. sub-routers (depth-first)
        for sub in self._sub_routers:
            result = await sub.propagate(update, data)
            if result is not _UNHANDLED:
                return result

        return _UNHANDLED
