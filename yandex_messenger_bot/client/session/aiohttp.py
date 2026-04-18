from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlparse

import aiohttp

from yandex_messenger_bot.exceptions import (
    ClientDecodeError,
    NetworkError,
    ServerError,
    TooManyRequestsError,
    raise_for_status,
)
from yandex_messenger_bot.loggers import event as logger
from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.input_file import InputFile

from .base import BaseSession

_MAX_RETRIES = 3
_DEFAULT_TIMEOUT = 60.0
_CHUNK_SIZE = 65536
_HTTP_CLIENT_ERROR = 400
_HTTP_RATE_LIMITED = 429


class AiohttpSession(BaseSession):
    """aiohttp-based HTTP session for Yandex Messenger Bot API."""

    BASE_URL = "https://botapi.messenger.yandex.net"

    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return the aiohttp session, creating it lazily on first call."""
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=100,
                        ttl_dns_cache=3600,
                    )
                    self._session = aiohttp.ClientSession(connector=connector, trust_env=False)
        return self._session

    def _build_url(self, path: str) -> str:
        return f"{self.BASE_URL}{path}"

    async def _build_form_data(self, method: YaBotMethod[Any]) -> aiohttp.FormData:
        """Build multipart FormData from a method, streaming InputFile fields."""
        form = aiohttp.FormData(quote_fields=False)
        # Add non-file fields from model_dump
        params = method.model_dump(exclude_none=True, by_alias=True)
        for key, value in params.items():
            if isinstance(value, str):
                form.add_field(key, value)
            elif isinstance(value, bool):
                form.add_field(key, str(value).lower())
            elif isinstance(value, (int, float)):
                form.add_field(key, str(value))
            else:
                form.add_field(key, json.dumps(value, ensure_ascii=False))

        # Add InputFile fields directly from the method attributes
        for field_name, field_info in method.model_fields.items():
            value = getattr(method, field_name, None)
            if value is None:
                continue
            alias = field_info.alias or field_name
            if isinstance(value, InputFile):
                file_bytes = b"".join([chunk async for chunk in value.read()])
                form.add_field(
                    alias,
                    file_bytes,
                    filename=value.filename or field_name,
                )
            elif isinstance(value, list) and value and isinstance(value[0], InputFile):
                for i, item in enumerate(value):
                    if not isinstance(item, InputFile):
                        continue
                    file_bytes = b"".join([chunk async for chunk in item.read()])
                    form.add_field(
                        alias,
                        file_bytes,
                        filename=item.filename or f"{field_name}_{i}",
                    )
        return form

    @staticmethod
    async def _extract_error_info(
        resp: aiohttp.ClientResponse,
    ) -> tuple[str, float | None]:
        """Return (description, retry_after) from an error response."""
        description = ""
        retry_after: float | None = None
        try:
            error_data = await resp.json(content_type=None)
            if isinstance(error_data, dict):
                description = error_data.get("description", "") or error_data.get("message", "")
        except Exception:
            description = await resp.text()
        if resp.status == _HTTP_RATE_LIMITED:
            header = resp.headers.get("Retry-After")
            if header is not None:
                try:
                    retry_after = min(float(header), 300.0)
                except ValueError:
                    retry_after = 1.0
        return description, retry_after

    async def _do_request(
        self,
        session: aiohttp.ClientSession,
        token: str,
        method: YaBotMethod[Any],
    ) -> Any:
        """Execute one HTTP request (no retry logic here)."""
        url = self._build_url(method.__api_path__)
        headers = {"Authorization": f"OAuth {token}"}
        client_timeout = aiohttp.ClientTimeout(total=self._timeout)

        if method.__multipart__:
            form = await self._build_form_data(method)
            response_cm = session.post(
                url,
                data=form,
                headers=headers,
                timeout=client_timeout,
                allow_redirects=False,
            )
        elif method.__http_method__ == "GET":
            params = method.model_dump(exclude_none=True, by_alias=True)
            response_cm = session.get(
                url,
                params=params,
                headers=headers,
                timeout=client_timeout,
                allow_redirects=False,
            )
        else:
            body = method.model_dump(exclude_none=True, by_alias=True)
            response_cm = session.post(
                url,
                json=body,
                headers=headers,
                timeout=client_timeout,
                allow_redirects=False,
            )

        async with response_cm as resp:
            status = resp.status

            # For streaming/bytes methods (e.g. GetFile), return raw bytes
            if method.__returning__ is bytes:
                if status >= _HTTP_CLIENT_ERROR:
                    desc, retry_after = await self._extract_error_info(resp)
                    raise_for_status(status, desc, method=method, retry_after=retry_after)
                return await resp.read()

            # Check HTTP errors first, before JSON decode
            if status >= _HTTP_CLIENT_ERROR:
                desc, retry_after = await self._extract_error_info(resp)
                raise_for_status(status, desc, method=method, retry_after=retry_after)

            # Parse successful response JSON
            try:
                data = await resp.json(content_type=None)
            except Exception as exc:
                raw = await resp.text()
                raise ClientDecodeError(
                    f"Failed to decode response (status={status}): {raw!r}"
                ) from exc

            if isinstance(data, dict):
                ok = data.get("ok", True)
                if not ok:
                    description = data.get("description", "Unknown error")
                    raise_for_status(status, description, method=method)
                result = data.get("result", data)
            else:
                result = data

            return result

    async def make_request(self, token: str, method: YaBotMethod[Any]) -> Any:
        """Execute an API method with retry logic for 429 and 5xx responses."""
        session = await self._get_session()
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                return await self._do_request(session, token, method)
            except TooManyRequestsError as exc:
                last_exc = exc
                wait_time = exc.retry_after
                logger.warning(
                    "Rate limited (429). Retry-After=%.1fs. Attempt %d/%d.",
                    wait_time,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait_time)
            except ServerError as exc:
                last_exc = exc
                wait_time = 2.0**attempt
                logger.warning(
                    "Server error (%d). Retrying in %.1fs. Attempt %d/%d.",
                    exc.status_code,
                    wait_time,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait_time)
            except (TimeoutError, aiohttp.ClientError) as exc:
                raise NetworkError(f"Request failed: {type(exc).__name__}: {exc}") from exc

        if last_exc is None:
            raise RuntimeError("Retry loop exited without an exception")
        raise last_exc

    async def stream_content(self, token: str, url: str) -> AsyncIterator[bytes]:  # ty: ignore[invalid-method-override]
        """Stream raw bytes from a URL using chunked transfer."""
        parsed = urlparse(url)
        base_parsed = urlparse(self.BASE_URL)
        if parsed.scheme not in ("https", "http") or parsed.netloc != base_parsed.netloc:
            raise ValueError(f"Refusing to stream from untrusted URL: {url}")
        session = await self._get_session()
        headers = {"Authorization": f"OAuth {token}"}
        client_timeout = aiohttp.ClientTimeout(total=self._timeout)
        try:
            async with session.get(
                url, headers=headers, timeout=client_timeout, allow_redirects=False
            ) as resp:
                if resp.status >= _HTTP_CLIENT_ERROR:
                    description, _ = await self._extract_error_info(resp)
                    raise_for_status(resp.status, description)
                async for chunk in resp.content.iter_chunked(_CHUNK_SIZE):
                    yield chunk
        except (TimeoutError, aiohttp.ClientError) as exc:
            raise NetworkError(f"Stream failed: {type(exc).__name__}: {exc}") from exc

    async def close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
            # Allow SSL connections to drain
            await asyncio.sleep(0.25)
        self._session = None
