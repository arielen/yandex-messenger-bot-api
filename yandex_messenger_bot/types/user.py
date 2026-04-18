from yandex_messenger_bot.types.base import YaBotObject


class User(YaBotObject):
    """Represents a user or bot in Yandex Messenger."""

    id: str | None = None
    login: str | None = None
    display_name: str | None = None
    robot: bool = False
