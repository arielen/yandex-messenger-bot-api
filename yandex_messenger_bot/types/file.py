from yandex_messenger_bot.types.base import YaBotObject


class Document(YaBotObject):
    """Represents a file/document attachment."""

    id: str
    name: str | None = None
    mime_type: str | None = None
    size: int | None = None


class Image(YaBotObject):
    """Represents an image attachment (one size variant)."""

    file_id: str
    width: int | None = None
    height: int | None = None
    size: int | None = None
    name: str | None = None


class Sticker(YaBotObject):
    """Represents a sticker."""

    id: str
    emoji: str | None = None
    set_id: str | None = None
