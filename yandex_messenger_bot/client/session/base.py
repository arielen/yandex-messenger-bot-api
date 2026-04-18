from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, TypeVar

from yandex_messenger_bot.methods.base import YaBotMethod

TResult = TypeVar("TResult")


class BaseSession(ABC):
    """Abstract HTTP session for making API requests."""

    @abstractmethod
    async def make_request(self, token: str, method: YaBotMethod[TResult]) -> Any:
        """Execute an API method and return raw response data."""
        ...

    @abstractmethod
    async def stream_content(self, token: str, url: str) -> AsyncIterator[bytes]:
        """Stream content from a URL as an async iterator of byte chunks."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the session and release resources."""
        ...
