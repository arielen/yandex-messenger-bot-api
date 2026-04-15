from __future__ import annotations

# FSMContextMiddleware — to be implemented when the dispatcher middleware
# interface is finalised. This module is a placeholder that will wire
# FSMContext into every handler call by:
#   1. Resolving the StorageKey from the incoming update (chat_id, user_id).
#   2. Creating an FSMContext backed by the configured BaseStorage.
#   3. Injecting the FSMContext into handler kwargs so handlers can receive it
#      via dependency injection (e.g. `ctx: FSMContext`).
#   4. Optionally enforcing the chosen FSMStrategy (USER_IN_CHAT, CHAT,
#      GLOBAL_USER) when building the StorageKey.
