"""Tests for middleware chain, registration, and propagation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from tests.conftest import make_update
from yandex_messenger_bot.dispatcher.dispatcher import Dispatcher
from yandex_messenger_bot.dispatcher.middlewares.base import BaseMiddleware
from yandex_messenger_bot.dispatcher.router import Router
from yandex_messenger_bot.types.update import Update

# ---------------------------------------------------------------------------
# Helpers / test middlewares
# ---------------------------------------------------------------------------


class RecordingMiddleware(BaseMiddleware):
    """Records calls with a label, then always delegates to the next handler."""

    def __init__(self, label: str, log: list[str]) -> None:
        self._label = label
        self._log = log

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        update: Update,
        data: dict[str, Any],
    ) -> Any:
        self._log.append(f"before:{self._label}")
        result = await handler(update, data)
        self._log.append(f"after:{self._label}")
        return result


class ShortCircuitMiddleware(BaseMiddleware):
    """Returns a fixed value without calling the next handler."""

    def __init__(self, return_value: Any, log: list[str] | None = None) -> None:
        self._return_value = return_value
        self._log: list[str] = [] if log is None else log

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        update: Update,
        data: dict[str, Any],
    ) -> Any:
        self._log.append("short-circuited")
        return self._return_value


class MutatingMiddleware(BaseMiddleware):
    """Injects a key/value pair into data before calling next handler."""

    def __init__(self, key: str, value: Any) -> None:
        self._key = key
        self._value = value

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        update: Update,
        data: dict[str, Any],
    ) -> Any:
        data[self._key] = self._value
        return await handler(update, data)


def _make_bot_stub() -> Any:
    from unittest.mock import MagicMock

    bot = MagicMock()
    bot.token = "test-token"
    return bot


# ---------------------------------------------------------------------------
# BaseMiddleware interface
# ---------------------------------------------------------------------------


class TestBaseMiddleware:
    async def test_recording_middleware_wraps_handler(self) -> None:
        log: list[str] = []
        mw = RecordingMiddleware("mw", log)

        async def handler(update: Update, data: dict[str, Any]) -> str:
            log.append("handler")
            return "done"

        result = await mw(handler, make_update(), {})
        assert result == "done"
        assert log == ["before:mw", "handler", "after:mw"]

    async def test_short_circuit_middleware_does_not_call_handler(self) -> None:
        log: list[str] = []
        handler_called: list[bool] = []

        async def handler(update: Update, data: dict[str, Any]) -> str:
            handler_called.append(True)
            return "should not run"

        mw = ShortCircuitMiddleware("blocked", log)
        result = await mw(handler, make_update(), {})
        assert result == "blocked"
        assert handler_called == []
        assert log == ["short-circuited"]

    async def test_mutating_middleware_injects_data(self) -> None:
        received: dict[str, Any] = {}

        async def handler(update: Update, data: dict[str, Any]) -> None:
            received.update(data)

        mw = MutatingMiddleware("injected_key", 42)
        await mw(handler, make_update(), {})
        assert received.get("injected_key") == 42


# ---------------------------------------------------------------------------
# Inner middleware (registered via observer.middleware())
# ---------------------------------------------------------------------------


class TestInnerMiddleware:
    async def test_inner_middleware_wraps_matched_handler(self) -> None:
        log: list[str] = []
        router = Router()
        router.message.middleware(RecordingMiddleware("inner", log))

        @router.message()
        async def handler(update: Update) -> str:
            log.append("handler")
            return "ok"

        await router.propagate(make_update(), {})
        assert log == ["before:inner", "handler", "after:inner"]

    async def test_inner_middleware_not_called_when_no_handler_matches(self) -> None:
        """Inner middleware should only run when a handler actually matches."""
        log: list[str] = []
        router = Router()
        router.message.middleware(RecordingMiddleware("inner", log))

        # No handlers registered — nothing matches
        from yandex_messenger_bot.dispatcher.event_observer import _UNHANDLED

        result = await router.propagate(make_update(), {})
        assert result is _UNHANDLED
        # The inner middleware should not have been invoked
        assert "before:inner" not in log

    async def test_multiple_inner_middlewares_ordered_correctly(self) -> None:
        """Multiple inner middlewares wrap handlers in registration order (outermost first)."""
        log: list[str] = []
        router = Router()
        router.message.middleware(RecordingMiddleware("first", log))
        router.message.middleware(RecordingMiddleware("second", log))

        @router.message()
        async def handler(update: Update) -> str:
            log.append("handler")
            return "ok"

        await router.propagate(make_update(), {})
        # first wraps second, which wraps handler
        assert log == ["before:first", "before:second", "handler", "after:second", "after:first"]

    async def test_inner_middleware_can_short_circuit(self) -> None:
        handler_called: list[bool] = []
        router = Router()
        log: list[str] = []
        router.message.middleware(ShortCircuitMiddleware("blocked", log))

        @router.message()
        async def handler(update: Update) -> str:
            handler_called.append(True)
            return "should not run"

        result = await router.propagate(make_update(), {})
        assert result == "blocked"
        assert handler_called == []

    async def test_inner_middleware_can_modify_data(self) -> None:
        """Middleware can inject data that is then available to the handler
        if the handler declares the injected key as a named parameter."""
        received: dict[str, Any] = {}
        router = Router()
        router.message.middleware(MutatingMiddleware("from_middleware", "injected"))

        @router.message()
        async def handler(update: Update, from_middleware: str) -> None:
            received["from_middleware"] = from_middleware

        await router.propagate(make_update(), {})
        assert received.get("from_middleware") == "injected"


# ---------------------------------------------------------------------------
# Outer middleware (registered via observer.outer_middleware())
# ---------------------------------------------------------------------------


class TestOuterMiddleware:
    async def test_outer_middleware_wraps_entire_observer(self) -> None:
        log: list[str] = []
        router = Router()
        router.message.outer_middleware(RecordingMiddleware("outer", log))

        @router.message()
        async def handler(update: Update) -> str:
            log.append("handler")
            return "ok"

        await router.propagate(make_update(), {})
        assert log == ["before:outer", "handler", "after:outer"]

    async def test_outer_middleware_runs_even_with_no_matching_handler(self) -> None:
        """Outer middleware wraps the observer call, including the no-match path."""
        log: list[str] = []
        router = Router()
        router.message.outer_middleware(RecordingMiddleware("outer", log))
        # No handlers registered

        await router.propagate(make_update(), {})
        # Outer MW ran even with no handlers
        assert "before:outer" in log
        assert "after:outer" in log

    async def test_outer_middleware_can_short_circuit(self) -> None:
        handler_called: list[bool] = []
        log: list[str] = []
        router = Router()
        router.message.outer_middleware(ShortCircuitMiddleware("outer-blocked", log))

        @router.message()
        async def handler(update: Update) -> str:
            handler_called.append(True)
            return "should not run"

        result = await router.propagate(make_update(), {})
        assert result == "outer-blocked"
        assert handler_called == []

    async def test_multiple_outer_middlewares_ordered_correctly(self) -> None:
        log: list[str] = []
        router = Router()
        router.message.outer_middleware(RecordingMiddleware("outer-1", log))
        router.message.outer_middleware(RecordingMiddleware("outer-2", log))

        @router.message()
        async def handler(update: Update) -> str:
            log.append("handler")
            return "ok"

        await router.propagate(make_update(), {})
        # outer-1 registered first → wraps outermost
        assert log == [
            "before:outer-1",
            "before:outer-2",
            "handler",
            "after:outer-2",
            "after:outer-1",
        ]


# ---------------------------------------------------------------------------
# Middleware propagation: parent router outer middlewares apply to child handlers
# ---------------------------------------------------------------------------


class TestMiddlewarePropagation:
    async def test_parent_outer_middleware_applies_to_child_handler(self) -> None:
        """Outer middleware on a parent router must wrap child router handlers."""
        log: list[str] = []
        parent = Router(name="parent")
        child = Router(name="child")
        parent.include_router(child)

        parent.message.outer_middleware(RecordingMiddleware("parent-outer", log))

        @child.message()
        async def handler(update: Update) -> str:
            log.append("child-handler")
            return "ok"

        await parent.propagate(make_update(), {})
        assert "before:parent-outer" in log
        assert "child-handler" in log
        assert "after:parent-outer" in log

    async def test_parent_outer_before_child_outer(self) -> None:
        """Parent outer middleware wraps child outer middleware.

        The propagation model applies each router's outer middleware around
        its entire sub-tree (own handlers + sub-routers), so parent middleware
        runs exactly once, outermost.
        """
        log: list[str] = []
        parent = Router(name="parent")
        child = Router(name="child")
        parent.include_router(child)

        parent.message.outer_middleware(RecordingMiddleware("parent-outer", log))
        child.message.outer_middleware(RecordingMiddleware("child-outer", log))

        @child.message()
        async def handler(update: Update) -> str:
            log.append("handler")
            return "ok"

        await parent.propagate(make_update(), {})
        # Parent outer wraps child outer, which wraps handler — each runs once
        assert log == [
            "before:parent-outer",
            "before:child-outer",
            "handler",
            "after:child-outer",
            "after:parent-outer",
        ]

    async def test_dispatcher_outer_middleware_applies_via_feed_update(self) -> None:
        """Outer middleware on the Dispatcher applies when using feed_update."""
        log: list[str] = []
        dp = Dispatcher()
        dp.message.outer_middleware(RecordingMiddleware("dp-outer", log))

        @dp.message()
        async def handler(update: Update) -> None:
            log.append("handler")

        bot = _make_bot_stub()
        await dp.feed_update(bot, make_update())
        assert log == ["before:dp-outer", "handler", "after:dp-outer"]

    async def test_child_outer_middleware_without_parent_outer(self) -> None:
        """Child outer middleware runs even when the parent has no outer middleware."""
        log: list[str] = []
        parent = Router(name="parent")
        child = Router(name="child")
        parent.include_router(child)

        child.message.outer_middleware(RecordingMiddleware("child-only-outer", log))

        @child.message()
        async def handler(update: Update) -> str:
            log.append("handler")
            return "ok"

        await parent.propagate(make_update(), {})
        assert log == ["before:child-only-outer", "handler", "after:child-only-outer"]

    async def test_outer_middleware_on_parent_not_applied_to_unrelated_event_type(self) -> None:
        """Outer middleware registered on parent.message does not affect bot_request events."""
        log: list[str] = []
        parent = Router(name="parent")
        parent.message.outer_middleware(RecordingMiddleware("msg-outer", log))

        upd = make_update(
            text=None,
            bot_request={"server_action": {"name": "click", "payload": {}}},
        )

        @parent.bot_request()
        async def handler(update: Update) -> str:
            log.append("bot_request-handler")
            return "ok"

        await parent.propagate(upd, {})
        # The message outer middleware should NOT have run
        assert "before:msg-outer" not in log
        assert "bot_request-handler" in log


# ---------------------------------------------------------------------------
# Combined: outer + inner middleware execution order
# ---------------------------------------------------------------------------


class TestCombinedMiddlewareOrder:
    async def test_outer_wraps_inner_wraps_handler(self) -> None:
        log: list[str] = []
        router = Router()
        router.message.outer_middleware(RecordingMiddleware("outer", log))
        router.message.middleware(RecordingMiddleware("inner", log))

        @router.message()
        async def handler(update: Update) -> str:
            log.append("handler")
            return "ok"

        await router.propagate(make_update(), {})
        assert log == ["before:outer", "before:inner", "handler", "after:inner", "after:outer"]

    async def test_parent_outer_child_outer_inner_handler_order(self) -> None:
        """Full ordering within the child observer's invocation:
        parent-outer → child-outer → inner → handler.

        Note: the parent outer middleware runs once on the parent's own (empty)
        observer pass, then again on the child observer pass (inherited via
        _resolve_middlewares), so it appears twice in the full log.
        """
        log: list[str] = []
        parent = Router(name="parent")
        child = Router(name="child")
        parent.include_router(child)

        parent.message.outer_middleware(RecordingMiddleware("p-outer", log))
        child.message.outer_middleware(RecordingMiddleware("c-outer", log))
        child.message.middleware(RecordingMiddleware("inner", log))

        @child.message()
        async def handler(update: Update) -> str:
            log.append("handler")
            return "ok"

        await parent.propagate(make_update(), {})
        # Actual full log:
        #   before:p-outer, after:p-outer,                    <- parent's own pass (no handlers)
        #   before:p-outer, before:c-outer, before:inner,     <- child's observer pass
        #   handler,
        #   after:inner, after:c-outer, after:p-outer
        expected_suffix = [
            "before:p-outer",
            "before:c-outer",
            "before:inner",
            "handler",
            "after:inner",
            "after:c-outer",
            "after:p-outer",
        ]
        # The suffix (child observer pass) must appear at the end of the log
        assert log[-len(expected_suffix) :] == expected_suffix
