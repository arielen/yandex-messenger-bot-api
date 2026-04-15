from __future__ import annotations

from typing import TYPE_CHECKING

from aiohttp import web

from yandex_messenger_bot.loggers import webhook as logger
from yandex_messenger_bot.types.update import Update

if TYPE_CHECKING:
    from yandex_messenger_bot.client.bot import Bot
    from yandex_messenger_bot.dispatcher.dispatcher import Dispatcher


class WebhookHandler:
    """aiohttp request handler that feeds incoming webhook payloads to the dispatcher."""

    def __init__(
        self,
        dispatcher: Dispatcher,
        bot: Bot,
        *,
        secret_token: str | None = None,
        max_body_size: int = 1_048_576,
    ) -> None:
        self._dispatcher = dispatcher
        self._bot = bot
        self._secret_token = secret_token
        self._max_body_size = max_body_size

    async def handle(self, request: web.Request) -> web.Response:
        """Parse the incoming JSON body as an Update and dispatch it."""
        # --- Authentication ---
        if self._secret_token is not None:
            token = request.headers.get("X-Secret-Token")
            if token != self._secret_token:
                return web.Response(status=401)

        # --- Content-Length guard ---
        content_length = request.content_length
        if content_length is not None and content_length > self._max_body_size:
            return web.Response(status=413)

        # --- Content-Type check ---
        content_type = request.content_type
        if not content_type.startswith("application/json"):
            return web.Response(status=415)

        try:
            data = await request.json()
            update = Update.model_validate(data)
            await self._dispatcher.feed_update(self._bot, update)
        except Exception:
            logger.exception("Error processing webhook update")
            return web.Response(status=200)

        return web.Response(status=200)

    def setup(self, app: web.Application, path: str = "/webhook") -> None:
        """Register the POST route on *app* at *path*."""
        app.router.add_post(path, self.handle)
