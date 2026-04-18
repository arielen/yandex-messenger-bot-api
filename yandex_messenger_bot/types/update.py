from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field, field_validator

from yandex_messenger_bot.enums import ChatType
from yandex_messenger_bot.types.base import YaBotObject

if TYPE_CHECKING:
    from yandex_messenger_bot.client.bot import Bot
    from yandex_messenger_bot.methods.send_text import SendTextResult

from yandex_messenger_bot.types.bot_request import BotRequest
from yandex_messenger_bot.types.chat import Chat
from yandex_messenger_bot.types.file import Document, Image, Sticker
from yandex_messenger_bot.types.forward import ForwardedMessage
from yandex_messenger_bot.types.user import User


class Update(YaBotObject):
    """A single update from Yandex Messenger Bot API.

    This is a flat object — all fields come at the same level.
    An update may contain text, document, images, sticker,
    bot_request, forwarded_messages, etc. simultaneously.
    """

    update_id: int
    message_id: int
    timestamp: int
    chat: Chat
    from_user: User | None = Field(None, alias="from")
    text: str | None = None
    thread_id: int | None = None

    # Attachments (not mutually exclusive)
    forwarded_messages: list[ForwardedMessage] | None = None
    sticker: Sticker | None = None
    image: Image | None = None
    images: list[list[Image]] | None = None
    document: Document | None = None
    file: Document | None = None

    # Bot request (from button directives)
    bot_request: BotRequest | None = None

    # ------------------------------------------------------------------
    # Defensive validators: the Yandex docs are inconsistent about the
    # wire format of some fields.  These validators normalise both known
    # shapes so that parsing never fails regardless of what the API sends.
    # See docs/api-inconsistencies.md for details.
    # ------------------------------------------------------------------

    @field_validator("images", mode="before")
    @classmethod
    def _normalize_images(cls, v: Any) -> Any:
        """Accept both Image[] (flat) and Image[][] (nested) from the API.

        The data-types page documents ``Image[]``, but the polling response
        examples show ``Image[][]`` (outer = images, inner = size variants).
        """
        if v and isinstance(v, list) and v and isinstance(v[0], dict):
            return [v]  # flat → wrap in outer list
        return v

    @field_validator("forwarded_messages", mode="before")
    @classmethod
    def _normalize_forwarded(cls, v: Any) -> Any:
        """Accept both a single object and an array."""
        if isinstance(v, dict):
            return [v]
        return v

    async def reply(
        self,
        text: str,
        *,
        bot: Bot | None = None,
        in_private: bool = False,
        **kwargs: Any,
    ) -> SendTextResult:
        """Send a text message quoting this update (``reply_message_id``).

        Uses the current bot from :func:`~yandex_messenger_bot.context.get_current_bot`
        (set in :meth:`~yandex_messenger_bot.dispatcher.dispatcher.Dispatcher.feed_update`).
        Pass ``bot`` to override or when calling outside the dispatcher.

        If ``in_private`` is true, the message is sent to the user's personal chat
        (``login``), not to the group/channel chat. Automatic ``reply_message_id``
        and group ``thread_id`` are not applied (pass them explicitly in ``kwargs``
        if the API accepts them for your case).
        """
        from yandex_messenger_bot.context import get_current_bot  # noqa: PLC0415

        resolved = bot if bot is not None else get_current_bot()
        payload = dict(kwargs)
        if not in_private:
            if "reply_message_id" not in payload:
                payload["reply_message_id"] = self.message_id
            if "thread_id" not in kwargs and self.chat.type == ChatType.GROUP:
                tid = self.chat.thread_id if self.chat.thread_id is not None else self.thread_id
                if tid is not None:
                    payload["thread_id"] = tid

        if in_private:
            if self.from_user is not None and self.from_user.login is not None:
                return await resolved.send_text(login=self.from_user.login, text=text, **payload)
            if self.chat.type == ChatType.PRIVATE and self.chat.id is not None:
                return await resolved.send_text(chat_id=self.chat.id, text=text, **payload)
            raise ValueError(
                "Cannot reply in private: need from_user.login or a private chat with chat.id"
            )

        if self.chat.id is not None:
            return await resolved.send_text(chat_id=self.chat.id, text=text, **payload)
        if self.from_user is not None and self.from_user.login is not None:
            return await resolved.send_text(login=self.from_user.login, text=text, **payload)
        raise ValueError("Cannot reply: update has no chat.id and no from_user.login")
