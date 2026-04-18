from __future__ import annotations

from typing import Any

from yandex_messenger_bot.fsm.state import State
from yandex_messenger_bot.fsm.storage.base import BaseStorage, StorageKey


class FSMContext:
    """Per-user FSM context for managing conversation state."""

    def __init__(self, storage: BaseStorage, key: StorageKey) -> None:
        self._storage = storage
        self._key = key

    async def set_state(self, state: State | str | None = None) -> None:
        if isinstance(state, State):
            state = state.state_name
        await self._storage.set_state(self._key, state)

    async def get_state(self) -> str | None:
        return await self._storage.get_state(self._key)

    async def set_data(self, data: dict[str, Any]) -> None:
        await self._storage.set_data(self._key, data)

    async def get_data(self) -> dict[str, Any]:
        return await self._storage.get_data(self._key)

    async def update_data(self, **kwargs: Any) -> dict[str, Any]:
        data = await self.get_data()
        data.update(kwargs)
        await self.set_data(data)
        return data

    async def clear(self) -> None:
        await self.set_state(None)
        await self.set_data({})
