from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from yandex_messenger_bot.dispatcher.handler import HandlerObject
from yandex_messenger_bot.types.update import Update

_AnyHandler = Callable[..., Awaitable[Any]]

# Sentinel returned by trigger() when no handler matched.  Distinct from None
# so that handlers which legitimately return None are still treated as handled.
_UNHANDLED: object = object()


class EventObserver:
    """Manages a list of handlers and middleware for a specific event category.

    Usage::

        observer = EventObserver()


        @observer(CommandFilter("start"))
        async def on_start(update: Update) -> None: ...
    """

    def __init__(self) -> None:
        self.handlers: list[HandlerObject] = []
        self._middlewares: list[Callable[..., Any]] = []
        self._outer_middlewares: list[Callable[..., Any]] = []

    # ------------------------------------------------------------------ #
    # Registration                                                         #
    # ------------------------------------------------------------------ #

    def register(self, callback: _AnyHandler, *filters: Any) -> _AnyHandler:
        """Register *callback* with optional *filters*."""
        handler = HandlerObject(callback=callback, filters=filters)
        self.handlers.append(handler)
        return callback

    def __call__(self, *filters: Any) -> Callable[[_AnyHandler], _AnyHandler]:
        """Decorator factory — use as ``@observer(filter1, filter2)``."""

        def decorator(callback: _AnyHandler) -> _AnyHandler:
            self.register(callback, *filters)
            return callback

        return decorator

    # ------------------------------------------------------------------ #
    # Middleware registration                                              #
    # ------------------------------------------------------------------ #

    def middleware(self, middleware_obj: Any) -> Any:
        """Register an *inner* middleware (wraps each matched handler call)."""
        self._middlewares.append(middleware_obj)
        return middleware_obj

    def outer_middleware(self, middleware_obj: Any) -> Any:
        """Register an *outer* middleware (wraps the entire observer trigger)."""
        self._outer_middlewares.append(middleware_obj)
        return middleware_obj

    # ------------------------------------------------------------------ #
    # Dispatch                                                             #
    # ------------------------------------------------------------------ #

    async def trigger(self, update: Update, data: dict[str, Any]) -> Any:
        """Try each registered handler in order.

        Returns the result of the *first* handler whose filters all pass, or
        *None* if no handler matched.

        The call is wrapped by outer middlewares first, then for each
        matching handler by inner middlewares.
        """
        # Always make `update` available in the data dict so handlers can
        # declare `update: Update` as a parameter and receive it via DI.
        if "update" not in data:
            data = {**data, "update": update}

        # Build the core dispatch coroutine
        async def _dispatch(update: Update, data: dict[str, Any]) -> Any:
            for handler in self.handlers:
                extra = await handler.check_filters(update, data)
                if extra is None:
                    continue

                merged = {**data, **extra}

                # Build inner middleware chain around this handler
                async def _call_handler(
                    _update: Update,
                    _data: dict[str, Any],
                    _handler: HandlerObject = handler,
                ) -> Any:
                    return await _handler.call(_update, _data)

                chain: _AnyHandler = _call_handler
                for mw in reversed(self._middlewares):
                    _prev = chain

                    async def _wrapped(
                        u: Update,
                        d: dict[str, Any],
                        _mw: Any = mw,
                        _next: _AnyHandler = _prev,
                    ) -> Any:
                        return await _mw(_next, u, d)

                    chain = _wrapped

                return await chain(update, merged)

            return _UNHANDLED  # no handler matched

        # Wrap with outer middlewares
        outer_chain: _AnyHandler = _dispatch
        for mw in reversed(self._outer_middlewares):
            _prev_outer = outer_chain

            async def _outer_wrapped(
                u: Update,
                d: dict[str, Any],
                _mw: Any = mw,
                _next: _AnyHandler = _prev_outer,
            ) -> Any:
                return await _mw(_next, u, d)

            outer_chain = _outer_wrapped

        return await outer_chain(update, data)
