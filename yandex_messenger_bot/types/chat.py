from yandex_messenger_bot.enums import ChatType
from yandex_messenger_bot.types.base import YaBotObject


class Chat(YaBotObject):
    """Represents a chat (private, group, or channel)."""

    id: str
    type: ChatType | None = None
    organization_id: str | None = None
    title: str | None = None
    description: str | None = None
    is_channel: bool = False
