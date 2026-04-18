from __future__ import annotations

from abc import ABC
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, model_validator


class RecipientMixin(BaseModel):
    """Mixin that enforces exactly one of ``chat_id`` or ``login`` is set."""

    chat_id: str | None = None
    login: str | None = None

    @model_validator(mode="after")
    def _check_recipient(self) -> Self:
        if self.chat_id is None and self.login is None:
            raise ValueError("Either 'chat_id' or 'login' must be provided")
        if self.chat_id is not None and self.login is not None:
            raise ValueError("Provide either 'chat_id' or 'login', not both")
        return self


class YaBotMethod[TResult](BaseModel, ABC):
    """Base class for all API methods."""

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    __api_path__: ClassVar[str]
    __http_method__: ClassVar[str] = "POST"
    __returning__: ClassVar[type]
    __multipart__: ClassVar[bool] = False  # True for file upload methods
