"""MockedSession and MockedBot — test doubles for unit testing."""

from __future__ import annotations

from collections import deque
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from yandex_messenger_bot.client.bot import Bot
from yandex_messenger_bot.client.session.base import BaseSession
from yandex_messenger_bot.methods.base import YaBotMethod


class MockedSession(BaseSession):
    """Test session that queues pre-programmed responses and records requests.

    Usage::

        session = MockedSession()
        session.add_result({"message_id": 42})
        result = await session.make_request("token", SendText(...))
    """

    def __init__(self) -> None:
        self.responses: deque[Any] = deque()
        self.requests: deque[YaBotMethod] = deque()  # type: ignore[type-arg]
        self.closed = True
        self._stream_chunks: list[bytes] = [b"test-content"]

    def add_result(self, result: Any) -> None:
        """Enqueue *result* to be returned by the next :meth:`make_request` call."""
        self.responses.append(result)

    def get_request(self) -> YaBotMethod:  # type: ignore[type-arg]
        """Pop and return the oldest recorded request."""
        return self.requests.popleft()

    def set_stream_chunks(self, chunks: list[bytes]) -> None:
        """Set the byte chunks yielded by :meth:`stream_content`."""
        self._stream_chunks = chunks

    async def make_request(self, token: str, method: YaBotMethod) -> Any:  # type: ignore[type-arg]
        self.closed = False
        self.requests.append(method)
        if self.responses:
            return self.responses.popleft()
        # Fall back to a sensible default based on the method's return type
        returning = method.__returning__
        if returning is bytes:
            return b""
        if hasattr(returning, "model_validate"):
            # Build a minimal valid instance.  Most result types need at least
            # one integer field — try message_id first, then ok.
            try:
                return returning.model_validate({"message_id": 0})
            except Exception:
                pass
            try:
                return returning.model_validate({"ok": True})
            except Exception:
                pass
            try:
                return returning.model_validate({})
            except Exception:
                pass
        return None

    async def stream_content(self, token: str, url: str) -> AsyncIterator[bytes]:
        for chunk in self._stream_chunks:
            yield chunk

    async def close(self) -> None:
        self.closed = True


class MockedBot(Bot):
    """Bot subclass that uses :class:`MockedSession` for all API calls."""

    if TYPE_CHECKING:
        _session: MockedSession

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            token=kwargs.pop("token", "test-token-12345"),
            session=MockedSession(),
            **kwargs,
        )

    def add_result(self, result: Any) -> None:
        """Enqueue *result* for the next API call made by this bot."""
        self._session.add_result(result)

    def get_request(self) -> YaBotMethod:  # type: ignore[type-arg]
        """Pop and return the oldest recorded request."""
        return self._session.get_request()

    @property
    def session(self) -> MockedSession:
        return self._session
