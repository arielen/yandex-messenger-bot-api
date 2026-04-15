"""Tests for HandlerObject, EventObserver, Router, and Dispatcher."""

from __future__ import annotations

import hashlib
from typing import Any
from unittest.mock import MagicMock

from tests.conftest import make_update
from yandex_messenger_bot.dispatcher.dispatcher import Dispatcher
from yandex_messenger_bot.dispatcher.event_observer import _UNHANDLED, EventObserver
from yandex_messenger_bot.dispatcher.handler import HandlerObject
from yandex_messenger_bot.dispatcher.router import Router
from yandex_messenger_bot.filters.base import BaseFilter
from yandex_messenger_bot.fsm.context import FSMContext
from yandex_messenger_bot.fsm.storage.base import StorageKey
from yandex_messenger_bot.fsm.strategy import FSMStrategy
from yandex_messenger_bot.types.update import Update

# ---------------------------------------------------------------------------
# Helpers / minimal stubs
# ---------------------------------------------------------------------------


class _AlwaysPassFilter(BaseFilter):
    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        return True


class _AlwaysFailFilter(BaseFilter):
    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        return False


class _InjectFilter(BaseFilter):
    """Passes and injects a value into the data dict."""

    def __init__(self, key: str, value: Any) -> None:
        self._key = key
        self._value = value

    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        return {self._key: self._value}


def _make_bot_stub(token: str = "12345678:fake-token") -> Any:
    bot = MagicMock()
    bot.token = token
    return bot


# ---------------------------------------------------------------------------
# HandlerObject
# ---------------------------------------------------------------------------


class TestHandlerObject:
    async def test_inspects_params_correctly(self) -> None:
        async def handler(update: Update, text: str) -> None:
            pass

        obj = HandlerObject(callback=handler, filters=())
        assert "update" in obj._params
        assert "text" in obj._params

    async def test_prepare_kwargs_filters_to_declared_params(self) -> None:
        async def handler(update: Update, name: str) -> str:
            return name

        obj = HandlerObject(callback=handler, filters=())
        data = {"update": make_update(), "name": "Alice", "extra": "ignored"}
        kwargs = obj.prepare_kwargs(data)
        assert set(kwargs.keys()) == {"update", "name"}
        assert "extra" not in kwargs

    async def test_prepare_kwargs_missing_params_skipped(self) -> None:
        async def handler(update: Update, optional_thing: str) -> None:
            pass

        obj = HandlerObject(callback=handler, filters=())
        # optional_thing not in data — should simply be absent, no KeyError
        kwargs = obj.prepare_kwargs({"update": make_update()})
        assert "optional_thing" not in kwargs

    async def test_call_invokes_callback_with_filtered_kwargs(self) -> None:
        received: dict[str, Any] = {}

        async def handler(update: Update, tag: str) -> str:
            received["update"] = update
            received["tag"] = tag
            return "ok"

        obj = HandlerObject(callback=handler, filters=())
        upd = make_update()
        result = await obj.call(upd, {"update": upd, "tag": "hello", "noise": 99})
        assert result == "ok"
        assert received["tag"] == "hello"

    async def test_check_filters_all_pass_returns_empty_dict(self) -> None:
        async def handler(update: Update) -> None:
            pass

        obj = HandlerObject(callback=handler, filters=(_AlwaysPassFilter(),))
        result = await obj.check_filters(make_update(), {})
        assert result == {}

    async def test_check_filters_one_fails_returns_none(self) -> None:
        async def handler(update: Update) -> None:
            pass

        obj = HandlerObject(
            callback=handler,
            filters=(_AlwaysPassFilter(), _AlwaysFailFilter()),
        )
        result = await obj.check_filters(make_update(), {})
        assert result is None

    async def test_check_filters_merges_injected_dicts(self) -> None:
        async def handler(update: Update) -> None:
            pass

        obj = HandlerObject(
            callback=handler,
            filters=(_InjectFilter("x", 10), _InjectFilter("y", 20)),
        )
        result = await obj.check_filters(make_update(), {})
        assert result == {"x": 10, "y": 20}

    async def test_no_filters_always_passes(self) -> None:
        async def handler() -> None:
            pass

        obj = HandlerObject(callback=handler, filters=())
        result = await obj.check_filters(make_update(), {})
        assert result == {}


# ---------------------------------------------------------------------------
# EventObserver
# ---------------------------------------------------------------------------


class TestEventObserver:
    async def test_registers_and_triggers_handler(self) -> None:
        calls: list[str] = []
        observer = EventObserver()

        @observer(_AlwaysPassFilter())
        async def handler(update: Update) -> str:
            calls.append("called")
            return "done"

        result = await observer.trigger(make_update(), {})
        assert result == "done"
        assert calls == ["called"]

    async def test_skips_non_matching_handler(self) -> None:
        observer = EventObserver()

        @observer(_AlwaysFailFilter())
        async def handler(update: Update) -> str:
            return "should not run"

        result = await observer.trigger(make_update(), {})
        assert result is _UNHANDLED

    async def test_first_matching_handler_wins(self) -> None:
        observer = EventObserver()

        @observer(_AlwaysPassFilter())
        async def first(update: Update) -> str:
            return "first"

        @observer(_AlwaysPassFilter())
        async def second(update: Update) -> str:
            return "second"

        result = await observer.trigger(make_update(), {})
        assert result == "first"

    async def test_falls_through_to_second_when_first_fails(self) -> None:
        observer = EventObserver()

        @observer(_AlwaysFailFilter())
        async def missed(update: Update) -> str:
            return "nope"

        @observer(_AlwaysPassFilter())
        async def caught(update: Update) -> str:
            return "caught"

        result = await observer.trigger(make_update(), {})
        assert result == "caught"

    async def test_filter_injected_data_available_in_handler(self) -> None:
        observer = EventObserver()
        received: dict[str, Any] = {}

        @observer(_InjectFilter("magic", 42))
        async def handler(update: Update, magic: int) -> None:
            received["magic"] = magic

        await observer.trigger(make_update(), {})
        assert received["magic"] == 42

    async def test_update_injected_into_data_automatically(self) -> None:
        observer = EventObserver()
        received: list[Update] = []

        @observer()
        async def handler(update: Update) -> None:
            received.append(update)

        upd = make_update()
        await observer.trigger(upd, {})
        assert received[0] is upd

    async def test_no_handlers_returns_unhandled(self) -> None:
        observer = EventObserver()
        assert await observer.trigger(make_update(), {}) is _UNHANDLED

    async def test_register_returns_original_callback(self) -> None:
        observer = EventObserver()

        async def handler(update: Update) -> None:
            pass

        returned = observer.register(handler)
        assert returned is handler


# ---------------------------------------------------------------------------
# Router.propagate
# ---------------------------------------------------------------------------


class TestRouterPropagate:
    async def test_text_update_triggers_message_observer(self) -> None:
        router = Router()
        calls: list[str] = []

        @router.message(_AlwaysPassFilter())
        async def on_msg(update: Update) -> str:
            calls.append("message")
            return "msg"

        result = await router.propagate(make_update("hello"), {})
        assert result == "msg"
        assert calls == ["message"]

    async def test_bot_request_update_triggers_bot_request_observer(self) -> None:
        router = Router()
        calls: list[str] = []

        upd = make_update(
            text=None,
            bot_request={"server_action": {"name": "click", "payload": {}}},
        )

        @router.bot_request(_AlwaysPassFilter())
        async def on_req(update: Update) -> str:
            calls.append("bot_request")
            return "req"

        result = await router.propagate(upd, {})
        assert result == "req"
        assert calls == ["bot_request"]

    async def test_bot_request_observer_checked_before_message(self) -> None:
        """When an update has bot_request, bot_request observer runs first."""
        router = Router()
        order: list[str] = []

        upd = make_update(
            text="also has text",
            bot_request={"server_action": {"name": "x", "payload": {}}},
        )

        @router.bot_request(_AlwaysPassFilter())
        async def on_req(update: Update) -> str:
            order.append("bot_request")
            return "req"

        @router.message(_AlwaysPassFilter())
        async def on_msg(update: Update) -> str:
            order.append("message")
            return "msg"

        result = await router.propagate(upd, {})
        assert result == "req"
        assert order == ["bot_request"]

    async def test_no_match_returns_unhandled(self) -> None:
        router = Router()

        @router.message(_AlwaysFailFilter())
        async def handler(update: Update) -> str:
            return "nope"

        assert await router.propagate(make_update(), {}) is _UNHANDLED

    async def test_sub_router_reached_when_parent_misses(self) -> None:
        parent = Router(name="parent")
        child = Router(name="child")
        parent.include_router(child)

        @parent.message(_AlwaysFailFilter())
        async def parent_handler(update: Update) -> str:
            return "parent"

        @child.message(_AlwaysPassFilter())
        async def child_handler(update: Update) -> str:
            return "child"

        result = await parent.propagate(make_update(), {})
        assert result == "child"

    async def test_depth_first_sub_router_order(self) -> None:
        """Sub-routers are traversed in registration order, depth-first."""
        root = Router(name="root")
        first_child = Router(name="first")
        second_child = Router(name="second")
        grandchild = Router(name="grandchild")

        root.include_router(first_child)
        root.include_router(second_child)
        first_child.include_router(grandchild)

        visited: list[str] = []

        @root.message(_AlwaysFailFilter())
        async def root_h(update: Update) -> str:
            visited.append("root")
            return "root"

        @first_child.message(_AlwaysFailFilter())
        async def first_h(update: Update) -> str:
            visited.append("first")
            return "first"

        @grandchild.message(_AlwaysPassFilter())
        async def grand_h(update: Update) -> str:
            visited.append("grandchild")
            return "grandchild"

        @second_child.message(_AlwaysPassFilter())
        async def second_h(update: Update) -> str:
            visited.append("second")
            return "second"

        result = await root.propagate(make_update(), {})
        # Depth-first: root → first_child → grandchild (matches here, stops)
        assert result == "grandchild"
        assert visited == ["grandchild"]

    async def test_parent_handler_wins_over_sub_router(self) -> None:
        parent = Router(name="parent")
        child = Router(name="child")
        parent.include_router(child)

        @parent.message(_AlwaysPassFilter())
        async def parent_handler(update: Update) -> str:
            return "parent"

        @child.message(_AlwaysPassFilter())
        async def child_handler(update: Update) -> str:
            return "child"

        result = await parent.propagate(make_update(), {})
        assert result == "parent"


# ---------------------------------------------------------------------------
# Dispatcher.feed_update — DI injection
# ---------------------------------------------------------------------------


class TestDispatcherFeedUpdate:
    async def test_injects_bot_update_chat_state(self) -> None:
        dp = Dispatcher()
        received: dict[str, Any] = {}

        @dp.message(_AlwaysPassFilter())
        async def handler(update: Update, bot: Any, chat: Any, state: FSMContext) -> None:
            received["update"] = update
            received["bot"] = bot
            received["chat"] = chat
            received["state"] = state

        bot = _make_bot_stub()
        upd = make_update("hi")
        await dp.feed_update(bot, upd)

        assert received["update"] is upd
        assert received["bot"] is bot
        assert received["chat"] is upd.chat
        assert isinstance(received["state"], FSMContext)

    async def test_injects_user_when_from_user_present(self) -> None:
        dp = Dispatcher()
        received: dict[str, Any] = {}

        @dp.message(_AlwaysPassFilter())
        async def handler(user: Any) -> None:
            received["user"] = user

        bot = _make_bot_stub()
        upd = make_update("hello")
        await dp.feed_update(bot, upd)

        assert received["user"] is upd.from_user

    async def test_fsm_state_is_per_chat_user(self) -> None:
        """Two different (chat, user) pairs must get independent FSM contexts."""
        dp = Dispatcher()
        states_seen: list[str | None] = []

        @dp.message(_AlwaysPassFilter())
        async def handler(state: FSMContext) -> None:
            states_seen.append(await state.get_state())

        bot = _make_bot_stub()

        upd1 = make_update("hi", update_id=1)
        upd2 = make_update(
            "hi",
            update_id=2,
            **{
                "chat": {"id": "chat-2", "type": "private"},
                "from": {"id": "user-2", "login": "other@org.ru", "display_name": "Other"},
            },
        )

        # Set state for upd1's chat/user via a separate context
        bot_id = hashlib.sha256(bot.token.encode()).hexdigest()[:16]
        key1 = StorageKey(bot_id=bot_id, chat_id="chat-1", user_id="user-1")
        await dp.storage.set_state(key1, "SomeState")

        await dp.feed_update(bot, upd1)
        await dp.feed_update(bot, upd2)

        assert states_seen[0] == "SomeState"
        assert states_seen[1] is None  # different key

    async def test_custom_dependency_injected(self) -> None:
        dp = Dispatcher()
        received: dict[str, Any] = {}

        class FakeDB:
            pass

        async def get_db() -> FakeDB:
            return FakeDB()

        dp.dependency(FakeDB, factory=get_db)

        @dp.message(_AlwaysPassFilter())
        async def handler(fakedb: FakeDB) -> None:
            received["db"] = fakedb

        bot = _make_bot_stub()
        await dp.feed_update(bot, make_update())
        assert isinstance(received["db"], FakeDB)

    async def test_async_generator_dependency_cleanup_called(self) -> None:
        dp = Dispatcher()
        cleanup_called: list[bool] = []

        class Resource:
            pass

        async def get_resource():
            try:
                yield Resource()
            finally:
                cleanup_called.append(True)

        dp.dependency(Resource, factory=get_resource)

        @dp.message(_AlwaysPassFilter())
        async def handler(resource: Resource) -> None:
            pass

        bot = _make_bot_stub()
        await dp.feed_update(bot, make_update())
        assert cleanup_called == [True]

    async def test_exceptions_in_handler_are_swallowed(self) -> None:
        """feed_update must not propagate handler exceptions to the caller."""
        dp = Dispatcher()

        @dp.message(_AlwaysPassFilter())
        async def handler(update: Update) -> None:
            raise RuntimeError("boom")

        bot = _make_bot_stub()
        # Should not raise
        await dp.feed_update(bot, make_update())


class TestFSMStrategy:
    """Tests for FSMStrategy wiring in Dispatcher."""

    async def test_user_in_chat_strategy_is_default(self) -> None:
        """Default strategy keys by (bot_id, chat_id, user_id)."""
        dp = Dispatcher()
        assert dp.fsm_strategy == FSMStrategy.USER_IN_CHAT

        states: list[str | None] = []

        @dp.message(_AlwaysPassFilter())
        async def handler(state: FSMContext) -> None:
            states.append(await state.get_state())

        bot = _make_bot_stub()
        bot_id = hashlib.sha256(bot.token.encode()).hexdigest()[:16]

        # Set state for user-1 in chat-1
        key = StorageKey(bot_id=bot_id, chat_id="chat-1", user_id="user-1")
        await dp.storage.set_state(key, "active")

        upd1 = make_update()  # default: chat-1, user-1
        upd2 = make_update(
            **{
                "from": {"id": "user-2", "login": "other@org.ru", "display_name": "Other"},
            }
        )

        await dp.feed_update(bot, upd1)
        await dp.feed_update(bot, upd2)

        assert states[0] == "active"
        assert states[1] is None  # different user → different key

    async def test_chat_strategy_shares_state_across_users(self) -> None:
        """CHAT strategy keys by (bot_id, chat_id, '') — shared per chat."""
        dp = Dispatcher(fsm_strategy=FSMStrategy.CHAT)

        states: list[str | None] = []

        @dp.message(_AlwaysPassFilter())
        async def handler(state: FSMContext) -> None:
            states.append(await state.get_state())

        bot = _make_bot_stub()
        bot_id = hashlib.sha256(bot.token.encode()).hexdigest()[:16]

        # Set shared chat state
        key = StorageKey(bot_id=bot_id, chat_id="chat-1", user_id="")
        await dp.storage.set_state(key, "shared")

        upd1 = make_update()  # user-1 in chat-1
        upd2 = make_update(
            **{
                "from": {"id": "user-2", "login": "other@org.ru", "display_name": "Other"},
            }
        )  # user-2 in chat-1

        await dp.feed_update(bot, upd1)
        await dp.feed_update(bot, upd2)

        # Both users see the same state
        assert states[0] == "shared"
        assert states[1] == "shared"

    async def test_global_user_strategy_shares_state_across_chats(self) -> None:
        """GLOBAL_USER strategy keys by (bot_id, '', user_id) — user state across chats."""
        dp = Dispatcher(fsm_strategy=FSMStrategy.GLOBAL_USER)

        states: list[str | None] = []

        @dp.message(_AlwaysPassFilter())
        async def handler(state: FSMContext) -> None:
            states.append(await state.get_state())

        bot = _make_bot_stub()
        bot_id = hashlib.sha256(bot.token.encode()).hexdigest()[:16]

        # Set global user state
        key = StorageKey(bot_id=bot_id, chat_id="", user_id="user-1")
        await dp.storage.set_state(key, "global")

        upd1 = make_update()  # user-1 in chat-1
        upd2 = make_update(chat={"id": "chat-2", "type": "group"})  # user-1 in chat-2

        await dp.feed_update(bot, upd1)
        await dp.feed_update(bot, upd2)

        # Same user in different chats sees the same state
        assert states[0] == "global"
        assert states[1] == "global"
