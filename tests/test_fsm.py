"""Tests for the FSM subsystem: StatesGroup, State, FSMContext, MemoryStorage."""

from __future__ import annotations

import pytest

from yandex_messenger_bot.fsm.context import FSMContext
from yandex_messenger_bot.fsm.state import State, StatesGroup
from yandex_messenger_bot.fsm.storage.base import StorageKey
from yandex_messenger_bot.fsm.storage.memory import MemoryStorage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_key(bot: str = "bot1", chat: str = "chat1", user: str = "user1") -> StorageKey:
    return StorageKey(bot_id=bot, chat_id=chat, user_id=user)


def make_ctx(storage: MemoryStorage | None = None, key: StorageKey | None = None) -> FSMContext:
    return FSMContext(storage=storage or MemoryStorage(), key=key or make_key())


# ---------------------------------------------------------------------------
# StatesGroup metaclass
# ---------------------------------------------------------------------------


class TestStatesGroupMeta:
    def test_state_names_are_auto_assigned(self) -> None:
        class Form(StatesGroup):
            name = State()
            age = State()

        assert Form.name.state_name == "Form:name"
        assert Form.age.state_name == "Form:age"

    def test_all_states_tuple_is_populated(self) -> None:
        class Wizard(StatesGroup):
            step1 = State()
            step2 = State()
            step3 = State()

        assert len(Wizard.__all_states__) == 3

    def test_all_state_names_matches_states(self) -> None:
        class Order(StatesGroup):
            confirm = State()
            pay = State()

        assert set(Order.__all_state_names__) == {"Order:confirm", "Order:pay"}

    def test_group_attribute_set_on_state(self) -> None:
        class Reg(StatesGroup):
            phone = State()

        assert Reg.phone._group is Reg

    def test_base_class_has_empty_tuples(self) -> None:
        """The StatesGroup base itself must not grow __all_states__."""
        assert StatesGroup.__all_states__ == ()
        assert StatesGroup.__all_state_names__ == ()

    def test_state_without_group_raises(self) -> None:
        orphan = State()
        with pytest.raises(RuntimeError, match="StatesGroup"):
            _ = orphan.state_name

    def test_two_groups_do_not_share_states(self) -> None:
        class A(StatesGroup):
            x = State()

        class B(StatesGroup):
            x = State()

        assert A.x.state_name == "A:x"
        assert B.x.state_name == "B:x"
        assert A.x is not B.x


# ---------------------------------------------------------------------------
# StatesGroup.__contains__
# ---------------------------------------------------------------------------


class TestStatesGroupContains:
    def test_contains_existing_state(self) -> None:
        class Login(StatesGroup):
            password = State()

        # __contains__ is defined on instances, not the class itself
        assert "Login:password" in Login()

    def test_not_contains_foreign_state(self) -> None:
        class Login(StatesGroup):
            password = State()

        assert "Login:email" not in Login()

    def test_contains_checks_full_qualified_name(self) -> None:
        class A(StatesGroup):
            s = State()

        class B(StatesGroup):
            s = State()

        # Each instance only knows its own group's states
        assert "B:s" not in A()
        assert "A:s" not in B()

    def test_all_state_names_also_usable_for_membership(self) -> None:
        """Class attribute __all_state_names__ is available for class-level checks."""

        class Reg(StatesGroup):
            step1 = State()
            step2 = State()

        assert "Reg:step1" in Reg.__all_state_names__
        assert "Reg:missing" not in Reg.__all_state_names__


# ---------------------------------------------------------------------------
# FSMContext full lifecycle
# ---------------------------------------------------------------------------


class TestFSMContextLifecycle:
    async def test_initial_state_is_none(self) -> None:
        ctx = make_ctx()
        assert await ctx.get_state() is None

    async def test_set_and_get_state_object(self) -> None:
        class S(StatesGroup):
            first = State()

        ctx = make_ctx()
        await ctx.set_state(S.first)
        assert await ctx.get_state() == "S:first"

    async def test_set_state_by_string(self) -> None:
        ctx = make_ctx()
        await ctx.set_state("some:state")
        assert await ctx.get_state() == "some:state"

    async def test_set_state_none_clears_state(self) -> None:
        class S(StatesGroup):
            step = State()

        ctx = make_ctx()
        await ctx.set_state(S.step)
        await ctx.set_state(None)
        assert await ctx.get_state() is None

    async def test_update_data_merges_incrementally(self) -> None:
        ctx = make_ctx()
        await ctx.update_data(name="Alice")
        await ctx.update_data(age=30)
        data = await ctx.get_data()
        assert data == {"name": "Alice", "age": 30}

    async def test_update_data_overwrites_existing_key(self) -> None:
        ctx = make_ctx()
        await ctx.update_data(count=1)
        await ctx.update_data(count=2)
        assert (await ctx.get_data())["count"] == 2

    async def test_set_data_replaces_entirely(self) -> None:
        ctx = make_ctx()
        await ctx.update_data(a=1, b=2)
        await ctx.set_data({"c": 3})
        assert await ctx.get_data() == {"c": 3}

    async def test_clear_resets_state_and_data(self) -> None:
        class S(StatesGroup):
            step = State()

        ctx = make_ctx()
        await ctx.set_state(S.step)
        await ctx.update_data(x=42)
        await ctx.clear()

        assert await ctx.get_state() is None
        assert await ctx.get_data() == {}

    async def test_get_data_returns_shallow_copy(self) -> None:
        """get_data returns a shallow copy: adding a top-level key doesn't
        affect storage, but mutating a nested mutable value does (shallow copy
        semantics — documented behaviour of MemoryStorage)."""
        ctx = make_ctx()
        await ctx.set_data({"score": 10})
        data = await ctx.get_data()
        # Adding a new key to the returned dict must NOT touch stored data
        data["extra"] = "injected"
        assert "extra" not in (await ctx.get_data())


# ---------------------------------------------------------------------------
# MemoryStorage isolation
# ---------------------------------------------------------------------------


class TestMemoryStorageIsolation:
    async def test_different_keys_do_not_interfere(self) -> None:
        storage = MemoryStorage()
        key_a = make_key(user="alice")
        key_b = make_key(user="bob")

        await storage.set_state(key_a, "state_a")
        await storage.set_state(key_b, "state_b")

        assert await storage.get_state(key_a) == "state_a"
        assert await storage.get_state(key_b) == "state_b"

    async def test_data_isolation_between_keys(self) -> None:
        storage = MemoryStorage()
        key_a = make_key(chat="chat-a")
        key_b = make_key(chat="chat-b")

        await storage.set_data(key_a, {"x": 1})
        await storage.set_data(key_b, {"x": 99})

        assert (await storage.get_data(key_a))["x"] == 1
        assert (await storage.get_data(key_b))["x"] == 99

    async def test_unknown_key_returns_defaults(self) -> None:
        storage = MemoryStorage()
        key = make_key(user="ghost")

        assert await storage.get_state(key) is None
        assert await storage.get_data(key) == {}

    async def test_close_clears_all(self) -> None:
        storage = MemoryStorage()
        key = make_key()
        await storage.set_state(key, "alive")
        await storage.set_data(key, {"val": 1})

        await storage.close()

        assert await storage.get_state(key) is None
        assert await storage.get_data(key) == {}

    async def test_set_data_stores_copy(self) -> None:
        """External mutation of the dict passed to set_data must not affect stored value."""
        storage = MemoryStorage()
        key = make_key()
        original = {"k": "v"}
        await storage.set_data(key, original)
        original["k"] = "mutated"
        assert (await storage.get_data(key))["k"] == "v"
