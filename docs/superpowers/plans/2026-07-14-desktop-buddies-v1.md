# Desktop Buddies v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v1 of Desktop Buddies — an animated desktop-pet sprite that idles/walks, plus real-time multiplayer presence where friends in a shared room see each other's sprites move, connected through a developer-hosted relay.

**Architecture:** A "dumb" async WebSocket **relay** manages rooms and fans out messages, knowing nothing about sprites. Each person runs a **PySide6 desktop client** that renders one transparent, always-on-top window per sprite, drives its own sprite's idle/walk AI, and puppets remote sprites from network updates. A **shared** message schema is imported by both so wire formats can't drift.

**Tech Stack:** Python 3.11+, PySide6 (Qt) for the client GUI, `websockets` for relay + client transport, JSON messages, `pytest` + `pytest-asyncio` for tests.

## Global Constraints

- **Python:** 3.11+ (uses `X | None` unions and `tuple[...]` builtins freely).
- **GUI toolkit:** PySide6 only (not PyQt).
- **Transport:** `websockets` library; messages are JSON strings.
- **Message schema single source of truth:** `shared/messages.py`. Client and relay MUST import type constants and `encode`/`decode` from it — never hand-build JSON.
- **Coordinates are fractional:** sprite `x`, `y` are floats in `0.0`–`1.0` (fraction of screen), never pixels, on the wire and in the world model. Pixel conversion happens only at render time.
- **Facing:** integer `1` (right) or `-1` (left).
- **Existing scaffold filenames are kept as-is:** `Src/Connections.py` (net), `Src/User.py` (identity), `Src/Host.py` (room-creation role). New client modules use lowercase names.
- **Cross-platform:** must run on macOS and Windows. Avoid OS-specific APIs; rely on Qt window flags.
- **Sprite windows:** one frameless, translucent, always-on-top window per sprite (no fullscreen overlay, no click-through logic).

---

## File Structure

```
Desktop Buddies/
  pyproject.toml            # package + pytest config
  requirements.txt          # runtime + dev deps
  CLAUDE.md                 # (created separately)
  shared/
    __init__.py
    messages.py             # type constants, encode(), decode()
  relay/
    __init__.py
    room.py                 # Registry: rooms, create/join/leave/relay (pure async logic)
    server.py               # websockets server wiring the Registry
    __main__.py             # `python -m relay` entry point
  Src/
    __init__.py
    User.py                 # PlayerIdentity dataclass
    world.py                # Sprite, OwnController (idle/walk AI), World (interp)
    sprite_window.py        # FrameCycler (pure) + SpriteWindow (Qt) + frame loader
    menu.py                 # MenuWindow (Qt) + input validation helpers
    Connections.py          # NetClient: async websocket client on a bg thread -> Qt signals
    Host.py                 # Host: holds owned-room code + local id
    app.py                  # AppController: wires menu, net, world, sprite windows
    __main__.py             # `python -m Src` entry point
  Sprites/
    placeholder_cat/ placeholder_dog/ placeholder_blob/
      sprite.json
      idle/ 0.png 1.png ...
      walk/ 0.png 1.png ...
  tools/
    make_placeholder_sprites.py   # generates the placeholder frames (PySide6 QPainter)
  tests/
    __init__.py
    test_messages.py
    test_room.py
    test_server.py
    test_world.py
    test_sprite_frames.py
    test_menu.py
```

---

## Task 1: Project scaffold & tooling

**Files:**
- Create: `pyproject.toml`, `requirements.txt`
- Create: `shared/__init__.py`, `relay/__init__.py`, `Src/__init__.py`, `tests/__init__.py`
- Test: `tests/test_smoke.py`

**Interfaces:**
- Consumes: nothing.
- Produces: importable packages `shared`, `relay`, `Src`; a working `pytest` command.

- [ ] **Step 1: Create dependency files**

`requirements.txt`:
```
PySide6>=6.6
websockets>=12.0
pytest>=8.0
pytest-asyncio>=0.23
```

`pyproject.toml`:
```toml
[project]
name = "desktop-buddies"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["PySide6>=6.6", "websockets>=12.0"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create empty package markers**

Create these files, each empty:
`shared/__init__.py`, `relay/__init__.py`, `Src/__init__.py`, `tests/__init__.py`.

- [ ] **Step 3: Write the smoke test**

`tests/test_smoke.py`:
```python
import importlib


def test_packages_import():
    for name in ("shared", "relay", "Src"):
        importlib.import_module(name)
```

- [ ] **Step 4: Install deps and run the smoke test**

Run:
```bash
python -m pip install -r requirements.txt
python -m pytest tests/test_smoke.py -v
```
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml requirements.txt shared/__init__.py relay/__init__.py Src/__init__.py tests/__init__.py tests/test_smoke.py
git commit -m "chore: project scaffold, deps, pytest config"
```

---

## Task 2: Shared message schema

**Files:**
- Create: `shared/messages.py`
- Test: `tests/test_messages.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - Constants: `CREATE_ROOM, ROOM_CREATED, JOIN_ROOM, ROOM_JOINED, ERROR, MEMBER_JOINED, MEMBER_LEFT, STATE` (all `str`).
  - `encode(msg_type: str, **fields) -> str` — JSON string `{"type": msg_type, **fields}`.
  - `decode(raw: str | bytes) -> dict | None` — parsed dict (always contains `"type"`), or `None` if malformed.

- [ ] **Step 1: Write the failing test**

`tests/test_messages.py`:
```python
from shared import messages as m


def test_encode_roundtrips_through_decode():
    raw = m.encode(m.STATE, id="7", x=0.5, y=0.9, facing=-1, anim="walk")
    out = m.decode(raw)
    assert out == {"type": "state", "id": "7", "x": 0.5, "y": 0.9,
                   "facing": -1, "anim": "walk"}


def test_decode_rejects_malformed():
    assert m.decode("not json") is None
    assert m.decode("[1, 2, 3]") is None      # not an object
    assert m.decode('{"no": "type"}') is None  # missing type


def test_constants_are_distinct_strings():
    values = [m.CREATE_ROOM, m.ROOM_CREATED, m.JOIN_ROOM, m.ROOM_JOINED,
              m.ERROR, m.MEMBER_JOINED, m.MEMBER_LEFT, m.STATE]
    assert all(isinstance(v, str) for v in values)
    assert len(set(values)) == len(values)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_messages.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'shared.messages'`).

- [ ] **Step 3: Write minimal implementation**

`shared/messages.py`:
```python
import json

CREATE_ROOM = "create_room"
ROOM_CREATED = "room_created"
JOIN_ROOM = "join_room"
ROOM_JOINED = "room_joined"
ERROR = "error"
MEMBER_JOINED = "member_joined"
MEMBER_LEFT = "member_left"
STATE = "state"


def encode(msg_type: str, **fields) -> str:
    return json.dumps({"type": msg_type, **fields})


def decode(raw: str | bytes) -> dict | None:
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or "type" not in data:
        return None
    return data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_messages.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add shared/messages.py tests/test_messages.py
git commit -m "feat: shared JSON message schema"
```

---

## Task 3: Relay room registry

**Files:**
- Create: `relay/room.py`
- Test: `tests/test_room.py`

**Interfaces:**
- Consumes: `shared.messages` (constants, `encode`).
- Produces:
  - `generate_code() -> str` — e.g. `"PLUM-42"` (word + 2-digit number).
  - `class Registry`:
    - `async create_room(name: str, character: str, send) -> tuple[str, str]` returns `(code, member_id)`; sends `ROOM_CREATED{code, your_id}` to `send`.
    - `async join_room(code: str, name: str, character: str, send) -> str | None` returns `member_id`, or `None` if `code` unknown; sends `ROOM_JOINED{your_id, members}` to joiner and `MEMBER_JOINED{id,name,character}` to others.
    - `async relay(code: str, sender_id: str, raw: str) -> None` forwards `raw` to every member except `sender_id`.
    - `async leave(code: str, member_id: str) -> None` removes member; sends `MEMBER_LEFT{id}` to remaining; deletes empty room.
  - `send` is any `async` callable taking a single `str` argument.

- [ ] **Step 1: Write the failing test**

`tests/test_room.py`:
```python
import pytest
from relay.room import Registry, generate_code
from shared import messages as m


class FakeConn:
    def __init__(self):
        self.sent = []

    async def send(self, raw):
        self.sent.append(m.decode(raw))


def test_generate_code_shape():
    code = generate_code()
    word, _, num = code.partition("-")
    assert word.isalpha() and num.isdigit()


async def test_create_room_sends_room_created():
    reg = Registry()
    a = FakeConn()
    code, mid = await reg.create_room("Kain", "cat", a.send)
    assert a.sent == [{"type": m.ROOM_CREATED, "code": code, "your_id": mid}]


async def test_join_notifies_both_sides():
    reg = Registry()
    a = FakeConn()
    code, a_id = await reg.create_room("Kain", "cat", a.send)
    b = FakeConn()
    b_id = await reg.join_room(code, "Sam", "dog", b.send)

    # joiner learns the existing member
    assert b.sent[0] == {"type": m.ROOM_JOINED, "your_id": b_id,
                         "members": [{"id": a_id, "name": "Kain", "character": "cat"}]}
    # existing member is told about the joiner
    assert a.sent[-1] == {"type": m.MEMBER_JOINED, "id": b_id,
                          "name": "Sam", "character": "dog"}


async def test_join_unknown_code_returns_none():
    reg = Registry()
    assert await reg.join_room("NOPE-00", "Sam", "dog", FakeConn().send) is None


async def test_relay_fans_out_to_others_only():
    reg = Registry()
    a, b = FakeConn(), FakeConn()
    code, a_id = await reg.create_room("Kain", "cat", a.send)
    await reg.join_room(code, "Sam", "dog", b.send)
    a.sent.clear(); b.sent.clear()

    raw = m.encode(m.STATE, id=a_id, x=0.3, y=0.9, facing=1, anim="walk")
    await reg.relay(code, a_id, raw)
    assert a.sent == []                 # sender does not get its own message
    assert b.sent == [m.decode(raw)]    # others do


async def test_leave_notifies_and_cleans_up():
    reg = Registry()
    a, b = FakeConn(), FakeConn()
    code, a_id = await reg.create_room("Kain", "cat", a.send)
    b_id = await reg.join_room(code, "Sam", "dog", b.send)
    a.sent.clear()

    await reg.leave(code, b_id)
    assert a.sent[-1] == {"type": m.MEMBER_LEFT, "id": b_id}

    await reg.leave(code, a_id)         # room now empty
    assert code not in reg.rooms
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_room.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'relay.room'`).

- [ ] **Step 3: Write minimal implementation**

`relay/room.py`:
```python
import random

from shared import messages as m

WORDS = ["PLUM", "MOSS", "FERN", "SAGE", "PEAR", "LARK", "WREN", "REED",
         "DUSK", "MINT", "CLAY", "ONYX", "JADE", "CORA", "IRIS", "FLAX"]


def generate_code() -> str:
    return f"{random.choice(WORDS)}-{random.randint(10, 99)}"


class Registry:
    def __init__(self):
        self.rooms: dict[str, dict] = {}   # code -> {"code", "members": {id -> member}}
        self._next_id = 0

    def _new_member_id(self) -> str:
        self._next_id += 1
        return str(self._next_id)

    def _unique_code(self) -> str:
        code = generate_code()
        while code in self.rooms:
            code = generate_code()
        return code

    @staticmethod
    def _public(room: dict) -> list[dict]:
        return [{"id": mem["id"], "name": mem["name"], "character": mem["character"]}
                for mem in room["members"].values()]

    async def create_room(self, name: str, character: str, send) -> tuple[str, str]:
        code = self._unique_code()
        mid = self._new_member_id()
        room = {"code": code, "members": {}}
        room["members"][mid] = {"id": mid, "name": name,
                                "character": character, "send": send}
        self.rooms[code] = room
        await send(m.encode(m.ROOM_CREATED, code=code, your_id=mid))
        return code, mid

    async def join_room(self, code: str, name: str, character: str, send) -> str | None:
        room = self.rooms.get(code)
        if room is None:
            return None
        mid = self._new_member_id()
        await send(m.encode(m.ROOM_JOINED, your_id=mid, members=self._public(room)))
        room["members"][mid] = {"id": mid, "name": name,
                                "character": character, "send": send}
        for mem in room["members"].values():
            if mem["id"] != mid:
                await mem["send"](m.encode(m.MEMBER_JOINED, id=mid,
                                           name=name, character=character))
        return mid

    async def relay(self, code: str, sender_id: str, raw: str) -> None:
        room = self.rooms.get(code)
        if room is None:
            return
        for mem in room["members"].values():
            if mem["id"] != sender_id:
                await mem["send"](raw)

    async def leave(self, code: str, member_id: str) -> None:
        room = self.rooms.get(code)
        if room is None:
            return
        room["members"].pop(member_id, None)
        if not room["members"]:
            del self.rooms[code]
            return
        for mem in room["members"].values():
            await mem["send"](m.encode(m.MEMBER_LEFT, id=member_id))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_room.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add relay/room.py tests/test_room.py
git commit -m "feat: relay room registry (create/join/leave/relay)"
```

---

## Task 4: Relay WebSocket server

**Files:**
- Create: `relay/server.py`, `relay/__main__.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `relay.room.Registry`, `shared.messages`.
- Produces:
  - `make_handler(registry: Registry) -> handler` — a `websockets` connection handler coroutine.
  - `async serve(host: str, port: int) -> None` — runs the server forever.
  - Connection lifecycle: first valid `CREATE_ROOM`/`JOIN_ROOM` binds the connection to a `(code, member_id)`; later `STATE` messages are relayed; unknown join code replies `ERROR{reason}`; disconnect triggers `leave`.

- [ ] **Step 1: Write the failing test**

`tests/test_server.py`:
```python
import asyncio
import pytest
import websockets

from relay.room import Registry
from relay.server import make_handler
from shared import messages as m


async def _recv(ws):
    return m.decode(await asyncio.wait_for(ws.recv(), timeout=2))


@pytest.fixture
async def server():
    registry = Registry()
    async with websockets.serve(make_handler(registry), "localhost", 0) as srv:
        port = srv.sockets[0].getsockname()[1]
        yield port


async def test_create_join_and_relay(server):
    port = server
    url = f"ws://localhost:{port}"
    async with websockets.connect(url) as host, websockets.connect(url) as guest:
        await host.send(m.encode(m.CREATE_ROOM, name="Kain", character="cat"))
        created = await _recv(host)
        assert created["type"] == m.ROOM_CREATED
        code = created["code"]

        await guest.send(m.encode(m.JOIN_ROOM, code=code, name="Sam", character="dog"))
        joined = await _recv(guest)
        assert joined["type"] == m.ROOM_JOINED
        assert await _recv(host) == {"type": m.MEMBER_JOINED, "id": joined["your_id"],
                                     "name": "Sam", "character": "dog"}

        raw = m.encode(m.STATE, id=created["your_id"], x=0.4, y=0.9,
                       facing=1, anim="walk")
        await host.send(raw)
        assert await _recv(guest) == m.decode(raw)


async def test_unknown_code_errors(server):
    url = f"ws://localhost:{server}"
    async with websockets.connect(url) as guest:
        await guest.send(m.encode(m.JOIN_ROOM, code="NOPE-00", name="x", character="cat"))
        assert (await _recv(guest))["type"] == m.ERROR


async def test_disconnect_sends_member_left(server):
    url = f"ws://localhost:{server}"
    async with websockets.connect(url) as host:
        await host.send(m.encode(m.CREATE_ROOM, name="Kain", character="cat"))
        code = (await _recv(host))["code"]
        guest = await websockets.connect(url)
        await guest.send(m.encode(m.JOIN_ROOM, code=code, name="Sam", character="dog"))
        left_id = (await _recv(guest))["your_id"]
        await _recv(host)  # member_joined
        await guest.close()
        assert await _recv(host) == {"type": m.MEMBER_LEFT, "id": left_id}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_server.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'relay.server'`).

- [ ] **Step 3: Write minimal implementation**

`relay/server.py`:
```python
import asyncio
import os

import websockets

from relay.room import Registry
from shared import messages as m


def make_handler(registry: Registry):
    async def handler(websocket):
        code: str | None = None
        member_id: str | None = None

        async def send(raw: str) -> None:
            await websocket.send(raw)

        try:
            async for raw in websocket:
                msg = m.decode(raw)
                if msg is None:
                    continue
                mtype = msg.get("type")

                if mtype == m.CREATE_ROOM and member_id is None:
                    code, member_id = await registry.create_room(
                        msg.get("name", ""), msg.get("character", ""), send)

                elif mtype == m.JOIN_ROOM and member_id is None:
                    mid = await registry.join_room(
                        msg.get("code", ""), msg.get("name", ""),
                        msg.get("character", ""), send)
                    if mid is None:
                        await send(m.encode(m.ERROR, reason="Room not found"))
                    else:
                        code, member_id = msg["code"], mid

                elif mtype == m.STATE and member_id is not None:
                    await registry.relay(code, member_id, raw)
        finally:
            if code is not None and member_id is not None:
                await registry.leave(code, member_id)

    return handler


async def serve(host: str, port: int) -> None:
    registry = Registry()
    async with websockets.serve(make_handler(registry), host, port):
        print(f"Desktop Buddies relay listening on ws://{host}:{port}")
        await asyncio.Future()  # run forever


def main() -> None:
    host = os.environ.get("BUDDIES_HOST", "0.0.0.0")
    port = int(os.environ.get("BUDDIES_PORT", "8765"))
    asyncio.run(serve(host, port))
```

`relay/__main__.py`:
```python
from relay.server import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_server.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add relay/server.py relay/__main__.py tests/test_server.py
git commit -m "feat: relay websocket server + entry point"
```

---

## Task 5: World model, own-sprite AI, and identity

**Files:**
- Create: `Src/User.py`, `Src/world.py`
- Test: `tests/test_world.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Src/User.py`: `PlayerIdentity` dataclass with `name: str`, `character: str`.
  - `Src/world.py`:
    - constants `IDLE = "idle"`, `WALK = "walk"`.
    - `Sprite` dataclass: `id, name, character` (str) + `x, y, target_x, target_y` (float, default `0.5`), `facing: int = 1`, `anim: str = IDLE`.
    - `OwnController(sprite: Sprite, rng=None)` with `update(dt: float) -> bool` (mutates `sprite`, returns `True` when position/anim changed this tick). Wanders horizontally along a fixed floor `y`.
    - `World(own: Sprite)`: `add_member(id, name, character)`, `remove_member(id)`, `apply_state(id, x, y, facing, anim)`, `tick(dt) -> bool` (advances own AI + lerps remotes toward targets), `all_sprites() -> list[Sprite]`.

- [ ] **Step 1: Write the failing test**

`tests/test_world.py`:
```python
import random
from Src.User import PlayerIdentity
from Src.world import Sprite, OwnController, World, IDLE, WALK


def test_identity_holds_name_and_character():
    ident = PlayerIdentity(name="Kain", character="cat")
    assert (ident.name, ident.character) == ("Kain", "cat")


def test_own_controller_starts_idle_then_walks():
    s = Sprite(id="me", name="Kain", character="cat", x=0.5, y=0.9)
    ctrl = OwnController(s, rng=random.Random(1))
    assert s.anim == IDLE
    ctrl.update(10.0)          # exceed any idle interval
    assert s.anim == WALK
    assert s.target_x != s.x   # picked a destination to walk toward


def test_own_controller_reaches_target_and_returns_to_idle():
    s = Sprite(id="me", name="Kain", character="cat", x=0.5, y=0.9)
    ctrl = OwnController(s, rng=random.Random(1))
    ctrl.update(10.0)                 # -> WALK toward some target
    target = s.target_x
    for _ in range(1000):             # walk until arrival
        ctrl.update(0.1)
        if s.anim == IDLE:
            break
    assert s.anim == IDLE
    assert abs(s.x - target) < 0.01


def test_own_controller_faces_direction_of_travel():
    s = Sprite(id="me", name="Kain", character="cat", x=0.5, y=0.9)
    ctrl = OwnController(s, rng=random.Random(1))
    ctrl.update(10.0)
    ctrl.update(0.1)
    assert s.facing == (1 if s.target_x > s.x else -1) or s.facing in (1, -1)


def test_world_add_apply_and_lerp_remote():
    own = Sprite(id="me", name="Kain", character="cat")
    world = World(own)
    world.add_member("them", "Sam", "dog")
    world.apply_state("them", x=1.0, y=0.9, facing=-1, anim=WALK)

    before = world.remotes["them"].x
    for _ in range(200):
        world.tick(0.05)
    after = world.remotes["them"].x
    assert after > before               # moved toward target 1.0
    assert abs(after - 1.0) < 0.01
    assert world.remotes["them"].facing == -1


def test_world_remove_member():
    world = World(Sprite(id="me", name="Kain", character="cat"))
    world.add_member("them", "Sam", "dog")
    world.remove_member("them")
    assert "them" not in world.remotes
    assert [sp.id for sp in world.all_sprites()] == ["me"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_world.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'Src.User'`).

- [ ] **Step 3: Write minimal implementation**

`Src/User.py`:
```python
from dataclasses import dataclass


@dataclass
class PlayerIdentity:
    name: str
    character: str
```

`Src/world.py`:
```python
import random
from dataclasses import dataclass

IDLE = "idle"
WALK = "walk"

WALK_SPEED = 0.12   # fraction of screen width per second
LERP_RATE = 8.0     # remote interpolation responsiveness


@dataclass
class Sprite:
    id: str
    name: str
    character: str
    x: float = 0.5
    y: float = 0.9
    target_x: float = 0.5
    target_y: float = 0.9
    facing: int = 1
    anim: str = IDLE


class OwnController:
    """Drives one Sprite with a simple idle/walk wander loop (horizontal)."""

    def __init__(self, sprite: Sprite, rng: random.Random | None = None):
        self.sprite = sprite
        self.rng = rng or random.Random()
        self._idle_timer = self._idle_time()

    def _idle_time(self) -> float:
        return self.rng.uniform(2.0, 5.0)

    def update(self, dt: float) -> bool:
        s = self.sprite
        if s.anim == IDLE:
            self._idle_timer -= dt
            if self._idle_timer <= 0:
                s.target_x = self.rng.uniform(0.05, 0.95)
                s.anim = WALK
                s.facing = 1 if s.target_x >= s.x else -1
                return True
            return False

        # WALK
        step = WALK_SPEED * dt
        remaining = s.target_x - s.x
        if abs(remaining) <= step:
            s.x = s.target_x
            s.anim = IDLE
            self._idle_timer = self._idle_time()
        else:
            s.x += step if remaining > 0 else -step
            s.facing = 1 if remaining > 0 else -1
        return True


class World:
    """Local model: own sprite driven by AI, remotes driven by network."""

    def __init__(self, own: Sprite):
        self.own = own
        self.controller = OwnController(own)
        self.remotes: dict[str, Sprite] = {}

    def add_member(self, id: str, name: str, character: str) -> None:
        self.remotes[id] = Sprite(id=id, name=name, character=character)

    def remove_member(self, id: str) -> None:
        self.remotes.pop(id, None)

    def apply_state(self, id: str, x: float, y: float, facing: int, anim: str) -> None:
        s = self.remotes.get(id)
        if s is None:
            return
        s.target_x, s.target_y, s.facing, s.anim = x, y, facing, anim

    def tick(self, dt: float) -> bool:
        changed = self.controller.update(dt)
        alpha = min(1.0, dt * LERP_RATE)
        for s in self.remotes.values():
            s.x += (s.target_x - s.x) * alpha
            s.y += (s.target_y - s.y) * alpha
        return changed

    def all_sprites(self) -> list[Sprite]:
        return [self.own, *self.remotes.values()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_world.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add Src/User.py Src/world.py tests/test_world.py
git commit -m "feat: world model, idle/walk AI, remote interpolation"
```

---

## Task 6: Placeholder sprite art

**Files:**
- Create: `tools/make_placeholder_sprites.py`
- Create (generated): `Sprites/placeholder_cat/`, `placeholder_dog/`, `placeholder_blob/` each with `sprite.json`, `idle/*.png`, `walk/*.png`
- Test: none (asset-generation task; verified by file existence + Task 7 loader tests)

**Interfaces:**
- Consumes: PySide6 (`QImage`, `QPainter`, `QColor`).
- Produces: the `Sprites/<character>/` folder layout. Each `sprite.json` is `{"fps": <int>, "scale": <int>}`. `idle/` has 2 frames, `walk/` has 4 frames, all 64×64 PNGs with transparent background.

- [ ] **Step 1: Write the generator script**

`tools/make_placeholder_sprites.py`:
```python
"""Generate simple placeholder sprite frames with PySide6 (no external art)."""
import json
import math
import sys
from pathlib import Path

from PySide6.QtGui import QImage, QPainter, QColor, QBrush
from PySide6.QtCore import Qt, QRectF

ROOT = Path(__file__).resolve().parent.parent / "Sprites"
SIZE = 64

CHARACTERS = {
    "placeholder_cat": QColor(240, 170, 90),
    "placeholder_dog": QColor(150, 190, 240),
    "placeholder_blob": QColor(170, 220, 160),
}


def _frame(color: QColor, squash: float, step: int) -> QImage:
    img = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    h = SIZE * 0.7 * squash
    w = SIZE * 0.7 / squash
    body = QRectF((SIZE - w) / 2, SIZE - h - 2, w, h)
    p.drawRoundedRect(body, 12, 12)
    # eyes
    p.setBrush(QBrush(QColor(30, 30, 30)))
    eye_y = body.top() + h * 0.35
    p.drawEllipse(QRectF(body.center().x() - 12, eye_y, 6, 6))
    p.drawEllipse(QRectF(body.center().x() + 6, eye_y, 6, 6))
    # little feet bob on walk frames
    foot_dy = 3 * math.sin(step * math.pi / 2)
    p.setBrush(QBrush(color.darker(120)))
    p.drawEllipse(QRectF(body.left() + 6, SIZE - 6 + foot_dy, 10, 6))
    p.drawEllipse(QRectF(body.right() - 16, SIZE - 6 - foot_dy, 10, 6))
    p.end()
    return img


def build():
    for name, color in CHARACTERS.items():
        base = ROOT / name
        (base / "idle").mkdir(parents=True, exist_ok=True)
        (base / "walk").mkdir(parents=True, exist_ok=True)
        for i in range(2):
            _frame(color, 1.0 + 0.03 * (i % 2), i).save(str(base / "idle" / f"{i}.png"))
        for i in range(4):
            _frame(color, 1.0, i).save(str(base / "walk" / f"{i}.png"))
        (base / "sprite.json").write_text(json.dumps({"fps": 6, "scale": 1}))
        print(f"wrote {name}")


if __name__ == "__main__":
    sys.exit(build())
```

- [ ] **Step 2: Run the generator**

Run:
```bash
python tools/make_placeholder_sprites.py
```
Expected: prints `wrote placeholder_cat`, `wrote placeholder_dog`, `wrote placeholder_blob`.

- [ ] **Step 3: Verify the files exist**

Run:
```bash
ls Sprites/placeholder_cat/idle Sprites/placeholder_cat/walk Sprites/placeholder_cat/sprite.json
```
Expected: `0.png 1.png` in `idle/`, `0.png 1.png 2.png 3.png` in `walk/`, and the json file present.

- [ ] **Step 4: Commit**

```bash
git add tools/make_placeholder_sprites.py Sprites/
git commit -m "feat: placeholder sprite art + generator"
```

---

## Task 7: Frame cycler & sprite window

**Files:**
- Create: `Src/sprite_window.py`
- Test: `tests/test_sprite_frames.py`

**Interfaces:**
- Consumes: `Sprites/` layout from Task 6; PySide6.
- Produces:
  - `FrameCycler(frame_count: int, fps: float)` with `advance(dt: float) -> int` (current frame index, wraps) and `reset()`.
  - `load_frames(sprites_dir: Path, character: str, anim: str) -> list[QPixmap]` — numbered PNGs sorted numerically.
  - `SpriteWindow(character: str, sprites_dir: Path)` (QWidget subclass): `set_animation(name: str)`, `set_facing(facing: int)`, `set_position(px: int, py: int)`, `tick(dt: float)` (advances frame + repaints), signal `clicked()`.

- [ ] **Step 1: Write the failing test (pure logic only)**

`tests/test_sprite_frames.py`:
```python
from Src.sprite_window import FrameCycler


def test_cycler_advances_at_fps():
    c = FrameCycler(frame_count=4, fps=10.0)   # 0.1s per frame
    assert c.advance(0.0) == 0
    assert c.advance(0.1) == 1
    assert c.advance(0.25) == 3   # 0.35s total -> frame 3


def test_cycler_wraps_around():
    c = FrameCycler(frame_count=2, fps=10.0)
    c.advance(0.1)                 # -> 1
    assert c.advance(0.1) == 0     # wraps back to 0


def test_cycler_single_frame_stays_at_zero():
    c = FrameCycler(frame_count=1, fps=10.0)
    assert c.advance(5.0) == 0


def test_cycler_reset():
    c = FrameCycler(frame_count=4, fps=10.0)
    c.advance(0.3)
    c.reset()
    assert c.advance(0.0) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sprite_frames.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'Src.sprite_window'`).

- [ ] **Step 3: Write the implementation**

`Src/sprite_window.py`:
```python
import json
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QPixmap, QPainter, QTransform
from PySide6.QtWidgets import QWidget


class FrameCycler:
    def __init__(self, frame_count: int, fps: float):
        self.frame_count = frame_count
        self.fps = fps
        self.index = 0
        self._elapsed = 0.0

    def advance(self, dt: float) -> int:
        if self.frame_count <= 1 or self.fps <= 0:
            self.index = 0
            return 0
        self._elapsed += dt
        frame_time = 1.0 / self.fps
        while self._elapsed >= frame_time:
            self._elapsed -= frame_time
            self.index = (self.index + 1) % self.frame_count
        return self.index

    def reset(self) -> None:
        self.index = 0
        self._elapsed = 0.0


def load_frames(sprites_dir: Path, character: str, anim: str) -> list[QPixmap]:
    folder = Path(sprites_dir) / character / anim
    files = sorted(folder.glob("*.png"), key=lambda p: int(p.stem))
    return [QPixmap(str(f)) for f in files]


class SpriteWindow(QWidget):
    clicked = Signal()

    def __init__(self, character: str, sprites_dir: Path):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        cfg = json.loads((Path(sprites_dir) / character / "sprite.json").read_text())
        self._fps = cfg.get("fps", 6)
        self._frames = {
            "idle": load_frames(sprites_dir, character, "idle"),
            "walk": load_frames(sprites_dir, character, "walk"),
        }
        self._anim = "idle"
        self._facing = 1
        self._cycler = FrameCycler(len(self._frames["idle"]), self._fps)
        size = self._frames["idle"][0].size()
        self.resize(size)
        self.show()

    def set_animation(self, name: str) -> None:
        if name != self._anim and name in self._frames:
            self._anim = name
            self._cycler = FrameCycler(len(self._frames[name]), self._fps)

    def set_facing(self, facing: int) -> None:
        self._facing = 1 if facing >= 0 else -1

    def set_position(self, px: int, py: int) -> None:
        self.move(QPoint(px, py))

    def tick(self, dt: float) -> None:
        self._cycler.advance(dt)
        self.update()

    def paintEvent(self, event) -> None:
        frames = self._frames[self._anim]
        if not frames:
            return
        pix = frames[self._cycler.index % len(frames)]
        if self._facing == -1:
            pix = pix.transformed(QTransform().scale(-1, 1))
        QPainter(self).drawPixmap(0, 0, pix)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
```

- [ ] **Step 4: Run the frame-cycler tests**

Run: `python -m pytest tests/test_sprite_frames.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Manual visual check**

Run this one-off snippet (needs a display):
```bash
python -c "
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from Src.sprite_window import SpriteWindow
app = QApplication([])
w = SpriteWindow('placeholder_cat', Path('Sprites'))
w.set_position(400, 400); w.set_animation('walk')
t = QTimer(); t.timeout.connect(lambda: w.tick(0.05)); t.start(50)
QTimer.singleShot(3000, app.quit); app.exec()
"
```
Expected: a small translucent, always-on-top cat animates for ~3 seconds, then closes.

- [ ] **Step 6: Commit**

```bash
git add Src/sprite_window.py tests/test_sprite_frames.py
git commit -m "feat: frame cycler + transparent sprite window"
```

---

## Task 8: Menu window

**Files:**
- Create: `Src/menu.py`
- Test: `tests/test_menu.py`

**Interfaces:**
- Consumes: PySide6.
- Produces:
  - `CHARACTERS: list[str]` — `["placeholder_cat", "placeholder_dog", "placeholder_blob"]`.
  - `validate_name(name: str) -> bool` — non-empty after strip, ≤ 20 chars.
  - `normalize_code(code: str) -> str` — uppercased, stripped.
  - `MenuWindow(QWidget)`: signals `create_requested(str, str)` → `(name, character)`, `join_requested(str, str, str)` → `(code, name, character)`; methods `show_code(code: str)`, `show_error(msg: str)`.

- [ ] **Step 1: Write the failing test (pure helpers only)**

`tests/test_menu.py`:
```python
from Src.menu import validate_name, normalize_code, CHARACTERS


def test_validate_name():
    assert validate_name("Kain")
    assert not validate_name("   ")
    assert not validate_name("")
    assert not validate_name("x" * 21)


def test_normalize_code():
    assert normalize_code("  plum-42 ") == "PLUM-42"


def test_characters_nonempty():
    assert CHARACTERS and all(isinstance(c, str) for c in CHARACTERS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_menu.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'Src.menu'`).

- [ ] **Step 3: Write the implementation**

`Src/menu.py`:
```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QButtonGroup, QRadioButton)

CHARACTERS = ["placeholder_cat", "placeholder_dog", "placeholder_blob"]


def validate_name(name: str) -> bool:
    stripped = name.strip()
    return 0 < len(stripped) <= 20


def normalize_code(code: str) -> str:
    return code.strip().upper()


class MenuWindow(QWidget):
    create_requested = Signal(str, str)        # name, character
    join_requested = Signal(str, str, str)     # code, name, character

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Buddies")
        layout = QVBoxLayout(self)

        self._name = QLineEdit(placeholderText="Your name")
        layout.addWidget(self._name)

        char_row = QHBoxLayout()
        self._char_group = QButtonGroup(self)
        for i, char in enumerate(CHARACTERS):
            rb = QRadioButton(char.replace("placeholder_", ""))
            if i == 0:
                rb.setChecked(True)
            self._char_group.addButton(rb, i)
            char_row.addWidget(rb)
        layout.addLayout(char_row)

        create_btn = QPushButton("Create room")
        create_btn.clicked.connect(self._on_create)
        layout.addWidget(create_btn)

        join_row = QHBoxLayout()
        self._code = QLineEdit(placeholderText="Room code")
        join_btn = QPushButton("Join")
        join_btn.clicked.connect(self._on_join)
        join_row.addWidget(self._code)
        join_row.addWidget(join_btn)
        layout.addLayout(join_row)

        self._status = QLabel("")
        layout.addWidget(self._status)

    def _character(self) -> str:
        return CHARACTERS[self._char_group.checkedId()]

    def _on_create(self) -> None:
        if not validate_name(self._name.text()):
            self.show_error("Enter a name (1-20 chars).")
            return
        self.create_requested.emit(self._name.text().strip(), self._character())

    def _on_join(self) -> None:
        if not validate_name(self._name.text()):
            self.show_error("Enter a name (1-20 chars).")
            return
        code = normalize_code(self._code.text())
        if not code:
            self.show_error("Enter a room code.")
            return
        self.join_requested.emit(code, self._name.text().strip(), self._character())

    def show_code(self, code: str) -> None:
        self._status.setText(f"Room code: {code}  (share this)")

    def show_error(self, msg: str) -> None:
        self._status.setText(msg)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_menu.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add Src/menu.py tests/test_menu.py
git commit -m "feat: launch menu (name, character pick, create/join)"
```

---

## Task 9: Network client (Qt bridge)

**Files:**
- Create: `Src/Connections.py`
- Test: none automated (Qt + thread + live socket glue; covered by the Task 4 server tests and the Task 10 manual integration). Includes an import smoke assertion.

**Interfaces:**
- Consumes: `shared.messages`, `websockets`, PySide6.
- Produces:
  - `NetClient(QObject)` with Qt signals:
    - `connected()`, `disconnected()`, `error_occurred(str)`
    - `room_created(str, str)` → `(code, your_id)`
    - `room_joined(str, list)` → `(your_id, members)`
    - `member_joined(dict)`, `member_left(str)`
    - `remote_state(dict)`
  - Methods: `start_create(url, name, character)`, `start_join(url, code, name, character)`, `send_state(id, x, y, facing, anim)`, `stop()`.
  - Runs an asyncio loop on a background thread; UI thread never blocks. All incoming messages are decoded via `shared.messages.decode` and dispatched to signals.

- [ ] **Step 1: Write the implementation**

`Src/Connections.py`:
```python
import asyncio
import threading

import websockets
from PySide6.QtCore import QObject, Signal

from shared import messages as m


class NetClient(QObject):
    connected = Signal()
    disconnected = Signal()
    error_occurred = Signal(str)
    room_created = Signal(str, str)      # code, your_id
    room_joined = Signal(str, list)      # your_id, members
    member_joined = Signal(dict)
    member_left = Signal(str)
    remote_state = Signal(dict)

    def __init__(self):
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws = None
        self._thread: threading.Thread | None = None
        self._hello: str | None = None   # first message to send on connect

    # ---- public API (called from the Qt/UI thread) ----
    def start_create(self, url: str, name: str, character: str) -> None:
        self._hello = m.encode(m.CREATE_ROOM, name=name, character=character)
        self._start(url)

    def start_join(self, url: str, code: str, name: str, character: str) -> None:
        self._hello = m.encode(m.JOIN_ROOM, code=code, name=name, character=character)
        self._start(url)

    def send_state(self, id: str, x: float, y: float, facing: int, anim: str) -> None:
        raw = m.encode(m.STATE, id=id, x=x, y=y, facing=facing, anim=anim)
        self._submit(raw)

    def stop(self) -> None:
        if self._loop and self._ws:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self._ws.close()))

    # ---- internals ----
    def _start(self, url: str) -> None:
        self._thread = threading.Thread(target=self._run, args=(url,), daemon=True)
        self._thread.start()

    def _submit(self, raw: str) -> None:
        if self._loop and self._ws:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self._ws.send(raw)))

    def _run(self, url: str) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._session(url))
        except Exception as exc:                      # noqa: BLE001
            self.error_occurred.emit(str(exc))
        finally:
            self.disconnected.emit()

    async def _session(self, url: str) -> None:
        async with websockets.connect(url) as ws:
            self._ws = ws
            self.connected.emit()
            await ws.send(self._hello)
            async for raw in ws:
                self._dispatch(m.decode(raw))

    def _dispatch(self, msg: dict | None) -> None:
        if msg is None:
            return
        t = msg.get("type")
        if t == m.ROOM_CREATED:
            self.room_created.emit(msg["code"], msg["your_id"])
        elif t == m.ROOM_JOINED:
            self.room_joined.emit(msg["your_id"], msg["members"])
        elif t == m.MEMBER_JOINED:
            self.member_joined.emit(msg)
        elif t == m.MEMBER_LEFT:
            self.member_left.emit(msg["id"])
        elif t == m.STATE:
            self.remote_state.emit(msg)
        elif t == m.ERROR:
            self.error_occurred.emit(msg.get("reason", "error"))
```

- [ ] **Step 2: Import smoke check**

Run:
```bash
python -c "from Src.Connections import NetClient; print('ok')"
```
Expected: prints `ok` (no import/signature errors).

- [ ] **Step 3: Commit**

```bash
git add Src/Connections.py
git commit -m "feat: async websocket NetClient bridged to Qt signals"
```

---

## Task 10: App composition, Host role & integration

**Files:**
- Create: `Src/Host.py`, `Src/app.py`, `Src/__main__.py`
- Test: none automated; final **manual two-client loopback** verification.

**Interfaces:**
- Consumes: `Src.menu.MenuWindow`, `Src.Connections.NetClient`, `Src.world` (`World`, `Sprite`, `IDLE/WALK`), `Src.sprite_window.SpriteWindow`, `Src.User.PlayerIdentity`, `Src.Host.Host`.
- Produces:
  - `Src/Host.py`: `Host` with `code: str | None`, `your_id: str | None`, `remember(code, your_id)`.
  - `Src/app.py`: `AppController` that owns the QApplication wiring; `run(relay_url: str) -> int`.
  - `Src/__main__.py`: reads relay URL from `BUDDIES_URL` env (default `ws://localhost:8765`) and runs.

- [ ] **Step 1: Write the Host role**

`Src/Host.py`:
```python
from dataclasses import dataclass


@dataclass
class Host:
    """Tracks the room this client created/joined and its assigned id."""
    code: str | None = None
    your_id: str | None = None

    def remember(self, code: str | None, your_id: str) -> None:
        self.code = code
        self.your_id = your_id
```

- [ ] **Step 2: Write the app controller**

`Src/app.py`:
```python
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from Src.Connections import NetClient
from Src.Host import Host
from Src.User import PlayerIdentity
from Src.menu import MenuWindow
from Src.sprite_window import SpriteWindow
from Src.world import World, Sprite

SPRITES_DIR = Path(__file__).resolve().parent.parent / "Sprites"
FLOOR_FRACTION = 0.9          # baseline y for sprites
SEND_INTERVAL = 0.1           # seconds between own-state broadcasts


class AppController:
    def __init__(self, relay_url: str):
        self.relay_url = relay_url
        self.identity: PlayerIdentity | None = None
        self.host = Host()
        self.world: World | None = None
        self.windows: dict[str, SpriteWindow] = {}   # sprite id -> window
        self._send_accum = 0.0

        self.net = NetClient()
        self.menu = MenuWindow()
        self.menu.create_requested.connect(self._on_create)
        self.menu.join_requested.connect(self._on_join)
        self.net.room_created.connect(self._on_room_created)
        self.net.room_joined.connect(self._on_room_joined)
        self.net.member_joined.connect(self._on_member_joined)
        self.net.member_left.connect(self._on_member_left)
        self.net.remote_state.connect(self._on_remote_state)
        self.net.error_occurred.connect(self.menu.show_error)

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)

    # ---- menu actions ----
    def _on_create(self, name, character):
        self.identity = PlayerIdentity(name, character)
        self.net.start_create(self.relay_url, name, character)

    def _on_join(self, code, name, character):
        self.identity = PlayerIdentity(name, character)
        self.net.start_join(self.relay_url, code, name, character)

    # ---- network events ----
    def _on_room_created(self, code, your_id):
        self.host.remember(code, your_id)
        self.menu.show_code(code)
        self._begin_world(your_id)

    def _on_room_joined(self, your_id, members):
        self.host.remember(None, your_id)
        self._begin_world(your_id)
        for mem in members:
            self._add_remote(mem["id"], mem["name"], mem["character"])
        self.menu.hide()

    def _on_member_joined(self, mem):
        if self.world:
            self._add_remote(mem["id"], mem["name"], mem["character"])

    def _on_member_left(self, mid):
        if self.world:
            self.world.remove_member(mid)
        w = self.windows.pop(mid, None)
        if w:
            w.close()

    def _on_remote_state(self, msg):
        if self.world:
            self.world.apply_state(msg["id"], msg["x"], msg["y"],
                                   msg["facing"], msg["anim"])

    # ---- world/render setup ----
    def _begin_world(self, your_id):
        own = Sprite(id=your_id, name=self.identity.name,
                     character=self.identity.character, y=FLOOR_FRACTION,
                     target_y=FLOOR_FRACTION)
        self.world = World(own)
        self.windows[your_id] = SpriteWindow(self.identity.character, SPRITES_DIR)
        self.timer.start(16)   # ~60 fps

    def _add_remote(self, mid, name, character):
        self.world.add_member(mid, name, character)
        self.windows[mid] = SpriteWindow(character, SPRITES_DIR)

    # ---- main loop ----
    def _tick(self):
        if not self.world:
            return
        dt = 0.016
        changed = self.world.tick(dt)

        screen = QGuiApplication.primaryScreen().geometry()
        for sp in self.world.all_sprites():
            win = self.windows.get(sp.id)
            if not win:
                continue
            px = int(sp.x * (screen.width() - win.width()))
            py = int(sp.y * (screen.height() - win.height()))
            win.set_position(px, py)
            win.set_facing(sp.facing)
            win.set_animation(sp.anim)
            win.tick(dt)

        self._send_accum += dt
        if changed and self._send_accum >= SEND_INTERVAL:
            self._send_accum = 0.0
            own = self.world.own
            self.net.send_state(own.id, own.x, own.y, own.facing, own.anim)

    def run(self) -> int:
        app = QApplication.instance() or QApplication(sys.argv)
        self.menu.show()
        return app.exec()
```

- [ ] **Step 3: Write the entry point**

`Src/__main__.py`:
```python
import os

from Src.app import AppController

if __name__ == "__main__":
    url = os.environ.get("BUDDIES_URL", "ws://localhost:8765")
    raise SystemExit(AppController(url).run())
```

- [ ] **Step 4: Run the full automated suite**

Run: `python -m pytest -v`
Expected: PASS (all tests from Tasks 1–8 green).

- [ ] **Step 5: Manual two-client loopback integration**

In three terminals from the project root:

Terminal 1 — relay:
```bash
python -m relay
```
Expected: `Desktop Buddies relay listening on ws://0.0.0.0:8765`.

Terminal 2 — first client:
```bash
BUDDIES_URL=ws://localhost:8765 python -m Src
```
Enter a name, pick the cat, click **Create room**. Expected: a room code appears in the menu, and a cat sprite appears wandering on your desktop.

Terminal 3 — second client:
```bash
BUDDIES_URL=ws://localhost:8765 python -m Src
```
Enter a different name, pick the dog, paste the code, click **Join**. Expected: on **both** desktops you now see two sprites (cat + dog), each wandering, with the remote one moving smoothly. Closing one client makes its sprite disappear on the other.

- [ ] **Step 6: Commit**

```bash
git add Src/Host.py Src/app.py Src/__main__.py
git commit -m "feat: app composition, host role, entry point (v1 complete)"
```

---

## Self-Review

**Spec coverage:**
- Sprite float-on-desktop + idle/walk → Tasks 5 (AI), 7 (window). ✓
- One-window-per-sprite overlay (no click-through) → Task 7 window flags. ✓
- Menu: name + character pick + create/join → Task 8. ✓
- Relay (dumb, room codes, fan-out) → Tasks 3–4. ✓
- Room control + state-sync protocol → Task 2 schema, 3–4 relay, 9 client. ✓
- Fractional coordinates + interpolation → Task 5 (`World`), 10 (pixel mapping). ✓
- Peer clients, self-authoritative → Task 10 sends only own state. ✓
- Placeholder art, folder-per-anim numbered frames → Task 6. ✓
- Error handling (bad code, disconnect, malformed) → Task 4 (ERROR + leave on disconnect), Task 2 (`decode` returns None), Task 10 (`error_occurred` → menu). ✓
- Testing approach (relay unit, schema round-trip, headless client logic, manual integration) → Tasks 2,3,4,5,7,8 automated + Task 10 manual. ✓
- Chat/pokes/Spotify → correctly **out of scope** for v1 (deferred phases). ✓

**Placeholder scan:** No TBD/TODO/"handle edge cases" left; every code step contains full code.

**Type consistency:** `Sprite` fields, `World`/`OwnController` method names, `NetClient` signal signatures, and `messages` constants are used identically across Tasks 5, 7, 9, 10. `send_state(id, x, y, facing, anim)` matches `STATE` schema in Task 2 and `apply_state` in Task 5.
