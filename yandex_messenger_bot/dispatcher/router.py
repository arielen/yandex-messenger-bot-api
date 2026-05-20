from __future__ import annotations

from collections.abc import Awaitable, Callable
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

        # ---- Parent back-reference (set by include_router on the parent) -----
        self._parent_router: Router | None = None

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
        if router is self:
            msg = "A router cannot include itself."
            raise ValueError(msg)
        # Cycle detection: walk up from self to root; if we encounter *router*
        # it would form a cycle.
        node: Router | None = self._parent_router
        while node is not None:
            if node is router:
                msg = "Circular router inclusion detected."
                raise ValueError(msg)
            node = node._parent_router
        router._parent_router = self
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

        Each event type is propagated through the entire router tree (own
        handlers + sub-routers), wrapped in the current router's outer
        middleware.  This ensures parent outer middleware wraps child handler
        execution exactly once.
        """
        # 1. bot_request event path
        if update.bot_request is not None:
            result = await self._propagate_event_tree(
                self.bot_request,
                update,
                data,
            )
            if result is not _UNHANDLED:
                return result

        # 2. message event path
        return await self._propagate_event_tree(self.message, update, data)

    async def _propagate_event_tree(
        self,
        observer: EventObserver,
        update: Update,
        data: dict[str, Any],
    ) -> Any:
        """Propagate an event through own handlers + sub-routers, wrapped in
        own outer middleware.

        Each router wraps its sub-tree in its own outer middleware, so parent
        middleware runs outermost and child middleware runs innermost — without
        the parent middleware executing twice.
        """
        _AnyHandler = Callable[..., Awaitable[Any]]
        event_attr = "bot_request" if observer is self.bot_request else "message"

        async def _core(update: Update, data: dict[str, Any]) -> Any:
            # Try own handlers (inner middleware applied by observer.trigger)
            result = await observer.trigger(update, data)
            if result is not _UNHANDLED:
                return result
            # Try sub-routers depth-first
            for sub in self._sub_routers:
                sub_observer: EventObserver = getattr(sub, event_attr)
                result = await sub._propagate_event_tree(
                    sub_observer,
                    update,
                    data,
                )
                if result is not _UNHANDLED:
                    return result
            return _UNHANDLED

        # Wrap _core in this router's outer middleware for this event type
        chain: _AnyHandler = _core
        for mw in reversed(observer._outer_middlewares):
            _prev = chain

            async def _outer_wrapped(
                u: Update,
                d: dict[str, Any],
                _mw: Any = mw,
                _next: _AnyHandler = _prev,
            ) -> Any:
                return await _mw(_next, u, d)

            chain = _outer_wrapped

        return await chain(update, data)
