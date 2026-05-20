from __future__ import annotations

from typing import TYPE_CHECKING, Any

from yandex_messenger_bot.filters.base import BaseFilter
from yandex_messenger_bot.fsm.state import State
from yandex_messenger_bot.types.update import Update

if TYPE_CHECKING:
    from yandex_messenger_bot.fsm.context import FSMContext


class StateFilter(BaseFilter):
    """Filter that checks whether the current FSM state matches any given state.

    Usage::

        from yandex_messenger_bot.filters.state import StateFilter


        class Form(StatesGroup):
            name = State()


        @router.message(StateFilter(Form.name))
        async def handle_name(update: Update, state: FSMContext) -> None: ...
    """

    def __init__(self, *states: State | str | None) -> None:
        self._states: tuple[State | str | None, ...] = states

    async def __call__(self, update: Update, **data: Any) -> bool | dict[str, Any]:
        state_ctx: FSMContext | None = data.get("state")  # type: ignore[assignment]
        if state_ctx is None:
            return False

        current = await state_ctx.get_state()

        for s in self._states:
            if s is None and current is None:
                return True
            if isinstance(s, State) and current == s.state_name:
                return True
            if isinstance(s, str) and current == s:
                return True

        return False
