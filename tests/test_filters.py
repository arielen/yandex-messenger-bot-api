"""Tests for all filter classes and the BaseFilter logical combinators."""

from __future__ import annotations

from typing import Any

from tests.conftest import make_update
from yandex_messenger_bot.filters.base import BaseFilter
from yandex_messenger_bot.filters.callback import ServerActionFilter
from yandex_messenger_bot.filters.command import CommandFilter, CommandObject
from yandex_messenger_bot.filters.state import StateFilter
from yandex_messenger_bot.fsm.context import FSMContext
from yandex_messenger_bot.fsm.state import State, StatesGroup
from yandex_messenger_bot.fsm.storage.base import StorageKey
from yandex_messenger_bot.fsm.storage.memory import MemoryStorage
from yandex_messenger_bot.types.update import Update

# ---------------------------------------------------------------------------
# CommandFilter
# ---------------------------------------------------------------------------


class TestCommandFilter:
    async def test_matches_simple_command(self) -> None:
        f = CommandFilter("start")
        result = await f(make_update("/start"))
        assert isinstance(result, dict)
        cmd: CommandObject = result["command"]
        assert cmd.command == "start"
        assert cmd.args == ""

    async def test_command_with_slash_prefix_in_filter(self) -> None:
        """Filter initialised with '/start' should work the same as 'start'."""
        f = CommandFilter("/start")
        result = await f(make_update("/start"))
        assert result is not False

    async def test_extracts_args(self) -> None:
        f = CommandFilter("start")
        result = await f(make_update("/start hello world"))
        assert isinstance(result, dict)
        assert result["command"].args == "hello world"

    async def test_args_are_stripped(self) -> None:
        f = CommandFilter("start")
        result = await f(make_update("/start   spaces   "))
        assert isinstance(result, dict)
        assert result["command"].args == "spaces"

    async def test_case_insensitive_by_default(self) -> None:
        f = CommandFilter("start")
        assert await f(make_update("/START")) is not False
        assert await f(make_update("/Start")) is not False

    async def test_case_sensitive_mode(self) -> None:
        f = CommandFilter("start", ignore_case=False)
        assert await f(make_update("/START")) is False
        assert await f(make_update("/start")) is not False

    async def test_multiple_commands(self) -> None:
        f = CommandFilter("start", "help")
        assert await f(make_update("/start")) is not False
        assert await f(make_update("/help")) is not False
        assert await f(make_update("/other")) is False

    async def test_does_not_match_non_command_text(self) -> None:
        f = CommandFilter("start")
        assert await f(make_update("just a regular message")) is False

    async def test_does_not_match_empty_text(self) -> None:
        f = CommandFilter("start")
        assert await f(make_update("")) is False

    async def test_does_not_match_none_text(self) -> None:
        f = CommandFilter("start")
        assert await f(make_update(text=None)) is False

    async def test_partial_command_not_matched(self) -> None:
        """'/starter' should NOT match a filter for '/start' — word boundary check."""
        f = CommandFilter("start")
        result = await f(make_update("/starter"))
        assert result is False


# ---------------------------------------------------------------------------
# ServerActionFilter
# ---------------------------------------------------------------------------


def _make_bot_request_update(action_name: str, payload: dict[str, Any] | None = None) -> Update:
    return make_update(
        text=None,
        bot_request={
            "server_action": {
                "name": action_name,
                "payload": payload or {},
            }
        },
    )


class TestServerActionFilter:
    async def test_matches_named_action(self) -> None:
        f = ServerActionFilter("submit_form")
        result = await f(_make_bot_request_update("submit_form"))
        assert isinstance(result, dict)
        assert result["server_action"].name == "submit_form"

    async def test_injects_server_action_object(self) -> None:
        f = ServerActionFilter("do_thing")
        result = await f(_make_bot_request_update("do_thing", payload={"key": "val"}))
        assert isinstance(result, dict)
        assert result["server_action"].payload == {"key": "val"}

    async def test_does_not_match_different_action(self) -> None:
        f = ServerActionFilter("submit_form")
        assert await f(_make_bot_request_update("other_action")) is False

    async def test_no_bot_request_returns_false(self) -> None:
        f = ServerActionFilter("submit_form")
        assert await f(make_update("plain text")) is False

    async def test_no_server_action_returns_false(self) -> None:
        """bot_request present but server_action is None."""
        update = make_update(text=None, bot_request={"element_id": "btn-1"})
        f = ServerActionFilter("submit_form")
        assert await f(update) is False

    async def test_no_action_names_matches_any_action(self) -> None:
        """ServerActionFilter() with no arguments matches any server action."""
        f = ServerActionFilter()
        result = await f(_make_bot_request_update("anything"))
        assert isinstance(result, dict)
        assert result["server_action"].name == "anything"

    async def test_multiple_action_names(self) -> None:
        f = ServerActionFilter("a", "b", "c")
        assert await f(_make_bot_request_update("a")) is not False
        assert await f(_make_bot_request_update("b")) is not False
        assert await f(_make_bot_request_update("d")) is False


# ---------------------------------------------------------------------------
# StateFilter
# ---------------------------------------------------------------------------


def _make_fsm_ctx(state_name: str | None = None) -> FSMContext:
    storage = MemoryStorage()
    key = StorageKey(bot_id="bot", chat_id="chat", user_id="user")
    ctx = FSMContext(storage=storage, key=key)
    # Inject state synchronously via the underlying storage dict
    storage._states[key] = state_name
    return ctx


class TestStateFilter:
    async def test_matches_current_state_object(self) -> None:
        class Form(StatesGroup):
            name = State()

        ctx = _make_fsm_ctx("Form:name")
        f = StateFilter(Form.name)
        update = make_update()
        result = await f(update, state=ctx)
        assert result is True

    async def test_does_not_match_different_state(self) -> None:
        class Form(StatesGroup):
            name = State()
            email = State()

        ctx = _make_fsm_ctx("Form:email")
        f = StateFilter(Form.name)
        result = await f(make_update(), state=ctx)
        assert result is False

    async def test_matches_state_by_string(self) -> None:
        ctx = _make_fsm_ctx("SomeGroup:step")
        f = StateFilter("SomeGroup:step")
        result = await f(make_update(), state=ctx)
        assert result is True

    async def test_matches_none_state(self) -> None:
        ctx = _make_fsm_ctx(None)
        f = StateFilter(None)
        result = await f(make_update(), state=ctx)
        assert result is True

    async def test_no_context_in_data_returns_false(self) -> None:
        class Form(StatesGroup):
            step = State()

        f = StateFilter(Form.step)
        result = await f(make_update())  # no state= kwarg
        assert result is False

    async def test_multiple_states_any_match(self) -> None:
        class Flow(StatesGroup):
            a = State()
            b = State()

        ctx = _make_fsm_ctx("Flow:b")
        f = StateFilter(Flow.a, Flow.b)
        result = await f(make_update(), state=ctx)
        assert result is True


# ---------------------------------------------------------------------------
# BaseFilter combinators: &, |, ~
# ---------------------------------------------------------------------------


class _TrueFilter(BaseFilter):
    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        return True


class _FalseFilter(BaseFilter):
    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        return False


class _DictFilter(BaseFilter):
    """Always returns a dict with a fixed key."""

    def __init__(self, key: str, value: Any) -> None:
        self._key = key
        self._value = value

    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        return {self._key: self._value}


class TestFilterCombinators:
    async def test_and_both_true(self) -> None:
        f = _TrueFilter() & _TrueFilter()
        assert await f(make_update()) is not False

    async def test_and_left_false(self) -> None:
        f = _FalseFilter() & _TrueFilter()
        assert await f(make_update()) is False

    async def test_and_right_false(self) -> None:
        f = _TrueFilter() & _FalseFilter()
        assert await f(make_update()) is False

    async def test_and_merges_dicts(self) -> None:
        f = _DictFilter("a", 1) & _DictFilter("b", 2)
        result = await f(make_update())
        assert isinstance(result, dict)
        assert result == {"a": 1, "b": 2}

    async def test_and_right_dict_wins_on_key_conflict(self) -> None:
        f = _DictFilter("k", "left") & _DictFilter("k", "right")
        result = await f(make_update())
        assert result == {"k": "right"}

    async def test_and_with_dict_and_false(self) -> None:
        f = _DictFilter("x", 1) & _FalseFilter()
        assert await f(make_update()) is False

    async def test_or_left_true(self) -> None:
        f = _TrueFilter() | _FalseFilter()
        assert await f(make_update()) is not False

    async def test_or_right_true(self) -> None:
        f = _FalseFilter() | _TrueFilter()
        assert await f(make_update()) is not False

    async def test_or_both_false(self) -> None:
        f = _FalseFilter() | _FalseFilter()
        assert await f(make_update()) is False

    async def test_or_returns_first_truthy_dict(self) -> None:
        f = _DictFilter("first", 1) | _DictFilter("second", 2)
        result = await f(make_update())
        # Left wins
        assert result == {"first": 1}

    async def test_invert_true_becomes_false(self) -> None:
        f = ~_TrueFilter()
        assert await f(make_update()) is False

    async def test_invert_false_becomes_true(self) -> None:
        f = ~_FalseFilter()
        assert await f(make_update()) is True

    async def test_invert_dict_becomes_false(self) -> None:
        """A dict is truthy, so inversion should yield False."""
        f = ~_DictFilter("x", 1)
        assert await f(make_update()) is False

    async def test_chained_combinators(self) -> None:
        """(True & True) | False should pass."""
        f = (_TrueFilter() & _TrueFilter()) | _FalseFilter()
        assert await f(make_update()) is not False

    async def test_not_of_and(self) -> None:
        """~(True & False) should be True."""
        f = ~(_TrueFilter() & _FalseFilter())
        assert await f(make_update()) is True
