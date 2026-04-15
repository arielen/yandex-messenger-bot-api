from __future__ import annotations

from collections.abc import Callable
from typing import Any


class Inject:
    """Marker for dependency injection via ``Annotated[T, Inject(...)]``.

    Usage::

        # With inline factory
        async def handler(db: Annotated[Database, Inject(factory=get_database)]) -> None: ...


        # Resolved from dp.dependency() by type
        async def handler(db: Annotated[Database, Inject()]) -> None: ...
    """

    def __init__(self, *, factory: Callable[..., Any] | None = None) -> None:
        self.factory = factory

    def __repr__(self) -> str:
        if self.factory:
            return f"Inject(factory={self.factory!r})"
        return "Inject()"
