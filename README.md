# yandex-messenger-bot

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Typing: typed](https://img.shields.io/badge/typing-typed-blue.svg)](https://peps.python.org/pep-0561/)

Modern, fully asynchronous Python framework for the [Yandex Messenger Bot API](https://yandex.ru/dev/messenger/).

## Features

- Full API coverage — all 14 endpoints (messages, files, images, galleries, polls, chats, webhooks)
- Pydantic v2 models for all API types with strict validation
- Router/Dispatcher system with depth-first propagation
- MagicFilter support (`F.text`, `F.chat.type == "group"`, etc.)
- FSM (Finite State Machine) with pluggable storage
- Dependency injection via `Annotated[T, Inject()]` with type checker support
- Middleware chain (inner + outer)
- Polling and webhook transports with auto-retry and backoff
- Typed exception hierarchy mapped to HTTP status codes
- `py.typed` — full inline type annotations

## Installation

```bash
pip install yandex-messenger-bot
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add yandex-messenger-bot
```

## Quick Start

```python
import asyncio

from yandex_messenger_bot import Bot, Dispatcher, Router
from yandex_messenger_bot.filters.command import CommandFilter
from yandex_messenger_bot.types import Update

router = Router()


@router.on_message(CommandFilter("start"))
async def on_start(update: Update, bot: Bot) -> None:
    await bot.send_text(chat_id=update.chat.id, text="Hello!")


async def main() -> None:
    bot = Bot(token="your-oauth-token")
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

## Sending Messages

```python
# Text
await bot.send_text(chat_id="chat-id", text="Hello!")

# By user login
await bot.send_text(login="user@company.ru", text="Hi there")

# File
from yandex_messenger_bot.types import FSInputFile

doc = FSInputFile("report.pdf")
await bot.send_file(chat_id="chat-id", document=doc)

# Image
img = FSInputFile("photo.jpg")
await bot.send_image(chat_id="chat-id", image=img)

# Gallery (up to 10 images)
images = [FSInputFile(f"img_{i}.jpg") for i in range(5)]
await bot.send_gallery(chat_id="chat-id", images=images, text="Album caption")
```

## Buttons (SuggestButtons)

```python
from yandex_messenger_bot.types import Directive, InlineSuggestButton, SuggestButtons

buttons = SuggestButtons(
    buttons=[
        [
            InlineSuggestButton(
                title="Open site",
                directives=[Directive(type="open_uri", url="https://example.com")],
            ),
            InlineSuggestButton(
                title="Confirm",
                directives=[
                    Directive(type="server_action", name="confirm", payload={"id": 42})
                ],
            ),
        ]
    ],
    persist=True,
)

await bot.send_text(chat_id="chat-id", text="Choose:", suggest_buttons=buttons)
```

## Handling Button Callbacks

```python
from yandex_messenger_bot.filters.callback import ServerActionFilter
from yandex_messenger_bot.types import ServerAction


@router.on_bot_request(ServerActionFilter("confirm"))
async def on_confirm(update: Update, bot: Bot, server_action: ServerAction) -> None:
    item_id = server_action.payload["id"]
    await bot.send_text(chat_id=update.chat.id, text=f"Confirmed item {item_id}")
```

## FSM (Conversation State)

```python
from yandex_messenger_bot import State, StatesGroup, FSMContext
from yandex_messenger_bot.filters.state import StateFilter


class Form(StatesGroup):
    name = State()
    email = State()


@router.on_message(CommandFilter("form"))
async def form_start(update: Update, bot: Bot, state: FSMContext) -> None:
    await state.set_state(Form.name)
    await bot.send_text(chat_id=update.chat.id, text="Enter your name:")


@router.on_message(StateFilter(Form.name))
async def process_name(update: Update, bot: Bot, state: FSMContext) -> None:
    await state.update_data(name=update.text)
    await state.set_state(Form.email)
    await bot.send_text(chat_id=update.chat.id, text="Enter your email:")


@router.on_message(StateFilter(Form.email))
async def process_email(update: Update, bot: Bot, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    await bot.send_text(
        chat_id=update.chat.id,
        text=f"Saved: {data['name']}, {update.text}",
    )
```

## Middleware

```python
from yandex_messenger_bot import BaseMiddleware
from yandex_messenger_bot.types import Update


class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, update: Update, data: dict) -> None:
        print(f"Update {update.update_id} from {update.from_user}")
        return await handler(update, data)


router.message.outer_middleware(LoggingMiddleware())
```

## Dependency Injection

```python
from typing import Annotated
from yandex_messenger_bot import Inject


class Database:
    async def get_user(self, login: str) -> dict: ...


async def get_database() -> Database:
    return Database()


# Register globally
dp.dependency(Database, factory=get_database)


# Or inline via Annotated
@router.on_message(CommandFilter("profile"))
async def profile(
    update: Update,
    bot: Bot,
    db: Annotated[Database, Inject(factory=get_database)],
) -> None:
    user = await db.get_user(update.from_user.login)
    await bot.send_text(chat_id=update.chat.id, text=str(user))
```

## Webhook Mode

```python
from aiohttp import web
from yandex_messenger_bot.webhook import WebhookHandler


async def main() -> None:
    bot = Bot(token="your-token")
    dp = Dispatcher()
    dp.include_router(router)

    # Set webhook URL in Yandex
    await bot.self_update(webhook_url="https://your-server.com/webhook")

    # Start aiohttp server
    wh = WebhookHandler(dp, bot, secret_token="your-secret")
    app = web.Application()
    wh.setup(app, path="/webhook")
    web.run_app(app, port=8080)
```

## Polls

```python
# Create a poll
await bot.create_poll(
    chat_id="chat-id",
    title="Lunch spot?",
    answers=["Sushi", "Pizza", "Burgers"],
    max_choices=1,
    is_anonymous=False,
)

# Get results
results = await bot.get_poll_results(chat_id="chat-id", message_id=12345)
print(results.voted_count, results.answers)
```

## Chat Management

```python
# Create a group chat
result = await bot.create_chat(
    name="Project Team",
    description="Discussion",
    members=["alice@company.ru", "bob@company.ru"],
    admins=["alice@company.ru"],
)

# Add/remove members
await bot.update_members(
    chat_id=result.chat_id,
    members_add=["charlie@company.ru"],
    members_remove=["bob@company.ru"],
)
```

## Error Handling

```python
from yandex_messenger_bot.exceptions import (
    APIError,
    TooManyRequestsError,
    ForbiddenError,
)

try:
    await bot.send_text(chat_id="chat-id", text="Hello")
except TooManyRequestsError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except ForbiddenError:
    print("Bot doesn't have access to this chat")
except APIError as e:
    print(f"API error {e.status_code}: {e.description}")
```

## Development

```bash
# Install dependencies
uv sync --all-groups

# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run ty check yandex_messenger_bot/
```

## License

MIT
