"""Tests for SDK method models: serialization, HTTP metadata, multipart flags."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from yandex_messenger_bot.methods.get_updates import GetUpdates
from yandex_messenger_bot.methods.send_file import SendFile
from yandex_messenger_bot.methods.send_text import SendText
from yandex_messenger_bot.types.button import Directive, InlineSuggestButton, SuggestButtons
from yandex_messenger_bot.types.input_file import BufferedInputFile

# ---------------------------------------------------------------------------
# SendText
# ---------------------------------------------------------------------------


class TestSendText:
    def test_api_path(self):
        assert SendText.__api_path__ == "/bot/v1/messages/sendText/"

    def test_http_method_is_post(self):
        assert SendText.__http_method__ == "POST"

    def test_not_multipart(self):
        assert SendText.__multipart__ is False

    def test_minimal_serialization(self):
        m = SendText(chat_id="chat-1", text="Hello")
        dumped = m.model_dump(exclude_none=True)
        assert dumped["chat_id"] == "chat-1"
        assert dumped["text"] == "Hello"

    def test_exclude_none_omits_optional_fields(self):
        m = SendText(chat_id="chat-1", text="Hi")
        dumped = m.model_dump(exclude_none=True)
        # optional fields with None must not appear in the payload
        assert "login" not in dumped
        assert "reply_message_id" not in dumped
        assert "thread_id" not in dumped
        assert "payload_id" not in dumped
        assert "inline_keyboard" not in dumped
        assert "suggest_buttons" not in dumped

    def test_bool_defaults_are_present(self):
        m = SendText(chat_id="chat-1", text="Hi")
        dumped = m.model_dump()
        assert dumped["disable_notification"] is False
        assert dumped["important"] is False
        assert dumped["disable_web_page_preview"] is False

    def test_all_optional_fields(self):
        sb = SuggestButtons(
            buttons=[
                [
                    InlineSuggestButton(
                        title="Yes", directives=[Directive(type="send_message", text="yes")]
                    )
                ]
            ],
        )
        m = SendText(
            chat_id="chat-1",
            text="Choose:",
            reply_message_id=55,
            disable_notification=True,
            important=True,
            thread_id=3,
            suggest_buttons=sb,
        )
        dumped = m.model_dump(exclude_none=True)
        assert dumped["reply_message_id"] == 55
        assert dumped["disable_notification"] is True
        assert dumped["important"] is True
        assert dumped["thread_id"] == 3
        assert dumped["suggest_buttons"]["buttons"][0][0]["title"] == "Yes"

    def test_is_frozen(self):
        m = SendText(chat_id="chat-1", text="Hi")
        with pytest.raises(ValidationError):
            m.text = "mutated"  # type: ignore[misc]

    def test_returning_type(self):
        from yandex_messenger_bot.methods.send_text import SendTextResult

        assert SendText.__returning__ is SendTextResult


# ---------------------------------------------------------------------------
# GetUpdates
# ---------------------------------------------------------------------------


class TestGetUpdates:
    def test_api_path(self):
        assert GetUpdates.__api_path__ == "/bot/v1/messages/getUpdates/"

    def test_http_method_is_get(self):
        assert GetUpdates.__http_method__ == "GET"

    def test_not_multipart(self):
        assert GetUpdates.__multipart__ is False

    def test_defaults(self):
        m = GetUpdates()
        assert m.offset == 0
        assert m.limit == 100

    def test_custom_offset_and_limit(self):
        m = GetUpdates(offset=50, limit=10)
        dumped = m.model_dump()
        assert dumped["offset"] == 50
        assert dumped["limit"] == 10

    def test_returning_type(self):
        from yandex_messenger_bot.methods.get_updates import GetUpdatesResult

        assert GetUpdates.__returning__ is GetUpdatesResult


# ---------------------------------------------------------------------------
# SendFile
# ---------------------------------------------------------------------------


class TestSendFile:
    def test_api_path(self):
        assert SendFile.__api_path__ == "/bot/v1/messages/sendFile/"

    def test_http_method_is_post(self):
        assert SendFile.__http_method__ == "POST"

    def test_is_multipart(self):
        assert SendFile.__multipart__ is True

    def test_document_field_excluded_from_model_dump(self):
        """InputFile must be excluded from JSON payload; it is handled separately as multipart."""
        doc = BufferedInputFile(data=b"pdf content", filename="report.pdf")
        m = SendFile(chat_id="chat-1", document=doc)
        dumped = m.model_dump(exclude_none=True)
        assert "document" not in dumped

    def test_non_document_fields_in_model_dump(self):
        doc = BufferedInputFile(data=b"data", filename="file.bin")
        m = SendFile(chat_id="chat-1", document=doc, thread_id=7)
        dumped = m.model_dump(exclude_none=True)
        assert dumped["chat_id"] == "chat-1"
        assert dumped["thread_id"] == 7

    def test_returning_type(self):
        from yandex_messenger_bot.methods.send_file import SendFileResult

        assert SendFile.__returning__ is SendFileResult


# ---------------------------------------------------------------------------
# HTTP method contract across all methods
# ---------------------------------------------------------------------------


class TestHTTPMethodContracts:
    """Verify GET vs POST assignments are correct and not accidentally swapped."""

    def test_get_updates_is_get_not_post(self):
        assert GetUpdates.__http_method__ == "GET"
        assert GetUpdates.__http_method__ != "POST"

    def test_send_text_is_post_not_get(self):
        assert SendText.__http_method__ == "POST"
        assert SendText.__http_method__ != "GET"

    def test_send_file_is_post_not_get(self):
        assert SendFile.__http_method__ == "POST"
        assert SendFile.__http_method__ != "GET"


# ---------------------------------------------------------------------------
# UpdateMembers
# ---------------------------------------------------------------------------


class TestUpdateMembers:
    def setup_method(self):
        from yandex_messenger_bot.methods.update_members import UpdateMembers

        self.UpdateMembers = UpdateMembers

    def test_update_members_api_path(self):
        assert self.UpdateMembers.__api_path__ == "/bot/v1/chats/updateMembers/"

    def test_update_members_http_method_is_post(self):
        assert self.UpdateMembers.__http_method__ == "POST"

    def test_update_members_not_multipart(self):
        assert self.UpdateMembers.__multipart__ is False

    def test_update_members_minimal_serialization_only_chat_id(self):
        m = self.UpdateMembers(chat_id="chat-42")
        dumped = m.model_dump(exclude_none=True)
        assert dumped == {"chat_id": "chat-42"}

    def test_update_members_members_serialized_as_user_objects(self):
        m = self.UpdateMembers(chat_id="c1", members=["alice@org", "bob@org"])
        dumped = m.model_dump(exclude_none=True)
        assert dumped["members"] == [{"login": "alice@org"}, {"login": "bob@org"}]

    def test_update_members_admins_serialized_as_user_objects(self):
        m = self.UpdateMembers(chat_id="c1", admins=["admin@org"])
        dumped = m.model_dump(exclude_none=True)
        assert dumped["admins"] == [{"login": "admin@org"}]

    def test_update_members_subscribers_serialized_as_user_objects(self):
        m = self.UpdateMembers(chat_id="c1", subscribers=["sub@org"])
        dumped = m.model_dump(exclude_none=True)
        assert dumped["subscribers"] == [{"login": "sub@org"}]

    def test_update_members_remove_serialized_as_user_objects(self):
        m = self.UpdateMembers(chat_id="c1", remove=["gone@org"])
        dumped = m.model_dump(exclude_none=True)
        assert dumped["remove"] == [{"login": "gone@org"}]

    def test_update_members_no_old_field_names(self):
        """Ensure old wrong field names no longer exist on the model."""
        field_names = set(self.UpdateMembers.model_fields.keys())
        assert "members_add" not in field_names
        assert "members_remove" not in field_names
        assert "admins_add" not in field_names
        assert "admins_remove" not in field_names
        assert "subscribers_add" not in field_names
        assert "subscribers_remove" not in field_names

    def test_update_members_all_four_api_fields_present(self):
        m = self.UpdateMembers(
            chat_id="c1",
            members=["m@org"],
            admins=["a@org"],
            subscribers=["s@org"],
            remove=["r@org"],
        )
        dumped = m.model_dump(exclude_none=True)
        assert dumped["members"] == [{"login": "m@org"}]
        assert dumped["admins"] == [{"login": "a@org"}]
        assert dumped["subscribers"] == [{"login": "s@org"}]
        assert dumped["remove"] == [{"login": "r@org"}]
