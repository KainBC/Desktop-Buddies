# Desktop Buddies — Chat Bubbles (Phase 2)

## Summary

Let friends send short text messages that appear as speech bubbles above their
sprite on every room member's desktop. A user opens a small input box by
**clicking their own sprite** or pressing a **global hotkey**, types a line, and
presses Enter. The message is relayed to peers and rendered as a rounded bubble
that floats above the sender's sprite for a few seconds and then fades out.

This is Phase 2 from the v1 design spec
(`docs/superpowers/specs/2026-07-14-desktop-buddies-design.md`). It builds on the
existing relay + one-window-per-sprite client architecture and changes none of
the v1 behavior.

## Goals

- Send a short text message tied to the sender's sprite id.
- Two ways to open the composer: click your own sprite, or a global hotkey.
- Render the message as a bubble above the sender's sprite on **all** members'
  screens, including a local echo above your own sprite.
- Bubble displays for ~5s, then fades out over ~0.5s. A newer message replaces
  the current one and resets the timer.
- Keep the relay dumb: it forwards chat messages without inspecting them.
- Keep pure logic (text sanitizing, bubble lifetime) separate from Qt so it is
  unit-testable headless, matching the v1 convention.

## Non-Goals

- No message history, persistence, or scrollback — bubbles are ephemeral.
- No delivery receipts, typing indicators, or read state.
- No moderation/filtering beyond length capping and whitespace trimming.
- No rich text, emoji pickers, images, or links — plain text only.
- Pokes (Phase 3) and Spotify (Phase 4) remain out of scope.

## Wire Protocol

Add a single message type to the shared schema — the single source of truth for
both client and relay.

- **`shared/messages.py`**: add `CHAT = "chat"`.
- **Message shape**: `{"type": "chat", "id": <sender sprite id>, "text": <str>}`.
  `id` is the sender's sprite id, consistent with the `STATE` message.
- Built via `messages.encode(CHAT, id=..., text=...)`; never hand-built.

### Relay change

`relay/server.py`'s connection handler currently relays only `STATE` messages:

```python
elif mtype == m.STATE and member_id is not None:
    await registry.relay(code, member_id, raw)
```

Widen this single branch to forward `CHAT` as well:

```python
elif mtype in (m.STATE, m.CHAT) and member_id is not None:
    await registry.relay(code, member_id, raw)
```

`Registry.relay()` already fans a raw message out to every member of the room
except the sender, so no change is needed in `relay/room.py`. The relay does not
parse or validate `text`.

## Client Architecture

### Sending path

1. **Trigger** (either opens the same composer, targeting the user's own sprite):
   - **Click own sprite**: `SpriteWindow.clicked` (already emitted on
     `mousePressEvent`) fires; `AppController` opens the composer for the owned
     sprite id. Clicks on remote sprites do nothing in Phase 2 (reserved for
     pokes).
   - **Global hotkey**: default **Cmd+Shift+B** (macOS) / **Ctrl+Shift+B**
     (other platforms), registered by a background `pynput` listener. On press it
     signals the Qt thread to open the composer.

2. **Composer** (`ChatInputWindow`): a small frameless, focusable window placed
   next to the sprite. It contains a single-line text field. Enter submits;
   Escape / focus-out cancels and closes. It emits `submitted(text)`.

3. **Submit**: `AppController` runs the text through `sanitize_chat()`. If the
   result is non-empty it:
   - calls `net.send_chat(own_id, text)` to relay to peers, and
   - shows a bubble above the user's own sprite immediately (local echo), so the
     sender sees what they said without a round-trip.

### Receiving path

- `NetClient` gains a `chat_received = Signal(dict)` signal and a dispatch branch
  for `CHAT` that emits the decoded message.
- `AppController._on_chat` looks up the sprite id in `self.windows` and shows /
  replaces a bubble for that sprite. Messages for unknown ids are ignored.

### Bubble rendering & positioning

- `BubbleWindow` (Qt): frameless, translucent, always-on-top, using the same
  window flags as `SpriteWindow` **including** `WA_MacAlwaysShowToolWindow` so
  bubbles stay visible when the app is not frontmost (the macOS fix already
  applied to sprites). It paints wrapped text inside a rounded speech-bubble
  background with a max width; height grows with wrapped lines.
- Bubbles are tracked by sprite id (at most one per sprite). Showing a new
  message on a sprite that already has a bubble replaces the text and resets the
  lifetime.
- In the existing `AppController._tick` loop, after sprite windows are
  positioned, each active bubble is:
  - advanced by `dt` and its window opacity set from `BubbleLifetime`,
  - positioned centered horizontally over its sprite window, just above the
    sprite's top edge, clamped to stay on-screen, and
  - closed and removed once `BubbleLifetime` reports it is done.
- On `member_left` / disconnect, a departing sprite's bubble is closed alongside
  its sprite window.

### Pure logic (headless-testable, no Qt)

Collected in a new `Src/chat.py`:

- **`sanitize_chat(text: str, max_len: int = 140) -> str`**: strips leading /
  trailing whitespace, collapses internal runs of whitespace to single spaces,
  truncates to `max_len` characters. Returns `""` for empty / whitespace-only
  input; the caller treats `""` as "nothing to send."
- **`BubbleLifetime(hold: float = 5.0, fade: float = 0.5)`**: tracks elapsed time
  via `advance(dt)`. Exposes `opacity()` (1.0 during hold, linearly decreasing to
  0.0 across the fade window) and `done` (True once `hold + fade` elapsed).
  `reset()` restarts it when a new message replaces the current bubble.

## Module Map (changed / new)

| File | Change |
|------|--------|
| `shared/messages.py` | Add `CHAT` constant. |
| `relay/server.py` | Forward `CHAT` alongside `STATE` in the handler branch. |
| `Src/Connections.py` | Add `send_chat(id, text)`, `chat_received` signal, `CHAT` dispatch. |
| `Src/chat.py` *(new)* | Pure `sanitize_chat()` + `BubbleLifetime` (no Qt). |
| `Src/bubble.py` *(new)* | `BubbleWindow`: Qt bubble rendering + opacity/fade. |
| `Src/chat_input.py` *(new)* | `ChatInputWindow`: focusable composer, emits `submitted(text)`. |
| `Src/hotkey.py` *(new)* | `GlobalHotkey`: pynput wrapper, graceful failure, Qt signal on press. |
| `Src/app.py` | Wire triggers → composer → send + echo; `chat_received` → bubble; position/tick/expire bubbles. |
| `requirements.txt` | Add `pynput`. |

## Error Handling & Edge Cases

- **Global hotkey unavailable** (macOS Accessibility denied, unsupported
  platform, or `pynput` import failure): `GlobalHotkey` catches the failure, logs
  a single warning, and does nothing further. Click-to-chat is unaffected and the
  app runs normally.
- **Empty / whitespace-only input**: `sanitize_chat` returns `""`; nothing is
  sent and no bubble is shown.
- **Over-long input**: truncated to `max_len` before sending.
- **Chat for an unknown sprite id** (e.g. a race with `member_left`): ignored.
- **Rapid messages**: each new message replaces the previous bubble for that
  sprite and resets its timer (no queue).
- **Malformed chat message**: `messages.decode` already returns `None` for
  non-JSON / typeless payloads; the dispatcher ignores it.

## Testing

**Headless unit tests (no display):**
- `sanitize_chat`: trims, collapses internal whitespace, caps at `max_len`,
  returns `""` for empty / whitespace-only input.
- `BubbleLifetime`: `opacity()` is 1.0 during hold, decreases through the fade
  window, reaches 0.0 and `done` becomes True after `hold + fade`; `reset()`
  restarts the clock.
- `CHAT` message `encode`/`decode` round-trip preserves `id` and `text`.
- Relay forwards a `CHAT` message to other room members but not back to the
  sender (extend the existing relay/server tests).

**Manual integration:**
- Start the relay; launch two clients in a shared room. Click your sprite (or
  press the hotkey), type a message, press Enter. Confirm a bubble appears above
  the sender's sprite on **both** desktops and fades after ~5s. Send a second
  message before the first fades and confirm it replaces the bubble.

## Open Considerations (not blocking)

- Bubble styling (colors, font, tail shape) starts minimal and legible; visual
  polish can follow.
- Hotkey is not user-configurable in Phase 2; a fixed default keeps scope small.
- Multi-monitor bubble clamping follows the same primary-screen assumption as v1.
