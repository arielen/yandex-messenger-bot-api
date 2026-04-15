from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path


class InputFile(ABC):
    """Base class for file uploads."""

    def __init__(self, filename: str | None = None) -> None:
        self.filename = filename

    @abstractmethod
    async def read(self) -> AsyncIterator[bytes]:
        """Yield file content as chunks."""
        yield b""  # pragma: no cover


class BufferedInputFile(InputFile):
    """File from in-memory bytes."""

    def __init__(self, data: bytes, filename: str) -> None:
        super().__init__(filename=filename)
        self._data = data

    async def read(self) -> AsyncIterator[bytes]:
        yield self._data


class FSInputFile(InputFile):
    """File from filesystem path."""

    def __init__(
        self,
        path: str | Path,
        filename: str | None = None,
        chunk_size: int = 65536,
    ) -> None:
        self._path = Path(path)
        self._chunk_size = chunk_size
        super().__init__(filename=filename or self._path.name)

    async def read(self) -> AsyncIterator[bytes]:
        with self._path.open("rb") as f:
            while chunk := f.read(self._chunk_size):
                yield chunk


class URLInputFile(InputFile):
    """File streamed from a URL. Requires an aiohttp session to download."""

    def __init__(self, url: str, filename: str | None = None) -> None:
        self._url = url
        super().__init__(filename=filename)

    @property
    def url(self) -> str:
        return self._url

    async def read(self) -> AsyncIterator[bytes]:
        msg = "URLInputFile.read() requires a session; use Bot.download() instead"
        raise NotImplementedError(msg)
        yield b""  # pragma: no cover  # noqa: RET503
