"""Yandex Messenger Bot API method classes."""

from yandex_messenger_bot.methods.base import YaBotMethod
from yandex_messenger_bot.methods.create_chat import CreateChat, CreateChatResult
from yandex_messenger_bot.methods.create_poll import CreatePoll, CreatePollResult
from yandex_messenger_bot.methods.delete_message import DeleteMessage, DeleteMessageResult
from yandex_messenger_bot.methods.get_file import GetFile
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

__all__ = [
    "CreateChat",
    "CreateChatResult",
    "CreatePoll",
    "CreatePollResult",
    "DeleteMessage",
    "DeleteMessageResult",
    "GetFile",
    "GetPollResults",
    "GetPollVoters",
    "GetUpdates",
    "GetUpdatesResult",
    "GetUserLink",
    "SelfUpdate",
    "SendFile",
    "SendFileResult",
    "SendGallery",
    "SendGalleryResult",
    "SendImage",
    "SendImageResult",
    "SendText",
    "SendTextResult",
    "UpdateMembers",
    "UpdateMembersResult",
    "YaBotMethod",
]
