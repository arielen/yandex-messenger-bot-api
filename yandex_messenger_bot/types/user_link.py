from yandex_messenger_bot.types.base import YaBotObject


class UserLink(YaBotObject):
    """Links for a user (chat and call)."""

    chat_link: str | None = None
    call_link: str | None = None
