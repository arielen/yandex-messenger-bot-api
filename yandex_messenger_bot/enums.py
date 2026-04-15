from enum import StrEnum


class ChatType(StrEnum):
    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"


class DirectiveType(StrEnum):
    OPEN_URI = "open_uri"
    SEND_MESSAGE = "send_message"
    SERVER_ACTION = "server_action"
    SET_ELEMENTS_STATE = "set_elements_state"
