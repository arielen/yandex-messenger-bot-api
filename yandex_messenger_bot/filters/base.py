from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from yandex_messenger_bot.types.update import Update


class BaseFilter(ABC):
    """Abstract base class for all update filters."""

    @abstractmethod
    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        """Return *True*/*False* or a dict of extra context data to inject."""

    # ------------------------------------------------------------------ #
    # Logical combinators                                                  #
    # ------------------------------------------------------------------ #

    def __and__(self, other: BaseFilter) -> _AndFilter:
        return _AndFilter(self, other)

    def __or__(self, other: BaseFilter) -> _OrFilter:
        return _OrFilter(self, other)

    def __invert__(self) -> _InvertFilter:
        return _InvertFilter(self)


class _AndFilter(BaseFilter):
    """Filter that passes only when *both* sub-filters pass."""

    def __init__(self, left: BaseFilter, right: BaseFilter) -> None:
        self._left = left
        self._right = right

    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        left_result = await self._left(update, **data)
        if left_result is False or left_result is None:
            return False

        right_result = await self._right(update, **data)
        if right_result is False or right_result is None:
            return False

        # Merge extra dicts if both returned dicts
        merged: dict[str, Any] = {}
        if isinstance(left_result, dict):
            merged.update(left_result)
        if isinstance(right_result, dict):
            merged.update(right_result)
        return merged if merged else True


class _OrFilter(BaseFilter):
    """Filter that passes when *at least one* sub-filter passes."""

    def __init__(self, left: BaseFilter, right: BaseFilter) -> None:
        self._left = left
        self._right = right

    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        left_result = await self._left(update, **data)
        if left_result is not False and left_result is not None:
            return left_result

        right_result = await self._right(update, **data)
        if right_result is not False and right_result is not None:
            return right_result

        return False


class _InvertFilter(BaseFilter):
    """Filter that inverts the result of its sub-filter."""

    def __init__(self, inner: BaseFilter) -> None:
        self._inner = inner

    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        result = await self._inner(update, **data)
        # A dict is truthy — invert it to False
        if isinstance(result, dict):
            return not result
        return not result
