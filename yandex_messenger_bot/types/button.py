from __future__ import annotations

from typing import Any

from pydantic import Field

from yandex_messenger_bot.types.base import YaBotObject


class Directive(YaBotObject):
    """A button directive (action to perform on click).

    Supported types:
    - open_uri: open a URL
    - send_message: send a message from the user
    - server_action: silent callback to bot
    - set_elements_state: disable/loading on UI elements
    """

    type: str
    name: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    url: str | None = Field(None, alias="uri")
    text: str | None = None
    timeout: int | None = Field(None, alias="timeout_seconds")
    ids: list[str] | None = None
    state: str | None = None


class InlineSuggestButton(YaBotObject):
    """A button in the suggest buttons layout."""

    id: str | None = None
    title: str | None = None
    directives: list[Directive] = Field(default_factory=list)


class SuggestButtons(YaBotObject):
    """Suggest buttons configuration attached to a message.

    Replaces deprecated inline_keyboard.
    """

    buttons: list[list[InlineSuggestButton]] = Field(default_factory=list)
    layout: str | None = None
    persist: bool = False
