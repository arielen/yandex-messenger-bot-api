from __future__ import annotations

# FSM context injection is handled directly by Dispatcher.feed_update(),
# which builds a StorageKey based on the configured FSMStrategy and injects
# the resulting FSMContext into the handler data dict.
#
# A dedicated FSMContextMiddleware is not needed at this time because
# the Dispatcher already owns the storage and strategy configuration.
