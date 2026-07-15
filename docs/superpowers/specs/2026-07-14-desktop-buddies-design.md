# Desktop Buddies — v1 Design

**Date:** 2026-07-14
**Status:** Approved for planning

## Summary

Desktop Buddies lets friends appear as animated desktop pets on each other's
computers. Each person runs a small always-on-top sprite that idles and walks
around their own screen. By joining a shared room (via a code), everyone sees
each other's sprites moving on their own desktop in real time.

This spec covers **v1** only: an animated sprite plus multiplayer presence.
Chat bubbles, pokes, and Spotify integration are deferred to later phases, each
of which will get its own spec.

## Goals (v1)

- A transparent, frameless, always-on-top sprite that idles and walks around the
  user's desktop, cross-platform on macOS and Windows.
- A launch menu: enter a display name, pick a placeholder character, then either
  create a room (receive a shareable code) or join a room (paste a code).
- Real-time multiplayer presence: sprites of everyone in the room appear and move
  on each member's screen, driven over the network through a relay server.
- A "dumb" relay server the developer hosts in the cloud, so clients on different
  home networks can connect without port-forwarding or NAT traversal.

## Non-goals (v1)

- Chat, pokes, and Spotify (later phases — see Phasing).
- Sprites perching on / tracking individual application windows. v1 sprites float
  on the desktop only.
- Persistence, accounts, authentication, or anti-cheat. Rooms are ephemeral and
  in-memory; this is for trusted friend groups.
- Custom/final art. v1 ships simple placeholder characters.

## Key decisions

These were settled during brainstorming and drive the rest of the design:

1. **Language/stack:** Python. Desktop client uses **PySide6** (Qt) for frameless
   translucent always-on-top windows, animation timers, and cross-platform
   packaging.
2. **Sprite placement:** sprites **float on the desktop** (walk along the screen);
   they do not detect or track other application windows.
3. **Overlay model — one tiny window per sprite.** Each sprite is its own small,
   frameless, transparent, always-on-top window positioned where the sprite is.
   The desktop *between* sprites is never covered, so there is **no click-through
   problem** — mouse clicks only ever land on an actual sprite window. Walking =
   moving the window. This deliberately avoids the hardest cross-platform issue
   (per-pixel click-through on a fullscreen overlay).
4. **Networking — developer-hosted relay.** One always-on relay server in the
   cloud. Clients connect *outward* to it (no inbound ports needed), so friends on
   different networks work without NAT traversal. A **room code** groups friends.
5. **Relay is "dumb."** It manages rooms and fans out messages; it knows nothing
   about sprites. All game logic lives in the clients.
6. **Peer clients, no authoritative host.** Each client is authoritative over its
   own sprite only. The room creator "owns" the room socially but runs no special
   netcode. (Reconciles the original "one user hosts a server" idea: the relay is
   the server; the room creator is the host.)

## Architecture

Three deployable pieces:

### 1. Relay server (`relay/`)

A standalone Python process, run in the cloud by the developer. Async WebSocket
server (`websockets` library).

Responsibilities:
- Accept client WebSocket connections.
- Handle `create_room` → generate a short unique code, create an in-memory room,
  add the connection as its first member.
- Handle `join_room {code}` → add the connection to the room, or reply `error` if
  the code is unknown.
- For every subsequent message from a client, **fan it out verbatim** to all
  *other* members of the same room.
- On disconnect, remove the member and notify the room (`member_left`). Delete the
  room when it becomes empty.

Rooms are in-memory dicts keyed by code — no database. Intentionally minimal so it
is cheap to host and hard to break.

### 2. Desktop client (`Src/`)

The PySide6 application each person runs. Internal modules:

- **`menu`** (backed by `Menu/`) — the launch window: name field, character
  picker, Create/Join actions, and display of the room code after creating.
- **`net`** (`Connections.py`) — a WebSocket client on a background thread. It
  translates between the relay's JSON messages and Qt signals so the UI thread is
  never blocked by the network.
- **`sprite`** — the `SpriteWindow` (one frameless/transparent/always-on-top
  window per character on screen) plus the frame animator.
- **`world`** — the local model of the room: the set of members, each sprite's
  position/facing/animation. Owns *your* sprite's idle/walk behavior and holds
  *remote* sprites as puppets driven by incoming network updates.
- **`app`** — composition root wiring menu, net, world, and sprite windows
  together.
- **`User.py`** — the local player's identity (name, chosen character) and its
  own-sprite behavior/state.
- **`Host.py`** — client-side room-creation ("I made this room") role.

### 3. Shared (`shared/`)

Message type constants and the encode/decode schema, imported by both the client
and the relay so their wire formats cannot drift.

## Networking protocol

WebSocket transport carrying JSON messages, in two layers.

### Room control (client ↔ relay)

- `create_room {name, character}` → relay replies `room_created {code, your_id}`
- `join_room {code, name, character}` → relay replies `room_joined {your_id,
  members: [{id, name, character}, ...]}` or `error {reason}` (unknown/expired
  code)
- relay pushes `member_joined {id, name, character}` when someone joins
- relay pushes `member_left {id}` when someone disconnects

### State sync (client → relay → other clients, forwarded verbatim)

- `state {id, x, y, facing, anim}` — one sprite's position, facing direction, and
  current animation.

Rules:
- Each client sends **only its own** `state`, a few times per second, and only
  when something changed.
- **Positions are fractions of screen size (0.0–1.0)**, not pixels, so members on
  differently sized monitors all see sprites in sensible relative locations.
- Remote sprite motion is **interpolated** between received updates so it looks
  smooth despite a low send rate.
- No reliability layer: a dropped `state` packet just yields a slightly stale
  position that the next update corrects.

## Data flow (walk-through)

1. You launch the app → menu → enter "Kain", pick the cat, click **Create**.
2. Client connects to the relay, receives code `PLUM-42`; the menu displays it;
   your cat window appears on your desktop and begins its idle/walk loop.
3. A friend launches their app, picks the dog, and **Joins** with `PLUM-42`.
4. Relay adds them: it sends you `member_joined` (a dog puppet window appears on
   *your* screen) and sends them `room_joined` listing existing members (your cat
   appears on *their* screen).
5. Thereafter each client streams its own `state`; the relay fans it out; each
   side moves the other's puppet window smoothly via interpolation.
6. When someone closes the app, the relay sends `member_left` and that puppet
   window disappears.

## Sprite format & animation

Folder-per-character, folder-per-animation, numbered frames:

```
Sprites/
  placeholder_cat/
    sprite.json          # frame rate, default scale
    idle/  0.png 1.png ...
    walk/  0.png 1.png ...
  placeholder_dog/
    ...
```

- The animator cycles the frames of the current animation on a Qt timer.
- `walk` frames are flipped horizontally to face left vs. right.
- v1 ships 2–3 simple placeholder characters (a few frames each) so the whole
  system is testable. Replacing art is just dropping new files into these folders.

## Own-sprite behavior (idle/walk AI)

The local client drives its own sprite with a small state machine: idle for a
random interval, then pick a random destination along the screen, switch to
`walk`, move toward it (updating `facing`), then return to idle. This produces the
ambient "wandering pet" feel and generates the `state` updates that friends see.

## Error handling

- **Unknown/expired room code:** relay replies `error {reason}`; menu shows a
  friendly message and lets the user retry.
- **Relay unreachable / connection drops:** client surfaces a "disconnected"
  state; puppets freeze/clear; user can return to the menu to reconnect. (Auto-
  reconnect is a nice-to-have, not required for v1.)
- **Malformed message:** receiver ignores it rather than crashing; the shared
  schema is the single source of truth for valid shapes.
- **Empty room:** relay deletes the room once the last member leaves, freeing the
  code.

## Testing approach

- **Relay:** unit-test room create/join/leave and message fan-out using fake
  in-memory WebSocket clients. Pure logic, no GUI.
- **Shared schema:** round-trip encode/decode tests so client and relay stay in
  sync.
- **Client logic** (`world` model, interpolation, own-sprite AI): tested headless,
  kept separate from Qt rendering so tests run without a display.
- **Manual integration:** run the relay locally and launch two client instances on
  one machine over loopback to watch two sprites interact before any cloud deploy.

## Phasing (later — each its own spec)

- **Phase 2 — Chat bubbles:** a hotkey opens an input box; `chat {id, text}`
  message; a bubble widget renders above the sprite window and fades out.
- **Phase 3 — Pokes:** click a friend's sprite → `poke {target_id}` → the target's
  sprite plays a small reaction gesture.
- **Phase 4 — Spotify:** each user authorizes their own Spotify developer app via
  OAuth; the client polls "now playing"; `music {id, track, artist}` renders a
  small now-playing tag above the sprite.

## Open considerations (not blocking v1)

- Multi-monitor: v1 targets the primary screen; fractional coordinates keep the
  door open for later multi-monitor handling.
- Relay hosting/deployment specifics (host, process manager, TLS) are an
  operational task tracked alongside Phase-1 implementation, not part of the
  client design.
