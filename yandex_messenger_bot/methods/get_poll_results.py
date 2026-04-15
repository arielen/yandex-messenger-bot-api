from __future__ import annotations

from typing import ClassVar

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.poll import PollResults


class GetPollResults(YaBotMethod[PollResults]):
    """Get aggregated results for a poll message."""

    __api_path__: ClassVar[str] = "/bot/v1/polls/getResults/"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = PollResults

    chat_id: str
    message_id: int
