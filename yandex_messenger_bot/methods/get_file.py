from __future__ import annotations

from typing import ClassVar

from yandex_messenger_bot.methods.base import YaBotMethod


class GetFile(YaBotMethod[bytes]):
    """Download a file by its file_id. Returns raw bytes (streaming response)."""

    __api_path__: ClassVar[str] = "/bot/v1/messages/getFile/"
    __http_method__: ClassVar[str] = "GET"
    __returning__: ClassVar[type] = bytes

    file_id: str
