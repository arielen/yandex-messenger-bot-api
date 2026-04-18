from __future__ import annotations

from pydantic import Field

from yandex_messenger_bot.types.base import YaBotObject
from yandex_messenger_bot.types.user import User


class PollResults(YaBotObject):
    """Aggregated poll results."""

    voted_count: int = 0
    answers: dict[str, int] = Field(default_factory=dict)


class PollVoter(YaBotObject):
    """A user who voted in a poll."""

    user: User
    timestamp: int


class PollVoters(YaBotObject):
    """Paginated list of poll voters."""

    answer_id: int
    voted_count: int
    votes: list[PollVoter] = Field(default_factory=list)
    cursor: int = 0
