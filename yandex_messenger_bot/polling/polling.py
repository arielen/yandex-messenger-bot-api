from __future__ import annotations

import asyncio
import contextlib
import random
import signal
from typing import TYPE_CHECKING

from yandex_messenger_bot.exceptions import TooManyRequestsError
from yandex_messenger_bot.loggers import polling as logger
from yandex_messenger_bot.methods.get_updates import GetUpdates

if TYPE_CHECKING:
    from yandex_messenger_bot.client.bot import Bot
    from yandex_messenger_bot.dispatcher.dispatcher import Dispatcher


class Backoff:
    """Exponential backoff with jitter for retrying failed operations."""

    def __init__(
        self,
        min_delay: float = 0.5,
        max_delay: float = 30.0,
        factor: float = 2.0,
        jitter: float = 0.5,
    ) -> None:
        self._min = min_delay
        self._max = max_delay
        self._factor = factor
        self._jitter = jitter
        self._current = min_delay

    def next(self) -> float:
        """Return the next delay and advance the internal counter."""
        delay = self._current + random.uniform(0, self._jitter)
        self._current = min(self._current * self._factor, self._max)
        return delay

    def reset(self) -> None:
        """Reset delay back to the minimum after a successful request."""
        self._current = self._min


async def run_polling(
    dispatcher: Dispatcher,
    bot: Bot,
    *,
    limit: int = 100,
    poll_interval: float = 1.0,
) -> None:
    """Run long-polling loop until SIGINT or SIGTERM is received.

    Args:
        dispatcher: The dispatcher that processes incoming updates.
        bot: The Bot instance used to call the API.
        limit: Maximum number of updates to fetch per request.
        poll_interval: Seconds to wait between polls when no updates arrive.
    """
    offset = 0
    backoff = Backoff()
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError, RuntimeError):
            loop.add_signal_handler(sig, stop.set)

    logger.info("Started polling")

    while not stop.is_set():
        try:
            result = await bot(GetUpdates(offset=offset, limit=limit))
            backoff.reset()

            for update in result.updates:
                offset = update.update_id + 1
                try:
                    await dispatcher.feed_update(bot, update)
                except Exception:
                    logger.exception("Error processing update %d", update.update_id)

            if not result.updates:
                await asyncio.sleep(poll_interval)

        except TooManyRequestsError as e:
            logger.warning("Rate limited, sleeping %s seconds", e.retry_after)
            await asyncio.sleep(e.retry_after)
        except asyncio.CancelledError:
            logger.info("Polling task cancelled")
            break
        except Exception:
            delay = backoff.next()
            logger.exception("Polling error, retrying in %.1fs", delay)
            await asyncio.sleep(delay)

    logger.info("Polling stopped")
