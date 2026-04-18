# Yandex Messenger Bot SDK — Architecture Design

## 1. Package Name & Structure

Package name: `ya_bot` (short, importable, unique on PyPI)

```
ya_bot/
├── __init__.py              # Public API: Bot, Dispatcher, Router, F
├── _meta.py                 # __version__
├── exceptions.py            # Exception hierarchy
├── enums.py                 # ChatType, UpdateType enums
│
├── types/                   # Pydantic v2 models for API objects
│   ├── __init__.py          # Re-exports all types
│   ├── base.py              # YaBotObject(BaseModel) — base for all types
│   ├── user.py              # User
│   ├── chat.py              # Chat
│   ├── message.py           # Message (incoming update)
│   ├── update.py            # Update (wrapper)
│   ├── file.py              # Document, Image, Sticker
│   ├── button.py            # InlineButton, SuggestButtons, Directive
│   ├── poll.py              # Poll, PollResults, PollVoter
│   ├── bot_request.py       # BotRequest, ServerAction
│   ├── forward.py           # ForwardInfo
│   └── input_file.py        # InputFile, BufferedInputFile, FSInputFile, URLInputFile
│
├── methods/                 # API method models (one per endpoint)
│   ├── __init__.py
│   ├── base.py              # YaBotMethod[T] — base for all methods
│   ├── send_text.py         # SendText
│   ├── send_file.py         # SendFile
│   ├── send_image.py        # SendImage
│   ├── send_gallery.py      # SendGallery
│   ├── get_file.py          # GetFile
│   ├── delete_message.py    # DeleteMessage
│   ├── get_updates.py       # GetUpdates
│   ├── create_chat.py       # CreateChat
│   ├── update_members.py    # UpdateMembers
│   ├── get_user_link.py     # GetUserLink
│   ├── create_poll.py       # CreatePoll
│   ├── get_poll_results.py  # GetPollResults
│   ├── get_poll_voters.py   # GetPollVoters
│   └── self_update.py       # SelfUpdate (webhook config)
│
├── client/                  # Bot class + HTTP layer
│   ├── __init__.py
│   ├── bot.py               # Bot — main entry, API method shortcuts
│   └── session/
│       ├── __init__.py
│       ├── base.py          # BaseSession ABC
│       └── aiohttp.py       # AiohttpSession
│
├── dispatcher/              # Event dispatching
│   ├── __init__.py
│   ├── dispatcher.py        # Dispatcher (root Router subclass)
│   ├── router.py            # Router — handler registration, tree structure
│   ├── handler.py           # HandlerObject — wraps callback + filters
│   └── middlewares/
│       ├── __init__.py
│       ├── base.py          # BaseMiddleware ABC
│       ├── manager.py       # MiddlewareManager (chain builder)
│       └── user_context.py  # Extracts user/chat from updates
│
├── filters/                 # Filter system
│   ├── __init__.py
│   ├── base.py              # BaseFilter ABC
│   ├── command.py           # CommandFilter
│   ├── state.py             # StateFilter
│   ├── callback.py          # ServerActionFilter
│   └── magic.py             # F (MagicFilter proxy)
│
├── fsm/                     # Finite State Machine
│   ├── __init__.py
│   ├── state.py             # State, StatesGroup
│   ├── context.py           # FSMContext
│   ├── strategy.py          # FSMStrategy enum
│   ├── middleware.py         # FSMContextMiddleware
│   └── storage/
│       ├── __init__.py
│       ├── base.py          # BaseStorage ABC, StorageKey
│       └── memory.py        # MemoryStorage
│
├── di/                      # Dependency Injection
│   ├── __init__.py
│   ├── inject.py            # Inject marker, resolve logic
│   └── provider.py          # Provider registry
│
├── polling/                 # Long-polling transport
│   ├── __init__.py
│   └── polling.py           # Polling loop with backoff
│
└── webhook/                 # Webhook transport
    ├── __init__.py
    └── aiohttp_server.py    # aiohttp webhook handler
```

## 2. Types System

All types inherit from `YaBotObject(pydantic.BaseModel)`:

```python
class YaBotObject(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="allow",           # forward-compat: unknown fields don't break
        populate_by_name=True,
        use_enum_values=True,
    )
```

### Key Types

```python
class User(YaBotObject):
    id: str                          # UUID
    login: str
    display_name: str
    robot: bool = False

class Chat(YaBotObject):
    id: str
    type: ChatType                   # "private" | "group" | "channel"
    organization_id: str | None = None
    title: str | None = None
    description: str | None = None
    is_channel: bool = False

class Document(YaBotObject):
    id: str
    name: str
    mime_type: str | None = None
    size: int | None = None

class Image(YaBotObject):
    file_id: str
    width: int | None = None
    height: int | None = None
    size: int | None = None
    name: str | None = None

class Sticker(YaBotObject):
    id: str
    emoji: str | None = None

class ForwardInfo(YaBotObject):
    from_user: User | None = Field(None, alias="from")
    chat: Chat | None = None
    message_id: int | None = None

class ServerAction(YaBotObject):
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)

class BotRequest(YaBotObject):
    server_action: ServerAction | None = None
    element_id: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)

class Message(YaBotObject):
    """Incoming message from an update."""
    message_id: int
    update_id: int
    timestamp: int
    chat: Chat
    from_user: User | None = Field(None, alias="from")
    text: str | None = None
    thread_id: int | None = None
    forward: ForwardInfo | None = None
    sticker: Sticker | None = None
    image: Image | None = None
    images: list[list[Image]] | None = None   # 2D array: variants per image
    document: Document | None = None
    bot_request: BotRequest | None = None

class Update(YaBotObject):
    """Raw update from getUpdates / webhook."""
    update_id: int
    message: Message | None = None
    # Future: may have other update types
```

### InputFile types (for uploads)

```python
class InputFile(ABC):
    filename: str | None

    @abstractmethod
    async def read(self) -> AsyncIterator[bytes]: ...

class BufferedInputFile(InputFile):
    """From in-memory bytes."""
    def __init__(self, data: bytes, filename: str): ...

class FSInputFile(InputFile):
    """From filesystem path."""
    def __init__(self, path: str | Path, filename: str | None = None): ...

class URLInputFile(InputFile):
    """Stream from URL."""
    def __init__(self, url: str, filename: str | None = None): ...
```

## 3. Methods System

Each API method is a Pydantic model with a `__api_path__` and `__http_method__` and a return type `T`:

```python
TResult = TypeVar("TResult")

class YaBotMethod(BaseModel, Generic[TResult], ABC):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    @classmethod
    @abstractmethod
    def __api_path__(cls) -> str: ...

    @classmethod
    def __http_method__(cls) -> str:
        return "POST"

    @classmethod
    @abstractmethod
    def __returning__(cls) -> type[TResult]: ...

class SendText(YaBotMethod[Message]):
    chat_id: str | None = None
    login: str | None = None
    text: str                                    # max 6000
    payload_id: str | None = None                # idempotency
    reply_message_id: int | None = None
    disable_notification: bool = False
    important: bool = False
    disable_web_page_preview: bool = False
    thread_id: int | None = None
    inline_keyboard: list[dict] | None = None    # deprecated
    suggest_buttons: SuggestButtons | None = None

    @classmethod
    def __api_path__(cls) -> str:
        return "/bot/v1/messages/sendText/"

    @classmethod
    def __returning__(cls) -> type[Message]:
        return Message
```

### All methods:

| Class | Path | HTTP | Returns |
|---|---|---|---|
| SendText | /bot/v1/messages/sendText/ | POST | Message |
| SendFile | /bot/v1/messages/sendFile/ | POST (multipart) | Message |
| SendImage | /bot/v1/messages/sendImage/ | POST (multipart) | Message |
| SendGallery | /bot/v1/messages/sendGallery/ | POST (multipart) | Message |
| GetFile | /bot/v1/messages/getFile/ | GET | bytes (streaming) |
| DeleteMessage | /bot/v1/messages/delete/ | POST | bool |
| GetUpdates | /bot/v1/messages/getUpdates/ | GET | list[Update] |
| CreateChat | /bot/v1/chats/create/ | POST | Chat |
| UpdateMembers | /bot/v1/chats/updateMembers/ | POST | bool |
| GetUserLink | /bot/v1/users/getUserLink/ | GET | UserLink |
| CreatePoll | /bot/v1/messages/createPoll/ | POST | Message |
| GetPollResults | /bot/v1/polls/getResults/ | GET | PollResults |
| GetPollVoters | /bot/v1/polls/getVoters/ | GET | PollVoters |
| SelfUpdate | /bot/v1/self/update/ | POST | BotSelf |

## 4. Bot Client

```python
class Bot:
    def __init__(
        self,
        token: str,
        session: BaseSession | None = None,  # defaults to AiohttpSession
    ) -> None: ...

    # Execute any method
    async def __call__(self, method: YaBotMethod[T]) -> T: ...

    # Shortcuts for all API methods
    async def send_text(self, chat_id: str | None = None, login: str | None = None,
                        text: str, **kwargs) -> Message: ...
    async def edit_text(self, chat_id: str | None = None, login: str | None = None, 
                        message_id: int, text: str, **kwargs) -> Message: ...
    async def send_file(self, chat_id: str | None = None, login: str | None = None,
                        document: InputFile, **kwargs) -> Message: ...
    async def send_image(self, ...) -> Message: ...
    async def send_gallery(self, ...) -> Message: ...
    async def get_file(self, file_id: str) -> bytes: ...
    async def delete_message(self, chat_id: str, message_id: int) -> bool: ...
    async def create_chat(self, ...) -> Chat: ...
    async def update_members(self, ...) -> bool: ...
    async def get_user_link(self, login: str) -> UserLink: ...
    async def create_poll(self, ...) -> Message: ...
    async def get_poll_results(self, ...) -> PollResults: ...
    async def get_poll_voters(self, ...) -> PollVoters: ...
    async def set_webhook(self, url: str | None) -> BotSelf: ...
    async def get_updates(self, offset: int = 0, limit: int = 100) -> list[Update]: ...

    # Context manager
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, *args) -> None: ...  # closes session

    # Download helper
    async def download(self, file_id: str, destination: Path | BinaryIO | None = None) -> BytesIO | None: ...
```

### Session Layer

```python
class BaseSession(ABC):
    @abstractmethod
    async def make_request(self, token: str, method: YaBotMethod[T]) -> T: ...

    @abstractmethod
    async def stream_content(self, token: str, url: str) -> AsyncIterator[bytes]: ...

    @abstractmethod
    async def close(self) -> None: ...

class AiohttpSession(BaseSession):
    """aiohttp-based session with connection pooling, retry, timeout."""

    BASE_URL = "https://botapi.messenger.yandex.net"

    def __init__(
        self,
        timeout: float = 60.0,
        connector_limit: int = 100,
    ) -> None: ...
```

## 5. Dispatcher & Router

```python
class Router:
    def __init__(self, name: str | None = None) -> None:
        self.message = EventObserver()          # text, file, image, sticker, forward
        self.bot_request = EventObserver()      # server_action callbacks
        self.startup = LifecycleObserver()
        self.shutdown = LifecycleObserver()
        self._sub_routers: list[Router] = []
        self._middlewares = MiddlewareManager()

    def include_router(self, router: Router) -> None: ...

    # Decorator shortcuts
    def on_message(self, *filters) -> Callable: ...      # register message handler
    def on_bot_request(self, *filters) -> Callable: ...   # register bot_request handler

class Dispatcher(Router):
    def __init__(self, storage: BaseStorage | None = None) -> None: ...

    async def feed_update(self, bot: Bot, update: Update) -> None: ...
    async def start_polling(self, bot: Bot) -> None: ...
    def run_polling(self, bot: Bot) -> None: ...          # sync entry point
```

### Event Dispatching Flow

```
Update arrives (poll/webhook)
  → Dispatcher.feed_update(bot, update)
    → outer middleware chain
      → classify update (message? bot_request?)
        → Router tree depth-first search
          → for each router: check filters → run inner middleware → call handler
            → handler receives (event, **injected_deps)
```

## 6. Filter System

```python
class BaseFilter(ABC):
    @abstractmethod
    async def __call__(self, event: Message | BotRequest, **kwargs) -> bool | dict[str, Any]: ...

class CommandFilter(BaseFilter):
    """Match /command in text."""
    def __init__(self, *commands: str, ignore_case: bool = True): ...

class StateFilter(BaseFilter):
    """Match FSM state."""
    def __init__(self, *states: State): ...

class ServerActionFilter(BaseFilter):
    """Match bot_request server_action by name."""
    def __init__(self, *action_names: str): ...
```

### MagicFilter (F)

```python
F = MagicFilter()

# Usage:
F.text == "/start"
F.text.startswith("hello")
F.from_user.login == "admin@company.ru"
F.document  # truthy check — has document
F.chat.type == ChatType.GROUP
```

## 7. Middleware

```python
class BaseMiddleware(ABC):
    @abstractmethod
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any: ...

# Example:
class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        logger.info("Received: %s", event.text)
        result = await handler(event, data)
        logger.info("Handled")
        return result

# Registration:
router.message.middleware(LoggingMiddleware())     # inner (after filters)
router.message.outer_middleware(LoggingMiddleware()) # outer (before filters)
```

## 8. Dependency Injection (Variant A)

### Built-in dependencies (resolved by type automatically)

| Type | Source |
|---|---|
| `Bot` | Current bot instance |
| `Message` | Current message (first positional arg) |
| `BotRequest` | Current bot_request event |
| `Chat` | Extracted from event |
| `User` | Extracted from event.from |
| `FSMContext` | Current FSM context |

### Custom dependencies via `Annotated[T, Inject()]`

```python
from ya_bot.di import Inject
from typing import Annotated

# Define a factory
async def get_database() -> Database:
    return Database(url="...")

# Register globally
dp = Dispatcher()
dp.dependency(Database, factory=get_database)

# Or inline via Annotated
@router.on_message(F.text == "/users")
async def list_users(
    message: Message,                                    # built-in, auto
    bot: Bot,                                            # built-in, auto
    state: FSMContext,                                   # built-in, auto
    db: Annotated[Database, Inject(factory=get_database)], # inline factory
) -> None:
    users = await db.get_users()
    await bot.send_text(chat_id=message.chat.id, text=str(users))
```

### Startup validation

At `dp.start_polling()` / webhook start, the DI system inspects all registered handlers and verifies that every parameter can be resolved (by type for built-ins, by `Inject` for custom). If not — `DependencyResolutionError` at startup.

## 9. FSM

```python
class UserForm(StatesGroup):
    name = State()
    email = State()

@router.on_message(CommandFilter("start"))
async def start(message: Message, state: FSMContext) -> None:
    await state.set_state(UserForm.name)
    await bot.send_text(login=message.from_user.login, text="What's your name?")

@router.on_message(StateFilter(UserForm.name))
async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(UserForm.email)
    await bot.send_text(login=message.from_user.login, text="What's your email?")
```

### Storage

```python
class BaseStorage(ABC):
    @abstractmethod
    async def get_state(self, key: StorageKey) -> str | None: ...
    @abstractmethod
    async def set_state(self, key: StorageKey, state: str | None) -> None: ...
    @abstractmethod
    async def get_data(self, key: StorageKey) -> dict[str, Any]: ...
    @abstractmethod
    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None: ...
    @abstractmethod
    async def close(self) -> None: ...

@dataclass(frozen=True)
class StorageKey:
    bot_id: str
    chat_id: str
    user_id: str
```

## 10. Error Handling

```python
class YaBotError(Exception): ...

class APIError(YaBotError):
    """Base API error."""
    status_code: int
    description: str
    method: YaBotMethod

class BadRequest(APIError): ...           # 400
class Unauthorized(APIError): ...         # 401
class Forbidden(APIError): ...            # 403
class NotFound(APIError): ...             # 404
class Conflict(APIError): ...             # 409
class PayloadTooLarge(APIError): ...      # 413
class TooManyRequests(APIError):          # 429
    retry_after: float                    # from Retry-After header
class ServerError(APIError): ...          # 5xx

class NetworkError(YaBotError): ...       # connection/timeout errors
class ClientDecodeError(YaBotError): ...  # JSON parse error
```

### Auto-retry for 429

In `AiohttpSession.make_request()`:
- On 429: read `Retry-After`, sleep, retry (max 3 attempts)
- On 5xx: exponential backoff, retry (max 3 attempts)

## 11. Polling & Webhook

### Polling

```python
async def start_polling(self, bot: Bot) -> None:
    """Long-poll loop with backoff and jitter."""
    offset = 0
    backoff = Backoff(min_delay=0.5, max_delay=30.0, factor=2, jitter=0.5)

    while not self._stop:
        try:
            updates = await bot.get_updates(offset=offset, limit=100)
            backoff.reset()
            for update in updates:
                offset = update.update_id + 1
                asyncio.create_task(self._process_update(bot, update))
        except TooManyRequests as e:
            await asyncio.sleep(e.retry_after)
        except Exception:
            delay = backoff.next()
            await asyncio.sleep(delay)
```

### Webhook

```python
class WebhookHandler:
    """aiohttp request handler for webhook mode."""

    def __init__(self, dispatcher: Dispatcher, bot: Bot) -> None: ...

    async def handle(self, request: web.Request) -> web.Response:
        data = await request.json()
        update = Update.model_validate(data)
        await self.dispatcher.feed_update(self.bot, update)
        return web.Response(status=200)

    def setup(self, app: web.Application, path: str = "/webhook") -> None:
        app.router.add_post(path, self.handle)
```

## 12. Message Shortcuts (Context-Bound)

```python
# Message gets a _bot reference via context propagation
class Message(YaBotObject):
    ...

    async def answer(self, text: str, **kwargs) -> Message:
        """Reply to the chat this message came from."""
        return await self._bot.send_text(chat_id=self.chat.id, text=text, **kwargs)

    async def reply(self, text: str, **kwargs) -> Message:
        """Reply quoting this message."""
        return await self._bot.send_text(
            chat_id=self.chat.id, text=text,
            reply_message_id=self.message_id, **kwargs
        )

    async def delete(self) -> bool:
        return await self._bot.delete_message(
            chat_id=self.chat.id, message_id=self.message_id
        )
```

## 13. Public API (ya_bot/__init__.py)

```python
from ya_bot.client.bot import Bot
from ya_bot.dispatcher.dispatcher import Dispatcher
from ya_bot.dispatcher.router import Router
from ya_bot.filters.magic import F
from ya_bot.filters.command import CommandFilter
from ya_bot.filters.state import StateFilter
from ya_bot.filters.callback import ServerActionFilter
from ya_bot.fsm.state import State, StatesGroup
from ya_bot.fsm.context import FSMContext
from ya_bot.di.inject import Inject
from ya_bot.dispatcher.middlewares.base import BaseMiddleware
from ya_bot.types import *
```

## 14. Usage Example

```python
from ya_bot import Bot, Dispatcher, Router, F, CommandFilter, StateFilter
from ya_bot import State, StatesGroup, FSMContext, Message
from ya_bot.types import SuggestButtons, InlineButton

router = Router(name="main")

@router.on_message(CommandFilter("start"))
async def start(message: Message, bot: Bot) -> None:
    buttons = SuggestButtons(buttons=[
        [InlineButton(text="Help", directives=[
            {"type": "server_action", "name": "help", "payload": {}}
        ])]
    ])
    await message.answer("Welcome!", suggest_buttons=buttons)

@router.on_bot_request(F.server_action.name == "help")
async def help_action(request: BotRequest, bot: Bot) -> None:
    await bot.send_text(chat_id=request.chat.id, text="Here's help...")

class Form(StatesGroup):
    name = State()

@router.on_message(CommandFilter("form"))
async def form_start(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.name)
    await message.answer("Enter your name:")

@router.on_message(StateFilter(Form.name))
async def form_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.clear()
    await message.answer(f"Saved: {message.text}")

async def main():
    bot = Bot(token="your-oauth-token")
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```
