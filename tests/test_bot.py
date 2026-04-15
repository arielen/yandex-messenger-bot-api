"""Tests for the Bot class using MockedBot / MockedSession."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from tests.mocked_bot import MockedBot, MockedSession
from yandex_messenger_bot.methods.create_chat import CreateChat
from yandex_messenger_bot.methods.create_poll import CreatePoll
from yandex_messenger_bot.methods.delete_message import DeleteMessage, DeleteMessageResult
from yandex_messenger_bot.methods.get_updates import GetUpdates, GetUpdatesResult
from yandex_messenger_bot.methods.get_user_link import GetUserLink
from yandex_messenger_bot.methods.self_update import SelfUpdate
from yandex_messenger_bot.methods.send_file import SendFile, SendFileResult
from yandex_messenger_bot.methods.send_image import SendImage, SendImageResult
from yandex_messenger_bot.methods.send_text import SendText, SendTextResult
from yandex_messenger_bot.methods.update_members import UpdateMembers
from yandex_messenger_bot.types.input_file import BufferedInputFile

# ---------------------------------------------------------------------------
# MockedSession unit tests
# ---------------------------------------------------------------------------


class TestMockedSession:
    async def test_make_request_records_method(self) -> None:
        session = MockedSession()
        method = SendText(chat_id="chat-1", text="hi")
        session.add_result({"message_id": 10})
        await session.make_request("token", method)
        recorded = session.get_request()
        assert recorded is method

    async def test_make_request_returns_queued_result(self) -> None:
        session = MockedSession()
        session.add_result({"message_id": 99})
        result = await session.make_request("token", SendText(chat_id="c", text="t"))
        assert result == {"message_id": 99}

    async def test_make_request_dequeues_in_order(self) -> None:
        session = MockedSession()
        session.add_result({"message_id": 1})
        session.add_result({"message_id": 2})
        r1 = await session.make_request("token", SendText(chat_id="c", text="a"))
        r2 = await session.make_request("token", SendText(chat_id="c", text="b"))
        assert r1 == {"message_id": 1}
        assert r2 == {"message_id": 2}

    async def test_make_request_default_for_send_text_result(self) -> None:
        """When no result is queued, returns a default valid SendTextResult."""
        session = MockedSession()
        result = await session.make_request("token", SendText(chat_id="c", text="t"))
        # Default is built from {"message_id": 0}
        assert result is not None

    async def test_make_request_default_for_delete_message_result(self) -> None:
        session = MockedSession()
        result = await session.make_request("token", DeleteMessage(chat_id="c", message_id=1))
        assert result is not None

    async def test_stream_content_yields_default_chunks(self) -> None:
        session = MockedSession()
        chunks = [c async for c in session.stream_content("token", "http://example.com")]
        assert chunks == [b"test-content"]

    async def test_stream_content_yields_custom_chunks(self) -> None:
        session = MockedSession()
        session.set_stream_chunks([b"chunk1", b"chunk2"])
        chunks = [c async for c in session.stream_content("token", "http://example.com")]
        assert chunks == [b"chunk1", b"chunk2"]

    async def test_closed_is_true_before_first_request(self) -> None:
        session = MockedSession()
        assert session.closed is True

    async def test_closed_becomes_false_after_request(self) -> None:
        session = MockedSession()
        await session.make_request("token", SendText(chat_id="c", text="t"))
        assert session.closed is False

    async def test_close_sets_closed_true(self) -> None:
        session = MockedSession()
        await session.make_request("token", SendText(chat_id="c", text="t"))
        assert session.closed is False
        await session.close()
        assert session.closed is True


# ---------------------------------------------------------------------------
# MockedBot construction and properties
# ---------------------------------------------------------------------------


class TestMockedBotConstruction:
    def test_default_token(self) -> None:
        bot = MockedBot()
        assert bot.token == "test-token-12345"

    def test_custom_token(self) -> None:
        bot = MockedBot(token="my-custom-token")
        assert bot.token == "my-custom-token"

    def test_session_is_mocked_session(self) -> None:
        bot = MockedBot()
        assert isinstance(bot.session, MockedSession)

    def test_add_result_and_get_request_delegation(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 7})
        # The result should be in the session queue now
        assert len(bot.session.responses) == 1

    async def test_get_request_pops_oldest(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 1})
        await bot(SendText(chat_id="c", text="x"))
        req = bot.get_request()
        assert isinstance(req, SendText)


# ---------------------------------------------------------------------------
# Bot context manager
# ---------------------------------------------------------------------------


class TestBotContextManager:
    async def test_aenter_returns_self(self) -> None:
        bot = MockedBot()
        result = await bot.__aenter__()
        assert result is bot
        await bot.__aexit__(None, None, None)

    async def test_aexit_closes_session(self) -> None:
        bot = MockedBot()
        # Make a request so closed flips to False
        await bot(SendText(chat_id="c", text="hi"))
        assert bot.session.closed is False
        async with bot:
            pass
        assert bot.session.closed is True

    async def test_close_calls_session_close(self) -> None:
        bot = MockedBot()
        await bot(SendText(chat_id="c", text="hi"))
        assert bot.session.closed is False
        await bot.close()
        assert bot.session.closed is True

    async def test_context_manager_closes_even_on_exception(self) -> None:
        bot = MockedBot()
        with pytest.raises(RuntimeError):
            async with bot:
                raise RuntimeError("oops")
        assert bot.session.closed is True


# ---------------------------------------------------------------------------
# Bot.__call__ — type dispatch
# ---------------------------------------------------------------------------


class TestBotCall:
    async def test_call_validates_model_from_dict(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 42})
        result = await bot(SendText(chat_id="c", text="hi"))
        assert isinstance(result, SendTextResult)
        assert result.message_id == 42

    async def test_call_returns_raw_bytes_for_bytes_returning_method(self) -> None:
        """When __returning__ is bytes, raw bytes are returned unchanged."""
        from yandex_messenger_bot.methods.get_file import GetFile

        bot = MockedBot()
        bot.add_result(b"\x89PNG")
        result = await bot(GetFile(file_id="abc"))
        assert result == b"\x89PNG"

    async def test_call_returns_raw_value_when_not_dict(self) -> None:
        """Non-dict, non-bytes results are returned as-is."""
        bot = MockedBot()
        # Pretend server returned something unexpected
        bot.add_result("unexpected-string")
        result = await bot(SendText(chat_id="c", text="hi"))
        assert result == "unexpected-string"


# ---------------------------------------------------------------------------
# Bot shortcut methods
# ---------------------------------------------------------------------------


class TestBotSendText:
    async def test_send_text_records_send_text_method(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 1})
        await bot.send_text(chat_id="chat-1", text="Hello")
        req = bot.get_request()
        assert isinstance(req, SendText)

    async def test_send_text_passes_chat_id(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 1})
        await bot.send_text(chat_id="chat-xyz", text="Hi")
        req = bot.get_request()
        assert req.chat_id == "chat-xyz"

    async def test_send_text_passes_text(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 1})
        await bot.send_text(chat_id="c", text="The message")
        req = bot.get_request()
        assert req.text == "The message"

    async def test_send_text_passes_optional_fields(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 5})
        await bot.send_text(
            chat_id="c",
            text="hi",
            reply_message_id=10,
            disable_notification=True,
            important=True,
            thread_id=3,
        )
        req = bot.get_request()
        assert req.reply_message_id == 10
        assert req.disable_notification is True
        assert req.important is True
        assert req.thread_id == 3

    async def test_send_text_with_login_instead_of_chat_id(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 2})
        await bot.send_text(login="user@org.ru", text="Direct message")
        req = bot.get_request()
        assert isinstance(req, SendText)
        assert req.login == "user@org.ru"
        assert req.chat_id is None

    async def test_send_text_returns_send_text_result(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 77})
        result = await bot.send_text(chat_id="c", text="hi")
        assert isinstance(result, SendTextResult)
        assert result.message_id == 77


class TestBotSendFile:
    async def test_send_file_records_send_file_method(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 3})
        doc = BufferedInputFile(data=b"content", filename="file.txt")
        await bot.send_file(chat_id="chat-1", document=doc)
        req = bot.get_request()
        assert isinstance(req, SendFile)

    async def test_send_file_stores_document(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 3})
        doc = BufferedInputFile(data=b"pdf", filename="report.pdf")
        await bot.send_file(chat_id="c", document=doc)
        req = bot.get_request()
        assert req.document is doc

    async def test_send_file_returns_send_file_result(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 8})
        doc = BufferedInputFile(data=b"data", filename="x.bin")
        result = await bot.send_file(chat_id="c", document=doc)
        assert isinstance(result, SendFileResult)
        assert result.message_id == 8


class TestBotSendImage:
    async def test_send_image_records_send_image_method(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 4})
        img = BufferedInputFile(data=b"\xff\xd8", filename="photo.jpg")
        await bot.send_image(chat_id="c", image=img)
        req = bot.get_request()
        assert isinstance(req, SendImage)

    async def test_send_image_stores_image(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 4})
        img = BufferedInputFile(data=b"\xff\xd8", filename="photo.jpg")
        await bot.send_image(chat_id="c", image=img)
        req = bot.get_request()
        assert req.image is img

    async def test_send_image_returns_send_image_result(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 9})
        img = BufferedInputFile(data=b"\xff\xd8", filename="p.jpg")
        result = await bot.send_image(chat_id="c", image=img)
        assert isinstance(result, SendImageResult)
        assert result.message_id == 9


class TestBotDeleteMessage:
    async def test_delete_message_records_delete_message_method(self) -> None:
        bot = MockedBot()
        bot.add_result({"ok": True})
        await bot.delete_message(chat_id="chat-1", message_id=55)
        req = bot.get_request()
        assert isinstance(req, DeleteMessage)

    async def test_delete_message_passes_chat_id_and_message_id(self) -> None:
        bot = MockedBot()
        bot.add_result({"ok": True})
        await bot.delete_message(chat_id="chat-abc", message_id=123)
        req = bot.get_request()
        assert req.chat_id == "chat-abc"
        assert req.message_id == 123

    async def test_delete_message_returns_delete_message_result(self) -> None:
        bot = MockedBot()
        bot.add_result({"ok": True})
        result = await bot.delete_message(chat_id="c", message_id=1)
        assert isinstance(result, DeleteMessageResult)
        assert result.ok is True


class TestBotGetUpdates:
    async def test_get_updates_records_get_updates_method(self) -> None:
        bot = MockedBot()
        bot.add_result({"updates": []})
        await bot.get_updates()
        req = bot.get_request()
        assert isinstance(req, GetUpdates)

    async def test_get_updates_default_params(self) -> None:
        bot = MockedBot()
        bot.add_result({"updates": []})
        await bot.get_updates()
        req = bot.get_request()
        assert req.offset == 0
        assert req.limit == 100

    async def test_get_updates_custom_params(self) -> None:
        bot = MockedBot()
        bot.add_result({"updates": []})
        await bot.get_updates(offset=50, limit=10)
        req = bot.get_request()
        assert req.offset == 50
        assert req.limit == 10

    async def test_get_updates_returns_get_updates_result(self) -> None:
        bot = MockedBot()
        bot.add_result({"updates": []})
        result = await bot.get_updates()
        assert isinstance(result, GetUpdatesResult)
        assert result.updates == []


class TestBotCreateChat:
    async def test_create_chat_records_method(self) -> None:
        bot = MockedBot()
        bot.add_result({"chat_id": "new-chat"})
        await bot.create_chat(name="Test Chat")
        req = bot.get_request()
        assert isinstance(req, CreateChat)

    async def test_create_chat_passes_name(self) -> None:
        bot = MockedBot()
        bot.add_result({"chat_id": "new-chat"})
        await bot.create_chat(name="My Group")
        req = bot.get_request()
        assert req.name == "My Group"

    async def test_create_chat_passes_optional_fields(self) -> None:
        bot = MockedBot()
        bot.add_result({"chat_id": "ch"})
        await bot.create_chat(
            name="Channel",
            description="A channel",
            members=["user1"],
            admins=["admin1"],
            is_channel=True,
        )
        req = bot.get_request()
        assert req.description == "A channel"
        assert req.members == ["user1"]
        assert req.admins == ["admin1"]
        assert req.is_channel is True


class TestBotUpdateMembers:
    async def test_update_members_records_method(self) -> None:
        bot = MockedBot()
        bot.add_result({"ok": True})
        await bot.update_members(chat_id="c", members_add=["u1"])
        req = bot.get_request()
        assert isinstance(req, UpdateMembers)

    async def test_update_members_passes_chat_id(self) -> None:
        bot = MockedBot()
        bot.add_result({"ok": True})
        await bot.update_members(chat_id="chat-xyz", members_remove=["u2"])
        req = bot.get_request()
        assert req.chat_id == "chat-xyz"
        assert req.members_remove == ["u2"]


class TestBotGetUserLink:
    async def test_get_user_link_records_method(self) -> None:
        bot = MockedBot()
        bot.add_result(
            {"chat_link": "https://example.com/chat", "call_link": "https://example.com/call"}
        )
        await bot.get_user_link(login="someuser@org.ru")
        req = bot.get_request()
        assert isinstance(req, GetUserLink)

    async def test_get_user_link_passes_login(self) -> None:
        bot = MockedBot()
        bot.add_result(
            {"chat_link": "https://example.com/chat", "call_link": "https://example.com/call"}
        )
        await bot.get_user_link(login="user@org.ru")
        req = bot.get_request()
        assert req.login == "user@org.ru"


class TestBotCreatePoll:
    async def test_create_poll_records_method(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 5})
        await bot.create_poll(chat_id="c", title="Pick one", answers=["A", "B"])
        req = bot.get_request()
        assert isinstance(req, CreatePoll)

    async def test_create_poll_passes_title_and_answers(self) -> None:
        bot = MockedBot()
        bot.add_result({"message_id": 5})
        await bot.create_poll(chat_id="c", title="Q?", answers=["Yes", "No"])
        req = bot.get_request()
        assert req.title == "Q?"
        assert req.answers == ["Yes", "No"]


class TestBotSelfUpdate:
    async def test_self_update_records_method(self) -> None:
        bot = MockedBot()
        bot.add_result({"id": "bot-id-123", "display_name": "Test Bot"})
        await bot.self_update(webhook_url="https://example.com/hook")
        req = bot.get_request()
        assert isinstance(req, SelfUpdate)

    async def test_self_update_passes_webhook_url(self) -> None:
        bot = MockedBot()
        bot.add_result({"id": "bot-id-123", "display_name": "Bot"})
        await bot.self_update(webhook_url="https://my.server/hook")
        req = bot.get_request()
        assert req.webhook_url == "https://my.server/hook"

    async def test_self_update_clears_webhook_with_none(self) -> None:
        bot = MockedBot()
        bot.add_result({"id": "bot-id-123", "display_name": "Bot"})
        await bot.self_update(webhook_url=None)
        req = bot.get_request()
        assert req.webhook_url is None


# ---------------------------------------------------------------------------
# Bot.download
# ---------------------------------------------------------------------------


class TestBotDownload:
    async def test_download_to_bytesio_returns_buffer(self) -> None:
        bot = MockedBot()
        bot.session.set_stream_chunks([b"file-", b"data"])
        result = await bot.download("file-id-123")
        assert isinstance(result, BytesIO)
        assert result.read() == b"file-data"

    async def test_download_to_bytesio_buffer_is_seeked_to_zero(self) -> None:
        bot = MockedBot()
        bot.session.set_stream_chunks([b"hello"])
        result = await bot.download("any-id")
        assert result is not None
        assert result.tell() == 0

    async def test_download_empty_file_returns_empty_bytesio(self) -> None:
        bot = MockedBot()
        bot.session.set_stream_chunks([b""])
        result = await bot.download("id")
        assert result is not None
        assert result.read() == b""

    async def test_download_to_path_writes_file(self, tmp_path: Path) -> None:
        bot = MockedBot()
        bot.session.set_stream_chunks([b"bytes-on-disk"])
        dest = tmp_path / "output.bin"
        result = await bot.download("file-id", destination=dest)
        assert result is None
        assert dest.read_bytes() == b"bytes-on-disk"

    async def test_download_to_path_returns_none(self, tmp_path: Path) -> None:
        bot = MockedBot()
        bot.session.set_stream_chunks([b"x"])
        dest = tmp_path / "out.bin"
        result = await bot.download("id", destination=dest)
        assert result is None

    async def test_download_to_fileobj_writes_and_returns_none(self) -> None:
        bot = MockedBot()
        bot.session.set_stream_chunks([b"written"])
        buf = BytesIO()
        result = await bot.download("id", destination=buf)
        assert result is None
        buf.seek(0)
        assert buf.read() == b"written"

    async def test_download_url_uses_file_id(self) -> None:
        """The URL built for streaming must contain the file_id."""
        bot = MockedBot()
        recorded_urls: list[str] = []

        async def capturing_stream(token: str, url: str):  # type: ignore[return]
            recorded_urls.append(url)
            yield b"data"

        bot.session.stream_content = capturing_stream  # type: ignore[method-assign]
        await bot.download("xyz-file-id")
        assert len(recorded_urls) == 1
        assert "xyz-file-id" in recorded_urls[0]

    async def test_download_multi_chunk_concatenated(self) -> None:
        bot = MockedBot()
        bot.session.set_stream_chunks([b"part1-", b"part2-", b"part3"])
        result = await bot.download("id")
        assert result is not None
        assert result.read() == b"part1-part2-part3"
