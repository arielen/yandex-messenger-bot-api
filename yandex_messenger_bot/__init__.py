"""Modern and fully asynchronous framework for Yandex Messenger Bot API."""

from yandex_messenger_bot._meta import __version__
from yandex_messenger_bot.client.bot import Bot
from yandex_messenger_bot.di.inject import Inject
from yandex_messenger_bot.dispatcher.dispatcher import Dispatcher
from yandex_messenger_bot.dispatcher.middlewares.base import BaseMiddleware
from yandex_messenger_bot.dispatcher.router import Router
from yandex_messenger_bot.filters.callback import ServerActionFilter
from yandex_messenger_bot.filters.command import CommandFilter
from yandex_messenger_bot.filters.magic import F
from yandex_messenger_bot.filters.state import StateFilter
from yandex_messenger_bot.fsm.context import FSMContext
from yandex_messenger_bot.fsm.state import State, StatesGroup
from yandex_messenger_bot.fsm.strategy import FSMStrategy
from yandex_messenger_bot.types.update import Update

__all__ = [
    "__version__",
    "BaseMiddleware",
    "Bot",
    "CommandFilter",
    "Dispatcher",
    "F",
    "FSMContext",
    "FSMStrategy",
    "Inject",
    "Router",
    "ServerActionFilter",
    "State",
    "StateFilter",
    "StatesGroup",
    "Update",
]
