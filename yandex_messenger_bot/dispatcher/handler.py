from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from yandex_messenger_bot.di.provider import resolve_handler_params
from yandex_messenger_bot.loggers import dispatcher as logger
from yandex_messenger_bot.types.update import Update


def _is_async_callable(obj: Any) -> bool:
    """Return *True* if *obj* is an async callable (function or object)."""
    if inspect.iscoroutinefunction(obj):
        return True
    # For class instances (e.g. BaseFilter subclasses) check the __call__ method
    # on the *type*, not the instance, to correctly detect async.
    return inspect.iscoroutinefunction(type(obj).__call__)


def _filter_signature(f: Any) -> tuple[bool, bool]:
    """Inspect a filter callable and return ``(accepts_kwargs, n_params > 1)``."""
    # For class instances use __call__; for plain functions use f directly.
    target = f if inspect.isfunction(f) or inspect.isbuiltin(f) else type(f).__call__

    try:
        sig = inspect.signature(target)
    except (ValueError, TypeError):
        return False, False

    params = list(sig.parameters.values())
    accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
    positional = [
        p
        for p in params
        if p.kind
        in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.KEYWORD_ONLY,
        )
    ]
    return accepts_kwargs, len(positional) > 1


class HandlerObject:
    """Wraps a handler callback together with its filters.

    On each incoming update:

    1. All filters are evaluated (:meth:`check_filters`).
    2. If all pass, the handler is called with the merged data dict
       (:meth:`call`).
    """

    def __init__(
        self,
        callback: Callable[..., Awaitable[Any]],
        filters: tuple[Any, ...] = (),
    ) -> None:
        self.callback = callback
        self.filters = filters
        self._params = self._inspect_params()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _inspect_params(self) -> dict[str, inspect.Parameter]:
        sig = inspect.signature(self.callback)
        return {
            name: param
            for name, param in sig.parameters.items()
            if param.kind
            in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        }

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def check_filters(self, update: Update, data: dict[str, Any]) -> dict[str, Any] | None:
        """Run every filter.

        Returns a dict of extra context data to merge if **all** filters pass,
        or *None* if any filter rejects the update.
        """
        extra: dict[str, Any] = {}

        for f in self.filters:
            if not callable(f):
                continue

            is_async = _is_async_callable(f)
            accepts_kwargs, multi_param = _filter_signature(f)

            # When passing the data dict as **kwargs we must exclude 'update'
            # since it is already provided as the first positional argument.
            data_kwargs = {k: v for k, v in data.items() if k != "update"}

            result = await _invoke_filter(
                f,
                update,
                data_kwargs,
                is_async=is_async,
                use_kwargs=accepts_kwargs or multi_param,
            )

            if result is False or result is None:
                return None
            if isinstance(result, dict):
                extra.update(result)

        return extra

    def prepare_kwargs(self, data: dict[str, Any]) -> dict[str, Any]:
        """Select only the kwargs that the handler signature declares."""
        return {k: data[k] for k in self._params if k in data}

    async def call(self, update: Update, data: dict[str, Any]) -> Any:
        """Invoke the handler with the resolved kwargs."""
        dependencies = data.get("__dependencies__", {})
        kwargs, cleanups = await resolve_handler_params(self.callback, data, dependencies)
        try:
            return await self.callback(**kwargs)
        finally:
            for cleanup in reversed(cleanups):
                try:
                    await cleanup
                except Exception:
                    logger.warning("Error during DI cleanup", exc_info=True)


async def _invoke_filter(
    f: Any,
    update: Update,
    data_kwargs: dict[str, Any],
    *,
    is_async: bool,
    use_kwargs: bool,
) -> Any:
    """Call a filter and return its result, falling back to plain invocation."""
    # magic-filter MagicFilter chains (e.g. F.text == "x") have a .resolve()
    # method that evaluates the expression against an object and returns bool.
    if hasattr(f, "resolve"):
        return f.resolve(update)

    try:
        if use_kwargs:
            return await f(update, **data_kwargs) if is_async else f(update, **data_kwargs)
        return await f(update) if is_async else f(update)
    except TypeError:
        return await f(update) if is_async else f(update)
