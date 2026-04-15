from __future__ import annotations

from abc import ABC
from typing import ClassVar

from pydantic import BaseModel, ConfigDict


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
