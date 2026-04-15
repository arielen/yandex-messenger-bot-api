"""Tests for WebhookHandler (aiohttp_server.py)."""

from __future__ import annotations

import json
import warnings
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from tests.mocked_bot import MockedBot
from yandex_messenger_bot.dispatcher.dispatcher import Dispatcher
from yandex_messenger_bot.webhook.aiohttp_server import WebhookHandler

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_UPDATE: dict[str, Any] = {
    "update_id": 1,
    "message_id": 100,
    "timestamp": 1700000000,
    "chat": {"id": "chat-1", "type": "private"},
    "from": {"id": "user-1", "login": "test@org.ru", "display_name": "Test"},
    "text": "hello",
}


def _make_app(
    *,
    secret_token: str | None = None,
    max_body_size: int = 1_048_576,
    path: str = "/webhook",
    dispatcher: Dispatcher | None = None,
    bot: MockedBot | None = None,
) -> tuple[web.Application, Dispatcher, MockedBot]:
    """Build an aiohttp Application with WebhookHandler registered."""
    dp = dispatcher or Dispatcher()
    b = bot or MockedBot()
    app = web.Application()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        handler = WebhookHandler(dp, b, secret_token=secret_token, max_body_size=max_body_size)
    handler.setup(app, path=path)
    return app, dp, b


async def _make_client(
    *,
    secret_token: str | None = None,
    max_body_size: int = 1_048_576,
    dispatcher: Dispatcher | None = None,
    bot: MockedBot | None = None,
) -> tuple[TestClient, Dispatcher, MockedBot]:
    app, dp, b = _make_app(
        secret_token=secret_token,
        max_body_size=max_body_size,
        dispatcher=dispatcher,
        bot=bot,
    )
    client = TestClient(TestServer(app))
    await client.start_server()
    return client, dp, b


async def _post(
    client: TestClient,
    body: bytes | dict[str, Any] = _MINIMAL_UPDATE,
    *,
    path: str = "/webhook",
    content_type: str = "application/json",
    headers: dict[str, str] | None = None,
) -> Any:
    """Send a POST request to the webhook endpoint."""
    raw_body = json.dumps(body).encode() if isinstance(body, dict) else body

    _headers = {"Content-Type": content_type}
    if headers:
        _headers.update(headers)

    return await client.post(path, data=raw_body, headers=_headers)


# ---------------------------------------------------------------------------
# WebhookHandler construction
# ---------------------------------------------------------------------------


class TestWebhookHandlerConstruction:
    def test_warns_when_no_secret_token(self) -> None:
        dp = Dispatcher()
        bot = MockedBot()
        with pytest.warns(UserWarning, match="secret_token"):
            WebhookHandler(dp, bot)

    def test_no_warning_when_secret_token_provided(self) -> None:
        dp = Dispatcher()
        bot = MockedBot()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            WebhookHandler(dp, bot, secret_token="s3cret")


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------


class TestWebhookAuthentication:
    async def test_no_secret_token_required_returns_200(self) -> None:
        client, _, _ = await _make_client()
        try:
            resp = await _post(client)
            assert resp.status == 200
        finally:
            await client.close()

    async def test_correct_secret_token_returns_200(self) -> None:
        client, _, _ = await _make_client(secret_token="my-secret")
        try:
            resp = await _post(client, headers={"X-Secret-Token": "my-secret"})
            assert resp.status == 200
        finally:
            await client.close()

    async def test_missing_secret_token_returns_401(self) -> None:
        client, _, _ = await _make_client(secret_token="my-secret")
        try:
            resp = await _post(client)
            assert resp.status == 401
        finally:
            await client.close()

    async def test_wrong_secret_token_returns_401(self) -> None:
        client, _, _ = await _make_client(secret_token="correct")
        try:
            resp = await _post(client, headers={"X-Secret-Token": "wrong"})
            assert resp.status == 401
        finally:
            await client.close()

    async def test_empty_secret_token_header_returns_401(self) -> None:
        client, _, _ = await _make_client(secret_token="nonempty")
        try:
            resp = await _post(client, headers={"X-Secret-Token": ""})
            assert resp.status == 401
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# Body size guard
# ---------------------------------------------------------------------------


class TestWebhookBodySize:
    async def test_small_body_within_limit_returns_200(self) -> None:
        client, _, _ = await _make_client(max_body_size=1_048_576)
        try:
            resp = await _post(client)
            assert resp.status == 200
        finally:
            await client.close()

    async def test_body_exceeds_limit_returns_413(self) -> None:
        """A body larger than max_body_size must be rejected with 413."""
        client, _, _ = await _make_client(max_body_size=10)
        try:
            # _MINIMAL_UPDATE JSON is much larger than 10 bytes
            resp = await _post(client)
            assert resp.status == 413
        finally:
            await client.close()

    async def test_body_exactly_at_limit_returns_200(self) -> None:
        """A body of exactly max_body_size bytes must be accepted."""
        body = json.dumps(_MINIMAL_UPDATE).encode()
        client, _, _ = await _make_client(max_body_size=len(body))
        try:
            resp = await _post(client)
            assert resp.status == 200
        finally:
            await client.close()

    async def test_body_one_byte_over_limit_returns_413(self) -> None:
        """A body of max_body_size + 1 must be rejected."""
        body = json.dumps(_MINIMAL_UPDATE).encode()
        client, _, _ = await _make_client(max_body_size=len(body) - 1)
        try:
            resp = await _post(client)
            assert resp.status == 413
        finally:
            await client.close()

    async def test_large_body_with_generous_limit_is_accepted(self) -> None:
        """With a large limit, large payloads must be accepted."""
        client, _, _ = await _make_client(max_body_size=10_000_000)
        try:
            resp = await _post(client)
            assert resp.status == 200
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# Content-Type check
# ---------------------------------------------------------------------------


class TestWebhookContentType:
    async def test_application_json_returns_200(self) -> None:
        client, _, _ = await _make_client()
        try:
            resp = await _post(client, content_type="application/json")
            assert resp.status == 200
        finally:
            await client.close()

    async def test_application_json_with_charset_returns_200(self) -> None:
        """application/json; charset=utf-8 must also be accepted."""
        client, _, _ = await _make_client()
        try:
            resp = await _post(client, content_type="application/json; charset=utf-8")
            assert resp.status == 200
        finally:
            await client.close()

    async def test_text_plain_returns_415(self) -> None:
        client, _, _ = await _make_client()
        try:
            resp = await _post(client, body=b"{}", content_type="text/plain")
            assert resp.status == 415
        finally:
            await client.close()

    async def test_multipart_returns_415(self) -> None:
        client, _, _ = await _make_client()
        try:
            resp = await _post(client, body=b"data", content_type="multipart/form-data")
            assert resp.status == 415
        finally:
            await client.close()

    async def test_octet_stream_returns_415(self) -> None:
        client, _, _ = await _make_client()
        try:
            resp = await _post(client, body=b"\x00\x01", content_type="application/octet-stream")
            assert resp.status == 415
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# Update dispatch
# ---------------------------------------------------------------------------


class TestWebhookDispatch:
    async def test_valid_update_dispatches_to_feed_update(self) -> None:
        dp = Dispatcher()
        received_ids: list[int] = []

        @dp.message()
        async def on_msg(update: Any) -> None:
            received_ids.append(update.update_id)

        client, _, _ = await _make_client(dispatcher=dp)
        try:
            resp = await _post(client)
            assert resp.status == 200
            assert received_ids == [1]
        finally:
            await client.close()

    async def test_valid_update_returns_200(self) -> None:
        client, _, _ = await _make_client()
        try:
            resp = await _post(client)
            assert resp.status == 200
        finally:
            await client.close()

    async def test_malformed_json_returns_200(self) -> None:
        """Parser errors must not surface as non-200; handler swallows them."""
        client, _, _ = await _make_client()
        try:
            resp = await _post(client, body=b"not-json")
            assert resp.status == 200
        finally:
            await client.close()

    async def test_invalid_update_structure_returns_200(self) -> None:
        """A JSON payload that doesn't validate as Update still returns 200."""
        client, _, _ = await _make_client()
        try:
            resp = await _post(client, body={"invalid": "data"})
            assert resp.status == 200
        finally:
            await client.close()

    async def test_empty_json_object_returns_200(self) -> None:
        """An empty JSON object {} is invalid as Update but must still return 200."""
        client, _, _ = await _make_client()
        try:
            resp = await _post(client, body=b"{}")
            assert resp.status == 200
        finally:
            await client.close()

    async def test_bot_request_update_dispatches_correctly(self) -> None:
        dp = Dispatcher()
        received_ids: list[int] = []

        @dp.bot_request()
        async def on_req(update: Any) -> None:
            received_ids.append(update.update_id)

        payload = {
            **_MINIMAL_UPDATE,
            "update_id": 99,
            "text": None,
            "bot_request": {"server_action": {"name": "click", "payload": {}}},
        }
        client, _, _ = await _make_client(dispatcher=dp)
        try:
            resp = await _post(client, body=payload)
            assert resp.status == 200
            assert received_ids == [99]
        finally:
            await client.close()

    async def test_update_fields_are_parsed_correctly(self) -> None:
        """Verify the update model is correctly built from the JSON payload."""
        dp = Dispatcher()
        received_updates: list[Any] = []

        @dp.message()
        async def on_msg(update: Any) -> None:
            received_updates.append(update)

        client, _, _ = await _make_client(dispatcher=dp)
        try:
            await _post(client)
            assert len(received_updates) == 1
            upd = received_updates[0]
            assert upd.update_id == 1
            assert upd.text == "hello"
            assert upd.chat.id == "chat-1"
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# setup() route registration
# ---------------------------------------------------------------------------


class TestWebhookSetup:
    def test_setup_registers_post_route(self) -> None:
        app, _, _ = _make_app(secret_token="s")
        routes = list(app.router.routes())
        assert any(r.method == "POST" for r in routes)

    def test_setup_registers_at_default_path(self) -> None:
        app, _, _ = _make_app(secret_token="s", path="/webhook")
        routes = list(app.router.routes())
        assert len(routes) == 1

    def test_setup_registers_at_custom_path(self) -> None:
        app, _, _ = _make_app(secret_token="s", path="/custom/hook")
        routes = list(app.router.routes())
        assert len(routes) == 1
