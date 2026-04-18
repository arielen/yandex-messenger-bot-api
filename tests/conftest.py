"""Shared test fixtures and helpers."""

from __future__ import annotations

from typing import Any

import pytest

from tests.mocked_bot import MockedBot
from yandex_messenger_bot.dispatcher.dispatcher import Dispatcher
from yandex_messenger_bot.types.update import Update


def make_update(text: str | None = "hello", update_id: int = 1, **kwargs: Any) -> Update:
    """Build a minimal Update for use in tests."""
    payload: dict[str, Any] = {
        "update_id": update_id,
        "message_id": 123,
        "timestamp": 1700000000,
        "chat": {"id": "chat-1", "type": "private"},
        "from": {"id": "user-1", "login": "test@org.ru", "display_name": "Test"},
        "text": text,
    }
    payload.update(kwargs)
    return Update.model_validate(payload)


@pytest.fixture
def bot() -> MockedBot:
    """Return a fresh MockedBot for each test."""
    return MockedBot()


@pytest.fixture
def dispatcher() -> Dispatcher:
    """Return a fresh Dispatcher for each test."""
    return Dispatcher()
