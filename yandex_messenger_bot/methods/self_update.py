from __future__ import annotations

from typing import ClassVar

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.bot_self import BotSelf


class SelfUpdate(YaBotMethod[BotSelf]):
    """Update bot settings (e.g., webhook URL). Pass None to clear the webhook."""

    __api_path__: ClassVar[str] = "/bot/v1/self/update/"
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type] = BotSelf

    webhook_url: str | None = None
