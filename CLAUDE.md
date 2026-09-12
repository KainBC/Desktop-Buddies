# Desktop Buddies

Friends appear as animated desktop pets on each other's computers. Each person
runs a transparent, always-on-top sprite that idles and walks around their own
screen. Joining a shared room (by code) makes everyone's sprites visible and
moving on each member's desktop in real time.

## Status

Building **v1**: animated sprite (idle/walk) + multiplayer presence via a
developer-hosted relay. Chat bubbles, pokes, and Spotify are deferred phases.

- Design spec: `docs/superpowers/specs/2026-07-14-desktop-buddies-design.md`
- Implementation plan: `docs/superpowers/plans/2026-07-14-desktop-buddies-v1.md`

## Architecture

Three pieces:

- **`relay/`** — a standalone async WebSocket server (run in the cloud). It is
  deliberately "dumb": it manages in-memory rooms keyed by a short code and fans
  out every message to the other members of a room. It knows nothing about
  sprites. All game logic lives in the clients.
- **`Src/`** — the PySide6 desktop client each person runs. It renders **one
  frameless, translucent, always-on-top window per sprite** (no fullscreen
  overlay, so there is no click-through problem), drives its own sprite's
  idle/walk AI, and puppets remote sprites from network updates.
- **`shared/`** — the JSON message schema imported by both client and relay so
  their wire formats cannot drift.
- **`desktop-buddies/`** — the marketing site (Next 16 / React 19 / Tailwind
  4). A separate deliverable from the desktop client: it shares the sprite
  art and copies the client's animation feel, but imports no Python, talks
  to no relay, and has no build-time dependency on the rest of the repo.
  Its animation logic lives in a pure, React-free `lib/buddy.ts` ported from
  `Src/world.py` and `Src/poke.py`; its sprite frames are copies of the
  placeholder art in `Sprites/`, refreshed whenever that art changes.

Each client is authoritative over **its own** sprite only and streams its state;
the relay forwards it; peers interpolate. There is no authoritative host — the
room creator just "owns" the room socially.

## Key module map

| File | Responsibility |
|------|----------------|
| `shared/messages.py` | Message type constants + `encode()`/`decode()`. **Single source of truth** — never hand-build JSON. |
| `relay/room.py` | `Registry`: room create/join/leave/relay (pure async logic). |
| `relay/server.py` | WebSocket wiring + connection lifecycle. |
| `Src/world.py` | `Sprite`, `OwnController` (idle/walk AI), `World` (remote interpolation). |
| `Src/User.py` | `PlayerIdentity` (name + character). |
| `Src/sprite_window.py` | `FrameCycler` (pure) + `SpriteWindow` (Qt) + frame loader. |
| `Src/menu.py` | Launch menu (name, character pick, create/join) + validators. |
| `Src/Connections.py` | `NetClient`: async websocket client on a bg thread → Qt signals. |
| `Src/Host.py` | Tracks the owned/joined room code + assigned id. |
| `Src/app.py` | `AppController`: wires menu, net, world, and sprite windows. |
| `desktop-buddies/lib/buddy.ts` | `FrameCycler`, `Hop`, `Stage` — the site's pure simulation. No React, no DOM. |
| `desktop-buddies/lib/characters.ts` | Which characters the site ships, their frame counts, and who wanders in the hero. |
| `desktop-buddies/lib/os.ts` | userAgent → platform, for the OS-labelled download button. |
| `desktop-buddies/lib/downloads.ts` | `BUILDS` — the one place a real installer URL gets filled in. |
| `desktop-buddies/components/BuddyStage.tsx` | The rAF loop: renders and pokes the hero's buddies. |

## Conventions

- **Python 3.11+**, **PySide6** (not PyQt), `websockets` for transport.
- Sprite coordinates on the wire and in the world model are **fractional floats
  `0.0`–`1.0`** (fraction of screen), never pixels. Pixels only at render time.
- `facing` is `1` (right) or `-1` (left).
- Client-side logic is kept **separate from Qt rendering** so it can be unit
  tested headless (`world`, `FrameCycler`, menu validators).
- TDD with frequent commits; existing scaffold filenames (`Connections.py`,
  `User.py`, `Host.py`) are kept capitalized, new modules are lowercase.

## Commands

```bash
python -m pip install -r requirements.txt   # install deps
python -m pytest -v                          # run the test suite
python -m relay                              # start the relay (ws://0.0.0.0:8765)
BUDDIES_URL=ws://localhost:8765 python -m Src  # run a client
python tools/make_placeholder_sprites.py     # regenerate placeholder art
cd desktop-buddies && npm install            # install website deps
cd desktop-buddies && npm run dev            # website at http://localhost:3000
cd desktop-buddies && npm test               # website unit tests (vitest)
```

To test locally: start the relay, then launch two clients — one creates a room,
the other joins with the code — and watch the two sprites on both desktops.
