"""Tests for SDK types: serialization, deserialization, constraints."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from yandex_messenger_bot.enums import ChatType
from yandex_messenger_bot.types.bot_request import BotRequest, BotRequestError, ServerAction
from yandex_messenger_bot.types.button import Directive, InlineSuggestButton, SuggestButtons
from yandex_messenger_bot.types.chat import Chat
from yandex_messenger_bot.types.file import Document, Image
from yandex_messenger_bot.types.forward import ForwardInfo
from yandex_messenger_bot.types.input_file import BufferedInputFile, FSInputFile, URLInputFile
from yandex_messenger_bot.types.update import Update
from yandex_messenger_bot.types.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_UPDATE_RAW = {
    "update_id": 1,
    "message_id": 100,
    "timestamp": 1700000000,
    "chat": {"id": "chat-abc"},
}

FULL_UPDATE_RAW = {
    "update_id": 42,
    "message_id": 999,
    "timestamp": 1700000000,
    "chat": {
        "id": "group-xyz",
        "type": "group",
        "title": "Dev team",
        "organization_id": "org-1",
        "description": "Developer chat",
        "is_channel": False,
    },
    "from": {
        "id": "user-777",
        "login": "alice",
        "display_name": "Alice",
        "robot": False,
    },
    "text": "Hello world",
    "thread_id": 5,
    "document": {
        "id": "doc-id-1",
        "name": "report.pdf",
        "mime_type": "application/pdf",
        "size": 204800,
    },
    "images": [
        [
            {"file_id": "img-small", "width": 100, "height": 75, "size": 4096},
            {"file_id": "img-large", "width": 800, "height": 600, "size": 32768},
        ]
    ],
    "forward": {
        "from": {"id": "user-888", "login": "bob", "display_name": "Bob", "robot": False},
        "chat": {"id": "chat-source"},
        "message_id": 55,
    },
    "bot_request": {
        "server_action": {"name": "button_clicked", "payload": {"key": "val"}},
        "element_id": "btn-1",
        "errors": [],
    },
}


# ---------------------------------------------------------------------------
# Update parsing
# ---------------------------------------------------------------------------


class TestUpdateParsing:
    def test_minimal_update_parses(self):
        u = Update.model_validate(MINIMAL_UPDATE_RAW)
        assert u.update_id == 1
        assert u.message_id == 100
        assert u.timestamp == 1700000000
        assert u.chat.id == "chat-abc"

    def test_full_update_scalar_fields(self):
        u = Update.model_validate(FULL_UPDATE_RAW)
        assert u.update_id == 42
        assert u.text == "Hello world"
        assert u.thread_id == 5

    def test_full_update_nested_chat(self):
        u = Update.model_validate(FULL_UPDATE_RAW)
        assert isinstance(u.chat, Chat)
        assert u.chat.id == "group-xyz"
        assert u.chat.type == ChatType.GROUP
        assert u.chat.title == "Dev team"
        assert u.chat.organization_id == "org-1"
        assert u.chat.is_channel is False

    def test_full_update_nested_user_via_from_alias(self):
        """The API sends 'from'; SDK must map it to from_user."""
        u = Update.model_validate(FULL_UPDATE_RAW)
        assert isinstance(u.from_user, User)
        assert u.from_user.id == "user-777"
        assert u.from_user.login == "alice"
        assert u.from_user.robot is False

    def test_full_update_document(self):
        u = Update.model_validate(FULL_UPDATE_RAW)
        assert isinstance(u.document, Document)
        assert u.document.id == "doc-id-1"
        assert u.document.mime_type == "application/pdf"
        assert u.document.size == 204800

    def test_images_2d_array(self):
        """Yandex returns images as array of arrays (size variants per row)."""
        u = Update.model_validate(FULL_UPDATE_RAW)
        assert u.images is not None
        assert len(u.images) == 1  # one row
        row = u.images[0]
        assert len(row) == 2  # two size variants
        small, large = row
        assert isinstance(small, Image)
        assert small.file_id == "img-small"
        assert small.width == 100
        assert large.file_id == "img-large"
        assert large.width == 800

    def test_forward_info_parsing(self):
        u = Update.model_validate(FULL_UPDATE_RAW)
        assert isinstance(u.forward, ForwardInfo)
        assert u.forward.from_user is not None
        assert u.forward.from_user.login == "bob"
        assert u.forward.chat is not None
        assert u.forward.chat.id == "chat-source"
        assert u.forward.message_id == 55

    def test_bot_request_parsing(self):
        u = Update.model_validate(FULL_UPDATE_RAW)
        assert isinstance(u.bot_request, BotRequest)
        sa = u.bot_request.server_action
        assert isinstance(sa, ServerAction)
        assert sa.name == "button_clicked"
        assert sa.payload == {"key": "val"}
        assert u.bot_request.element_id == "btn-1"
        assert u.bot_request.errors == []

    def test_optional_fields_default_to_none(self):
        u = Update.model_validate(MINIMAL_UPDATE_RAW)
        assert u.from_user is None
        assert u.text is None
        assert u.thread_id is None
        assert u.forward is None
        assert u.document is None
        assert u.images is None
        assert u.bot_request is None

    def test_extra_fields_are_accepted(self):
        """Forward-compat: unknown fields from API must not raise errors."""
        raw = {**MINIMAL_UPDATE_RAW, "new_field_from_future_api": "something"}
        u = Update.model_validate(raw)
        assert u.update_id == 1  # normal field still works


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


class TestFrozenModels:
    def test_update_is_frozen(self):
        u = Update.model_validate(MINIMAL_UPDATE_RAW)
        with pytest.raises(ValidationError):  # pydantic raises ValidationError or TypeError
            u.update_id = 99  # type: ignore[misc]

    def test_chat_is_frozen(self):
        chat = Chat(id="chat-1")
        with pytest.raises(ValidationError):
            chat.id = "mutated"  # type: ignore[misc]

    def test_user_is_frozen(self):
        user = User(id="u-1", login="alice")
        with pytest.raises(ValidationError):
            user.login = "mallory"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class TestChat:
    def test_is_channel_default_false(self):
        chat = Chat(id="c-1")
        assert chat.is_channel is False

    def test_chat_type_enum_coercion(self):
        chat = Chat.model_validate({"id": "c-2", "type": "private"})
        assert chat.type == ChatType.PRIVATE

    def test_chat_type_channel(self):
        chat = Chat.model_validate({"id": "c-3", "type": "channel", "is_channel": True})
        assert chat.type == ChatType.CHANNEL
        assert chat.is_channel is True


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------


class TestButtons:
    def test_directive_round_trip(self):
        d = Directive(type="open_uri", url="https://example.com")
        dumped = d.model_dump(exclude_none=True)
        assert dumped["type"] == "open_uri"
        assert dumped["url"] == "https://example.com"
        assert "name" not in dumped

    def test_server_action_directive(self):
        d = Directive(
            type="server_action",
            name="do_thing",
            payload={"action_id": 7},
        )
        dumped = d.model_dump()
        assert dumped["payload"] == {"action_id": 7}

    def test_suggest_buttons_round_trip(self):
        btn = InlineSuggestButton(
            title="Click me",
            directives=[Directive(type="send_message", text="Hello")],
        )
        sb = SuggestButtons(buttons=[[btn]], layout="vertical")
        dumped = sb.model_dump()
        assert dumped["layout"] == "vertical"
        assert dumped["persist"] is False
        row = dumped["buttons"][0]
        assert row[0]["title"] == "Click me"
        assert row[0]["directives"][0]["type"] == "send_message"

    def test_suggest_buttons_defaults(self):
        sb = SuggestButtons()
        assert sb.buttons == []
        assert sb.persist is False
        assert sb.layout is None

    def test_directive_payload_defaults_to_empty_dict(self):
        d = Directive(type="open_uri")
        assert d.payload == {}


# ---------------------------------------------------------------------------
# BotRequest
# ---------------------------------------------------------------------------


class TestBotRequest:
    def test_bot_request_with_errors(self):
        raw = {
            "element_id": "btn-2",
            "errors": [
                {"type": "timeout", "name": "RequestTimeout", "message": "Too slow"},
            ],
        }
        br = BotRequest.model_validate(raw)
        assert len(br.errors) == 1
        err = br.errors[0]
        assert isinstance(err, BotRequestError)
        assert err.type == "timeout"
        assert err.message == "Too slow"

    def test_bot_request_empty_defaults(self):
        br = BotRequest()
        assert br.server_action is None
        assert br.element_id is None
        assert br.errors == []


# ---------------------------------------------------------------------------
# InputFile
# ---------------------------------------------------------------------------


class TestInputFile:
    async def test_buffered_input_file_yields_exact_bytes(self):
        data = b"hello buffered world"
        f = BufferedInputFile(data=data, filename="test.txt")
        assert f.filename == "test.txt"
        chunks = [chunk async for chunk in f.read()]
        assert chunks == [data]

    async def test_buffered_input_file_preserves_binary_data(self):
        data = bytes(range(256))  # all byte values
        f = BufferedInputFile(data=data, filename="binary.bin")
        chunks = [chunk async for chunk in f.read()]
        assert b"".join(chunks) == data

    async def test_fs_input_file_reads_file(self):
        content = b"file system content"
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            f = FSInputFile(path=tmp_path)
            assert f.filename == tmp_path.name
            chunks = [chunk async for chunk in f.read()]
            assert b"".join(chunks) == content
        finally:
            tmp_path.unlink()

    async def test_fs_input_file_custom_filename(self):
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
            tmp.write(b"x")
            tmp_path = Path(tmp.name)

        try:
            f = FSInputFile(path=tmp_path, filename="override.txt")
            assert f.filename == "override.txt"
        finally:
            tmp_path.unlink()

    async def test_fs_input_file_respects_chunk_size(self):
        data = b"a" * 1000
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)

        try:
            f = FSInputFile(path=tmp_path, chunk_size=300)
            chunks = [chunk async for chunk in f.read()]
            assert len(chunks) == 4  # ceil(1000/300)
            assert b"".join(chunks) == data
        finally:
            tmp_path.unlink()

    async def test_url_input_file_raises_on_read(self):
        f = URLInputFile(url="https://example.com/file.pdf")
        assert f.url == "https://example.com/file.pdf"
        with pytest.raises(NotImplementedError):
            async for _ in f.read():
                pass

    def test_url_input_file_stores_url(self):
        f = URLInputFile(url="https://cdn.example.com/img.png", filename="img.png")
        assert f.url == "https://cdn.example.com/img.png"
        assert f.filename == "img.png"
