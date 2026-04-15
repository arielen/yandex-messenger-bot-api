# Yandex Messenger Bot API — Documented Inconsistencies and Undocumented Features

**Purpose:** This document records every known discrepancy between the official Yandex Messenger Bot API data-types reference and the actual behaviour observed in API response examples. It serves as the authoritative decision log for how this SDK handles each case.

**Sources verified on 2026-04-15:**

- Data types reference: https://yandex.ru/dev/messenger/doc/ru/data-types
- Update type anchor: https://yandex.ru/dev/messenger/doc/ru/data-types#update
- Polling endpoint + response examples: https://yandex.ru/dev/messenger/doc/ru/api-requests/update-polling
- Webhook endpoint: https://yandex.ru/dev/messenger/doc/ru/api-requests/update-webhook

---

## Inconsistencies Table

| # | Field / Feature | Documentation (data-types page) | Reality (API response examples / observed behaviour) | Source URL | SDK Decision |
|---|---|---|---|---|---|
| 1 | **`images` field type in `Update`** | Declared as `Image[]` — a flat array of `Image` objects. | Polling response examples show `Image[][]` — an outer array where each element is itself an array of size variants of a single image. One image → one inner array containing small/middle/middle-400/original variants. A gallery → multiple inner arrays, one per image. | https://yandex.ru/dev/messenger/doc/ru/api-requests/update-polling | SDK models `images` as `list[list[Image]]`. The outer index is the image number; the inner index is the size variant. The flat `Image[]` declaration in the docs is wrong. |
| 2 | **`forwarded_messages` in `Update`** | Not listed in the `Update` type table. No mention anywhere on the data-types page. | Appears in the polling "Прием пересланного сообщения" example as an array of message-like objects, each with `message_id`, `timestamp`, `chat`, `from`, and `text`. | https://yandex.ru/dev/messenger/doc/ru/api-requests/update-polling | SDK defines a `ForwardedMessage` type (subset of `Update` fields, all optional) and maps it to `Update.forwarded_messages: list[ForwardedMessage] \| None`. |
| 3 | **`sticker` in `Update`** | Not listed in the `Update` type table. No `Sticker` type definition exists anywhere on the data-types page. | Appears in the polling "Прием стикера" example as `{"id": "stickers/images/43/630.png", "set_id": "43"}`. Only `id` and `set_id` are shown. | https://yandex.ru/dev/messenger/doc/ru/api-requests/update-polling | SDK defines a `Sticker` type with `id: str`, `set_id: str \| None`, and `emoji: str \| None` (emoji is speculative — not in any example, added for completeness but marked optional). Mapped to `Update.sticker: Sticker \| None`. |
| 4 | **`thread_id` in `Update`** | Not listed in the `Update` type table. Not mentioned on the data-types page at all. | Present as a request parameter in `sendText`, `sendFile`, `sendImage`, `sendGallery` method docs, implying threads exist and messages can belong to them. No polling response example shows it arriving in an inbound update. | https://yandex.ru/dev/messenger/doc/ru/api-requests/update-polling (absent); method pages (present as send param) | SDK adds `thread_id: int \| None = None` to `Update` defensively. If the API ever sends it in an inbound update, it will deserialise correctly. All send-methods also expose `thread_id`. |
| 5 | **`image` (singular) in `Update`** | Not listed in the `Update` type table. The only image-related field listed is `images: Image[]`. | No polling response example ever shows a singular `image` field. Images always arrive inside the `images` array (even a single image comes as `[[...variants...]]`). | https://yandex.ru/dev/messenger/doc/ru/api-requests/update-polling | SDK includes `image: Image \| None = None` on `Update` as a defensive fallback field (some older API versions or edge cases may send it), but `images` is the canonical field. In practice `image` is expected to always be `None`. |
| 6 | **`Chat.id` — required in practice, optional in docs** | Marked as **optional** ("Нет"). The docs explain: *"У чата с типом private нет значимого идентификатора"* — private chats have no meaningful `id`. | Every group and channel example includes `"id": "0/0/<guid>"` or `"id": "1/0/<guid>"`. Private chat examples omit it entirely, consistent with the docs. So the docs are accurate for `private`, but the optional marker is misleading — for `group`/`channel` it is always present. | https://yandex.ru/dev/messenger/doc/ru/api-requests/update-polling | SDK models `Chat.id` as `str \| None = None`. The type is correct. Consumers should check `chat.type` before assuming `id` is populated. |
| 7 | **`from` (Sender) — required in `Update`, may be absent for channels** | Listed as **required** ("Да") in the `Update` type table. | The polling "Прием сообщения в канал" example shows `"from": {"id": "<guid>"}` — only an `id`, no `login`. The `Sender` docs clarify that for channels the `id` field (channel admin id) is used instead of `login`. In true anonymous channel posts the `from` object may have neither `login` nor a meaningful `id`. | https://yandex.ru/dev/messenger/doc/ru/data-types | SDK maps `Update.from_user` as `User \| None = None` (using `alias="from"`). Both `User.id` and `User.login` are optional. The "required" designation in the docs is misleading — `from` object may be minimal or absent in channel contexts. |
| 8 | **`File` type naming vs `Document` in SDK** | The data-types page defines a type called **`File`** with fields `id`, `name`, `size` (all required). The `Update` table calls the field **`file`** typed as `File`. | Polling "Прием файла" example shows `"file": {"id": "disk/<guid>", "name": "data.txt", "size": 20}` — matches the `File` type definition exactly. However the data-types `File.name` and `File.size` are marked required ("Да"), while in the SDK they are optional. | https://yandex.ru/dev/messenger/doc/ru/data-types ; https://yandex.ru/dev/messenger/doc/ru/api-requests/update-polling | SDK uses the internal class name `Document` (avoiding collision with Python's built-in concepts) but keeps the wire field name `file`. `Document.name` and `Document.size` are `\| None` as a defensive measure even though the docs say required. The `Update` also has a `document` alias field pointing to the same `Document` type for ergonomics. |
| 9 | **`Chat` extra fields — `title`, `organization_id`, `description`, `is_channel`** | Only two fields are documented for `Chat`: `type` (required) and `id` (optional). No other fields mentioned. | No polling response examples show extra fields on `Chat`. However the Yandex 360 Messenger web client and other integrations are known to return `title` for group chats and `organization_id` for org-scoped chats. No official doc exists for these. | https://yandex.ru/dev/messenger/doc/ru/data-types | SDK models `Chat` with `organization_id: str \| None`, `title: str \| None`, `description: str \| None`, and `is_channel: bool = False` as undocumented defensive fields. Pydantic's `extra = "allow"` is not used; unknown fields are silently ignored. |
| 10 | **`Sticker` type — no definition, `emoji` field undocumented** | No `Sticker` type is defined anywhere on the data-types page. There is no field list, no mention of `emoji`. | Polling example only shows `id` and `set_id`. The `id` value appears to be a file path (`stickers/images/43/630.png`). Whether `emoji` is ever sent by the API is unknown. | https://yandex.ru/dev/messenger/doc/ru/api-requests/update-polling | SDK defines `Sticker` with `id: str` (required), `set_id: str \| None`, `emoji: str \| None`. The `emoji` field is speculative — it is a natural property of stickers in any messenger protocol, but it has zero documentation basis. May be removed in a future version. |
| 11 | **`BotRequestError.type` — required** | Marked as **required** ("Да") with three allowed values: `unsupported_directive`, `invalid_directive_payload`, `client_error`. | No contradicting evidence in response examples. The field is only present in error scenarios (inside `bot_request.errors[]`). | https://yandex.ru/dev/messenger/doc/ru/data-types | SDK models `BotRequestError.type` as `str` (required, no default). The constraint to three values is documented but not enforced at the type level — the SDK accepts any string to avoid breaking on future error codes. |
| 12 | **`InlineSuggestButton.id` — documented as optional** | Listed as **optional** ("Нет"), max 255 characters. Used to identify which button was pressed in a `server_action` callback. | The `bot_request.element_id` in an inbound `Update` corresponds to this `id`. There is no example showing a full round-trip, but the mechanism is described in the `SetElementsStateDirective` docs. | https://yandex.ru/dev/messenger/doc/ru/data-types | SDK models `InlineSuggestButton.id` as `str \| None = None`. The `BotRequest.element_id` field on incoming updates receives the value of whichever button was pressed. |
| 13 | **`from` field in `Update` — both `id` and `login` present simultaneously** | `Sender` docs say only one of `login` or `id` will be present per response, depending on chat type. | Private/group polling examples show `from` with **both** `id` and `login` present: `{"id": "<guid>", "login": "ivan_ivanov", "display_name": "...", "robot": false}`. The channel example shows only `id`. The "one or the other" rule only strictly applies to channel messages. | https://yandex.ru/dev/messenger/doc/ru/api-requests/update-polling | SDK makes both `User.id` and `User.login` optional (`str \| None`). For channel messages only `id` arrives; for private/group messages both fields arrive. The docs' "either/or" framing is misleading about private/group behaviour. |
| 14 | **`images` vs gallery — single image still uses `Image[][]`** | The data-types page says `images: Image[]`. No distinction is drawn between a single image and a gallery. | A single image arrives as `[[ small, middle, middle-400, original ]]` — one outer element. A gallery of two images arrives as `[[ variants... ], [ variants... ]]`. There is no separate `image` (singular) field used for single images in any example. | https://yandex.ru/dev/messenger/doc/ru/api-requests/update-polling | SDK treats `images[0]` as the first image's size variants list regardless of gallery vs single. Helper property `Update.first_image` returns `images[0][-1]` (last = largest/original) as a convenience. `image` (singular) field is kept as a defensive fallback only. |

---

## Summary of Missing Type Definitions

The following types are used in API responses but have **no definition** on the data-types page:

| Type | Used in | Fields seen in examples | Notes |
|---|---|---|---|
| `Sticker` | `Update.sticker` | `id`, `set_id` | Completely absent from docs |
| `ForwardedMessage` | `Update.forwarded_messages[]` | `message_id`, `timestamp`, `chat`, `from`, `text` | Effectively a subset of `Update`; not named or defined |

---

## Summary of Undocumented `Update` Fields

Fields present in polling response examples that are **not listed** in the `Update` type table:

| Field | Type (inferred) | Appears in example |
|---|---|---|
| `forwarded_messages` | array of message-like objects | "Прием пересланного сообщения" |
| `sticker` | object with `id`, `set_id` | "Прием стикера" |

Fields **not in any example** but present in send-method parameters (implying round-trip existence):

| Field | Evidence |
|---|---|
| `thread_id` | Parameter in `sendText`, `sendFile`, `sendImage`, `sendGallery` |
