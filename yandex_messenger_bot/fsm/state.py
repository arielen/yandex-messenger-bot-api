from __future__ import annotations

from typing import Any


class StatesGroupMeta(type):
    """Metaclass that auto-assigns state names."""

    __all_states__: tuple[State, ...]
    __all_state_names__: tuple[str, ...]

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> StatesGroupMeta:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if bases:  # skip the base StatesGroup itself
            states = []
            for attr_name, value in namespace.items():
                if isinstance(value, State):
                    value._name = f"{name}:{attr_name}"
                    value._group = cls
                    states.append(value)
            cls.__all_states__ = tuple(states)
            cls.__all_state_names__ = tuple(s.state_name for s in states)

        return cls


class State:
    """A single FSM state."""

    def __init__(self) -> None:
        self._name: str | None = None
        self._group: type | None = None

    @property
    def state_name(self) -> str:
        if self._name is None:
            msg = "State must be defined inside a StatesGroup"
            raise RuntimeError(msg)
        return self._name

    def __repr__(self) -> str:
        return f"State({self._name!r})"


class StatesGroup(metaclass=StatesGroupMeta):
    """Group of FSM states."""

    __all_states__: tuple[State, ...] = ()
    __all_state_names__: tuple[str, ...] = ()

    def __contains__(self, item: str) -> bool:
        return item in self.__all_state_names__
