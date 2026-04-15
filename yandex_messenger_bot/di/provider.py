from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator, Callable
from typing import Annotated, Any, get_args, get_origin, get_type_hints

from yandex_messenger_bot.di.inject import Inject
from yandex_messenger_bot.exceptions import DependencyResolutionError
from yandex_messenger_bot.loggers import dispatcher as logger

_BUILTIN_TYPES: frozenset[type] = frozenset({str, int, float, bool, bytes, dict, list, tuple, set})
_MISSING = object()


async def resolve_handler_params(
    callback: Callable[..., Any],
    data: dict[str, Any],
    dependencies: dict[type, Any],
) -> tuple[dict[str, Any], list[Any]]:
    """Resolve all handler parameters from the data dict and DI registrations.

    Returns ``(kwargs, cleanups)`` where *cleanups* is a list of coroutines
    to await after the handler finishes (for async-generator-based deps).
    """
    try:
        hints = get_type_hints(callback, include_extras=True)
    except Exception:
        cb_name = getattr(callback, "__name__", repr(callback))
        logger.debug("Failed to resolve type hints for %s", cb_name, exc_info=True)
        hints = {}

    sig = inspect.signature(callback)
    result: dict[str, Any] = {}
    cleanups: list[Any] = []

    for name, param in sig.parameters.items():
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        hint = hints.get(name)
        # When get_type_hints failed (e.g. local class under PEP 563), fall back
        # to the raw annotation from the signature which may be a string.
        if hint is None and param.annotation is not inspect.Parameter.empty:
            hint = param.annotation
        resolved, cleanup = await _resolve_param(name, hint, data, dependencies)
        if resolved is not _MISSING:
            result[name] = resolved
            if cleanup is not None:
                cleanups.append(cleanup)

    return result, cleanups


async def _resolve_param(
    name: str,
    hint: Any,
    data: dict[str, Any],
    dependencies: dict[type, Any],
) -> tuple[Any, Any]:
    """Resolve a single parameter. Returns ``(value, cleanup)`` or ``(_MISSING, None)``."""
    # ---- Annotated[T, Inject(...)] -------------------------------------------
    if hint is not None and get_origin(hint) is Annotated:
        inject_result = await _try_inject(hint, data, dependencies, name)
        if inject_result is not _MISSING:
            return inject_result  # already (value, cleanup)

    # ---- Name-based lookup ---------------------------------------------------
    if name in data:
        return data[name], None

    # ---- Type-based lookup ---------------------------------------------------
    if hint is not None:
        base_type = get_args(hint)[0] if get_origin(hint) is Annotated else hint
        if isinstance(base_type, type) and base_type not in _BUILTIN_TYPES:
            # First check existing values in the data dict
            for val in data.values():
                if isinstance(val, base_type):
                    return val, None
            # Then check registered dependency factories
            if base_type in dependencies:
                value, cleanup = await _call_factory(dependencies[base_type], data)
                return value, cleanup
        elif isinstance(base_type, str):
            # String annotation (PEP 563 / from __future__ import annotations with
            # unresolvable local type). Match against registered dependency type names.
            for dep_type, factory in dependencies.items():
                if base_type in {dep_type.__name__, dep_type.__qualname__}:
                    value, cleanup = await _call_factory(factory, data)
                    return value, cleanup

    return _MISSING, None


async def _try_inject(
    hint: Any,
    data: dict[str, Any],
    dependencies: dict[type, Any],
    param_name: str,
) -> Any:
    """Attempt Annotated[T, Inject(...)] resolution.

    Returns ``(value, cleanup)`` on success, or ``_MISSING`` if no
    :class:`Inject` marker is present.
    """
    type_args = get_args(hint)
    base_type = type_args[0]

    marker: Inject | None = next((a for a in type_args[1:] if isinstance(a, Inject)), None)
    if marker is None:
        return _MISSING

    factory = marker.factory or dependencies.get(base_type)
    if factory is None:
        raise DependencyResolutionError(
            f"No factory registered for type {base_type!r} (parameter {param_name!r})"
        )

    value, cleanup = await _call_factory(factory, data)
    return value, cleanup


async def _call_factory(
    factory: Callable[..., Any],
    data: dict[str, Any],
) -> tuple[Any, Any]:
    """Call a factory (coroutine, async generator, or sync callable).

    Returns ``(value, cleanup_coroutine_or_None)``.
    """
    if inspect.isasyncgenfunction(factory):
        gen: AsyncGenerator[Any, None] = factory()
        try:
            value = await gen.__anext__()
        except BaseException:
            await gen.aclose()
            raise
        return value, gen.aclose()

    if inspect.iscoroutinefunction(factory):
        return await factory(), None

    return factory(), None
