# Desktop Buddies — Pokes (Phase 3)

## Summary

Let friends nudge each other by **clicking a friend's sprite**. The poked
sprite plays a short hop on every room member's desktop — the poker sees it, the
poked sees their own sprite jump, and everyone else in the room sees it too.

This is Phase 3 from the v1 design spec
(`docs/superpowers/specs/2026-07-14-desktop-buddies-design.md`). It builds on the
relay + one-window-per-sprite architecture and changes no v1 or Phase 2
behavior.

Click gets one consistent meaning across the app: **your sprite, talk; their
sprite, poke.** Clicking your own sprite continues to open the chat composer
exactly as it does today.

## Goals

- Poke a specific friend by clicking their sprite.
- Play the reaction on **all** members' screens, including a local echo on the
  poker's own screen (the relay never echoes a sender's own message back).
- Reaction is a short vertical hop, using no new sprite art.
- A hop rides on top of walking rather than interrupting it.
- Throttle sends per target so a held mouse button cannot flood the room.
- Keep the relay dumb: it forwards pokes without inspecting them.
- Keep pure logic (hop easing, cooldown) separate from Qt so it unit tests
  headless, matching the v1 and Phase 2 convention.

## Non-Goals

- No poke history, counters, or notifications when you are away.
- No sound, haptics, or OS-level alerts.
- No poke-back prompt, streaks, or any reciprocation mechanic.
- No new sprite art, and no new animation state in `SpriteWindow`.
- No keyboard shortcut for poking (chat keeps the hotkey; poke is click-only).
- Spotify (Phase 4) remains out of scope.

## Design Decisions

Three choices shape everything below.

**The reaction is public.** Every member renders the hop, not just the target.
This matches the ambient, over-the-shoulder feel of chat bubbles — you can watch
two friends poke each other — and it means the relay needs no notion of
addressing. Clients receive every poke and independently decide to hop the sprite
named by `target_id`.

**The reaction is motion, not art.** Every character has exactly two frame
folders (`idle/`, `walk/`), and `SpriteWindow._frames` is a hardcoded dict of
those two. A render-time position offset avoids adding a third animation, a
temporary-animation state machine that unwinds back to idle/walk, and art for
every present and future character.

**The hop is vertical.** Walking owns the horizontal axis, and every sprite sits
pinned at `FLOOR_FRACTION = 0.9`, so the vertical axis is otherwise unused. A
vertical offset can never be mistaken for movement or fight the remote
interpolator.

## Wire Protocol

Add a single message type to the shared schema — the single source of truth for
both client and relay.

- **`shared/messages.py`**: add `POKE = "poke"`.
- **Message shape**:
  `{"type": "poke", "id": <poker sprite id>, "target_id": <poked sprite id>}`.
  `id` is the sender, consistent with `STATE` and `CHAT`.
- Built via `messages.encode(POKE, id=..., target_id=...)`; never hand-built.

### Relay change

`relay/server.py:38` currently forwards two message types:

```python
elif mtype in (m.STATE, m.CHAT) and member_id is not None:
    await registry.relay(code, member_id, raw)
```

Widen the same branch to include `POKE`:

```python
elif mtype in (m.STATE, m.CHAT, m.POKE) and member_id is not None:
    await registry.relay(code, member_id, raw)
```

`Registry.relay()` already fans a raw message out to every member except the
sender, so `relay/room.py` is untouched. The relay does not read `target_id` and
has no concept of a poke.

## Client Architecture

### Sending path

1. **Trigger**: `SpriteWindow.clicked` already fires on `mousePressEvent` for
   every sprite window, but `app.py` currently connects it only for the owned
   sprite. `_add_remote` gains a connection for each remote window, binding that
   member's id at connect time:

   ```python
   win.clicked.connect(lambda mid=mid: self._on_poke_clicked(mid))
   ```

   The default-argument capture is required — a bare closure over `mid` would
   read the loop variable's final value.

2. **Throttle**: `_on_poke_clicked` consults a `PokeCooldown` keyed by target id. If the
   target was poked within the cooldown window, the click is ignored entirely
   (no send, no local hop).

3. **Send and echo**: otherwise `AppController` calls
   `net.send_poke(own_id, target_id)` and immediately applies the hop locally via
   `world.poke(target_id)`. The local echo is necessary because the relay
   excludes the sender from the fan-out, exactly as with chat.

Self-poking is structurally impossible: the owned window's `clicked` is connected
to the chat composer, not to `_on_poke_clicked`.

### Receiving path

- `NetClient` gains `poke_received = Signal(dict)` and a `POKE` branch in
  `_dispatch` that emits the decoded message.
- `AppController._on_poke_received` calls `world.poke(msg["target_id"])`.
  The poked member's own client takes this same path, hopping its owned sprite.
- `World.poke` ignores ids it does not know, so a poke racing a `member_left`
  is dropped harmlessly.

### Hop bookkeeping and rendering

`World` gains `hops: dict[str, Hop]` alongside `remotes`:

- **`poke(target_id)`** — if the id names a known sprite (own or remote), create
  a `Hop` for it, or `reset()` the existing one so a second poke restarts the arc
  rather than stacking. Unknown ids are ignored.
- **`tick(dt)`** — advance every hop and drop the ones reporting `done`, in the
  same pass that already drives the controller and remote interpolation.
- **`hop_offset(id) -> float`** — the sprite's current offset, `0.0` when it has
  no active hop.

`AppController._tick` applies the offset when converting fractional coordinates
to pixels:

```python
py = int((sp.y - self.world.hop_offset(sp.id)) * (screen.height() - win.height()))
```

Subtracted because screen y grows downward, so hopping up is a smaller `py`.
Because this happens at render time on top of the interpolated position, a poked
sprite mid-walk keeps walking and hops simultaneously.

Bubble positioning already derives from `win.x()` / `win.y()`, so a chat bubble
above a hopping sprite follows it up and down with no extra work.

### Pure logic (headless-testable, no Qt)

Collected in `Src/poke.py`:

- **`Hop(height=0.04, duration=0.45)`** — *implemented and committed
  (`ac7b31a`)*. `advance(dt)` accumulates elapsed time; `offset()` returns
  `height * sin(pi * elapsed / duration)`, a symmetric arc that is `0.0` at both
  ends and peaks at `height` midway; `done` is true once `duration` elapses, at
  which point `offset()` clamps to `0.0` rather than letting sine go negative and
  sink the sprite through the floor; `reset()` restarts the arc.
- **`PokeCooldown(seconds=1.0)`** — `try_send(target_id, now) -> bool` returns
  True and records the send if this target has not been poked within `seconds`,
  otherwise False. Cooldowns are independent per target, so two friends can be
  poked back to back. `now` is passed in rather than read from a clock inside the
  class, so tests drive time without sleeping.

## Module Map (changed / new)

| File | Change |
|------|--------|
| `shared/messages.py` | Add `POKE` constant. |
| `relay/server.py` | Forward `POKE` alongside `STATE` / `CHAT` in the existing branch. |
| `Src/poke.py` | `Hop` *(done)*; add pure `PokeCooldown`. |
| `Src/Connections.py` | Add `send_poke(id, target_id)`, `poke_received` signal, `POKE` dispatch. |
| `Src/world.py` | Add `hops`, `poke()`, `hop_offset()`; advance/expire hops in `tick()`. |
| `Src/app.py` | Connect remote `clicked` → `_on_poke_clicked` → cooldown → send + local echo; `poke_received` → hop; apply offset in `_tick`; drop hops on leave/disconnect. |

No new dependencies.

## Error Handling & Edge Cases

- **Poke for an unknown sprite id** (racing `member_left`): `World.poke` ignores
  it. Same rule chat already uses for bubbles.
- **Rapid clicks on one target**: suppressed by `PokeCooldown`; the click does
  nothing at all, so the poker never sees a hop the room did not receive.
- **Incoming pokes faster than the cooldown** (several friends poking one
  target): each resets the target's hop. Receiving is never throttled — only
  sending is.
- **Poked sprite leaves**: `_on_member_left` drops the hop alongside the sprite
  window and bubble.
- **Disconnect**: `_on_disconnected` clears `hops` with the rest of the world
  state.
- **Malformed poke**: `messages.decode` already returns `None` for non-JSON or
  typeless payloads; `_dispatch` ignores it. A well-formed JSON poke missing
  `target_id` would raise `KeyError` in the receiving slot — the same exposure
  `_on_chat` already has with `msg["text"]`. Both clients are built from the same
  `shared/messages.py`, so this is a protocol violation rather than a path worth
  defending; if it ever needs hardening, chat and poke should be hardened
  together.
- **Click on a remote sprite before the world exists**: remote windows only exist
  after `_begin_world`, so this cannot occur.

## Testing

**Headless unit tests (no display):**

- `Hop` — *done (9 tests in `tests/test_poke.py`)*: ground at both ends, peak at
  height midway, symmetric arc, clamped to `0.0` past `duration`, `offset()`
  leaves configuration unmutated, `advance()` accumulates, `reset()` restarts,
  default height is a plausible screen fraction.
- `PokeCooldown`: first send allowed; an immediate repeat denied; allowed again
  once `seconds` elapse; separate targets do not interfere.
- `World.poke`: creates a hop for a known remote id and for the owned id; ignores
  an unknown id; a second poke resets rather than stacking; `tick` expires the
  hop after `duration`; `hop_offset` returns `0.0` for a sprite with no hop.
- `POKE` `encode`/`decode` round-trip preserves `id` and `target_id`.
- Relay forwards a `POKE` to other room members but not back to the sender
  (extend the existing relay/server tests).

**Manual integration:**

Start the relay and launch two clients in a shared room. Click the other
person's sprite and confirm it hops on **both** desktops. Click it repeatedly and
confirm the cooldown holds it to roughly one hop per second. Poke a sprite while
it is walking and confirm it keeps walking through the hop.

## Open Considerations (not blocking)

- Hop height and duration start at 0.04 / 0.45s and can be tuned by feel once
  it is running on two real desktops.
- The cooldown is fixed at 1.0s and not user-configurable, matching the fixed
  hotkey decision in Phase 2.
- A poke currently carries the sender's `id` but nothing renders it. Attribution
  (a brief name tag, or hopping toward the poker) is a natural follow-up that
  needs no wire change.
