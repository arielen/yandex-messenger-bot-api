from __future__ import annotations

from typing import ClassVar

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.types.poll import PollVoters


class GetPollVoters(YaBotMethod[PollVoters]):
    """Get paginated list of voters for a specific poll answer."""

    __api_path__: ClassVar[str] = "/bot/v1/polls/getVoters/"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = PollVoters

    chat_id: str
    message_id: int
    answer_number: int
    cursor: int = 0
    limit: int = 100
