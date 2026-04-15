from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Self, TypeVar

from yandex_messenger_bot.client.session.aiohttp import AiohttpSession
from yandex_messenger_bot.client.session.base import BaseSession
from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.methods.create_chat import CreateChat, CreateChatResult
from yandex_messenger_bot.methods.create_poll import CreatePoll, CreatePollResult
from yandex_messenger_bot.methods.delete_message import DeleteMessage, DeleteMessageResult
from yandex_messenger_bot.methods.get_poll_results import GetPollResults
from yandex_messenger_bot.methods.get_poll_voters import GetPollVoters
from yandex_messenger_bot.methods.get_updates import GetUpdates, GetUpdatesResult
from yandex_messenger_bot.methods.get_user_link import GetUserLink
from yandex_messenger_bot.methods.self_update import SelfUpdate
from yandex_messenger_bot.methods.send_file import SendFile, SendFileResult
from yandex_messenger_bot.methods.send_gallery import SendGallery, SendGalleryResult
from yandex_messenger_bot.methods.send_image import SendImage, SendImageResult
from yandex_messenger_bot.methods.send_text import SendText, SendTextResult
from yandex_messenger_bot.methods.update_members import UpdateMembers, UpdateMembersResult
from yandex_messenger_bot.types.bot_self import BotSelf
from yandex_messenger_bot.types.button import SuggestButtons
from yandex_messenger_bot.types.input_file import InputFile
from yandex_messenger_bot.types.poll import PollResults, PollVoters
from yandex_messenger_bot.types.user_link import UserLink

TResult = TypeVar("TResult")


class Bot:
    """High-level client for the Yandex Messenger Bot API."""

    def __init__(
        self,
        token: str,
        session: BaseSession | None = None,
    ) -> None:
        self._token = token
        self._session = session or AiohttpSession()

    @property
    def token(self) -> str:
        return self._token

    async def __call__(self, method: YaBotMethod[TResult]) -> TResult:
        """Execute an API method and return a typed result."""
        raw = await self._session.make_request(self._token, method)
        returning = method.__returning__
        if returning is bytes:
            return raw  # type: ignore[return-value]
        if isinstance(raw, dict) and hasattr(returning, "model_validate"):
            return returning.model_validate(raw)  # ty: ignore[call-non-callable]
        return raw  # type: ignore[return-value]

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying session and release resources."""
        await self._session.close()

    # ------------------------------------------------------------------ #
    # Shortcut methods for all 14 API endpoints                           #
    # ------------------------------------------------------------------ #

    async def send_text(
        self,
        *,
        chat_id: str | None = None,
        login: str | None = None,
        text: str,
        payload_id: str | None = None,
        reply_message_id: int | None = None,
        disable_notification: bool = False,
        important: bool = False,
        disable_web_page_preview: bool = False,
        thread_id: int | None = None,
        suggest_buttons: SuggestButtons | None = None,
    ) -> SendTextResult:
        """Send a text message to a chat or user."""
        return await self(
            SendText(
                chat_id=chat_id,
                login=login,
                text=text,
                payload_id=payload_id,
                reply_message_id=reply_message_id,
                disable_notification=disable_notification,
                important=important,
                disable_web_page_preview=disable_web_page_preview,
                thread_id=thread_id,
                suggest_buttons=suggest_buttons,
            )
        )

    async def send_file(
        self,
        *,
        chat_id: str | None = None,
        login: str | None = None,
        document: InputFile,
        thread_id: int | None = None,
        suggest_buttons: SuggestButtons | None = None,
    ) -> SendFileResult:
        """Send a file (document) to a chat or user via multipart upload."""
        return await self(
            SendFile(
                chat_id=chat_id,
                login=login,
                document=document,
                thread_id=thread_id,
                suggest_buttons=suggest_buttons,
            )
        )

    async def send_image(
        self,
        *,
        chat_id: str | None = None,
        login: str | None = None,
        image: InputFile,
        thread_id: int | None = None,
        suggest_buttons: SuggestButtons | None = None,
    ) -> SendImageResult:
        """Send an image to a chat or user via multipart upload."""
        return await self(
            SendImage(
                chat_id=chat_id,
                login=login,
                image=image,
                thread_id=thread_id,
                suggest_buttons=suggest_buttons,
            )
        )

    async def send_gallery(
        self,
        *,
        chat_id: str | None = None,
        login: str | None = None,
        images: list[InputFile],
        text: str | None = None,
        thread_id: int | None = None,
        suggest_buttons: SuggestButtons | None = None,
    ) -> SendGalleryResult:
        """Send a gallery of images (up to 10) via multipart upload."""
        return await self(
            SendGallery(
                chat_id=chat_id,
                login=login,
                images=images,
                text=text,
                thread_id=thread_id,
                suggest_buttons=suggest_buttons,
            )
        )

    async def delete_message(
        self,
        *,
        chat_id: str,
        message_id: int,
    ) -> DeleteMessageResult:
        """Delete a message from a chat."""
        return await self(
            DeleteMessage(
                chat_id=chat_id,
                message_id=message_id,
            )
        )

    async def get_updates(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> GetUpdatesResult:
        """Fetch pending updates via long polling."""
        return await self(
            GetUpdates(
                offset=offset,
                limit=limit,
            )
        )

    async def create_chat(
        self,
        *,
        name: str,
        description: str | None = None,
        members: list[str] | None = None,
        admins: list[str] | None = None,
        subscribers: list[str] | None = None,
        is_channel: bool = False,
    ) -> CreateChatResult:
        """Create a new group chat or channel."""
        return await self(
            CreateChat(
                name=name,
                description=description,
                members=members,
                admins=admins,
                subscribers=subscribers,
                is_channel=is_channel,
            )
        )

    async def update_members(
        self,
        *,
        chat_id: str,
        members_add: list[str] | None = None,
        members_remove: list[str] | None = None,
        admins_add: list[str] | None = None,
        admins_remove: list[str] | None = None,
        subscribers_add: list[str] | None = None,
        subscribers_remove: list[str] | None = None,
    ) -> UpdateMembersResult:
        """Add or remove members/admins/subscribers from a chat or channel."""
        return await self(
            UpdateMembers(
                chat_id=chat_id,
                members_add=members_add,
                members_remove=members_remove,
                admins_add=admins_add,
                admins_remove=admins_remove,
                subscribers_add=subscribers_add,
                subscribers_remove=subscribers_remove,
            )
        )

    async def get_user_link(
        self,
        *,
        login: str,
    ) -> UserLink:
        """Get chat and call links for a user by login."""
        return await self(GetUserLink(login=login))

    async def create_poll(
        self,
        *,
        chat_id: str | None = None,
        login: str | None = None,
        title: str,
        answers: list[str],
        max_choices: int = 1,
        is_anonymous: bool = False,
        payload_id: str | None = None,
        reply_message_id: int | None = None,
        disable_notification: bool = False,
        important: bool = False,
        thread_id: int | None = None,
        suggest_buttons: SuggestButtons | None = None,
    ) -> CreatePollResult:
        """Create and send a poll to a chat or user."""
        return await self(
            CreatePoll(
                chat_id=chat_id,
                login=login,
                title=title,
                answers=answers,
                max_choices=max_choices,
                is_anonymous=is_anonymous,
                payload_id=payload_id,
                reply_message_id=reply_message_id,
                disable_notification=disable_notification,
                important=important,
                thread_id=thread_id,
                suggest_buttons=suggest_buttons,
            )
        )

    async def get_poll_results(
        self,
        *,
        chat_id: str,
        message_id: int,
    ) -> PollResults:
        """Get aggregated results for a poll message."""
        return await self(
            GetPollResults(
                chat_id=chat_id,
                message_id=message_id,
            )
        )

    async def get_poll_voters(
        self,
        *,
        chat_id: str,
        message_id: int,
        answer_number: int,
        cursor: int = 0,
        limit: int = 100,
    ) -> PollVoters:
        """Get paginated list of voters for a specific poll answer."""
        return await self(
            GetPollVoters(
                chat_id=chat_id,
                message_id=message_id,
                answer_number=answer_number,
                cursor=cursor,
                limit=limit,
            )
        )

    async def self_update(
        self,
        *,
        webhook_url: str | None = None,
    ) -> BotSelf:
        """Update bot settings (e.g., webhook URL). Pass None to clear the webhook."""
        return await self(SelfUpdate(webhook_url=webhook_url))

    async def download(
        self,
        file_id: str,
        destination: Path | BinaryIO | None = None,
    ) -> BytesIO | None:
        """Download a file by file_id.

        If destination is None, returns a BytesIO buffer with the file content.
        If destination is a Path, writes to disk and returns None.
        If destination is a file-like object, writes to it and returns None.
        """
        url = f"{AiohttpSession.BASE_URL}/bot/v1/messages/getFile/?file_id={file_id}"
        if destination is None:
            buffer = BytesIO()
            async for chunk in self._session.stream_content(self._token, url):
                buffer.write(chunk)
            buffer.seek(0)
            return buffer
        if isinstance(destination, Path):
            with destination.open("wb") as f:
                async for chunk in self._session.stream_content(self._token, url):
                    f.write(chunk)
            return None
        async for chunk in self._session.stream_content(self._token, url):
            destination.write(chunk)
        return None
