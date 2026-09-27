# Public Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Desktop Buddies v1.0.0 publicly: a hosted relay on Fly.io, unsigned installers for macOS (arm64 + x64), Windows and Linux built by GitHub Actions, an in-app update notice, and a Vercel-hosted site whose download buttons point at the latest GitHub Release.

**Architecture:** The relay gains small hardening changes and ships as a Docker image to one always-on Fly machine behind Fly's TLS proxy. The client gains a version constant, a frozen-aware resource lookup, a certifi-backed TLS context, a `--smoke-test` mode, and a GitHub-Releases update check; PyInstaller packages it per-OS in a tag-triggered CI matrix that smoke-tests each built binary. The site's `downloads.ts` points at version-less `releases/latest/download/<file>` URLs so it never changes per release.

**Tech Stack:** Python 3.11, PySide6 6.x (QtNetwork for the update check), websockets 12, certifi, pytest; PyInstaller 6 + Pillow (icon conversion), hdiutil, Inno Setup 6, appimagetool; GitHub Actions; Fly.io (flyctl); Next 16 / React 19 / vitest; Vercel.

**Spec:** `docs/superpowers/specs/2026-09-27-public-release-design.md`

## Global Constraints

- Python **3.11+**, **PySide6** (never PyQt). Qt-free logic stays in Qt-free modules so it tests headless.
- `websockets` pinned **`>=12,<13`** everywhere (requirements, pyproject, relay Dockerfile) — the code and tests are written against the 12.x API.
- First release version is **`1.0.0`**; tags are **`vX.Y.Z`**; releases are cut from **`main`** only.
- Artifact filenames carry **no version**, exactly: `DesktopBuddies-mac-arm64.dmg`, `DesktopBuddies-mac-x64.dmg`, `DesktopBuddies-windows-setup.exe`, `DesktopBuddies-linux-x86_64.AppImage`, plus `SHA256SUMS.txt`.
- Release download base URL: `https://github.com/KainBC/Desktop-Buddies/releases/latest/download`.
- Relay: **exactly one** Fly machine, never auto-stopped; `MAX_FRAME = 64 * 1024` bytes; `MAX_MEMBERS = 16`; full-room reason text exactly `"Room is full"`; not-found reason text exactly `"Room not found"`.
- Relay logs room codes and member ids only — **never names, appearances, or chat text**.
- The update check never blocks, never shows an error, and is skipped when `BUDDIES_NO_UPDATE_CHECK=1` or in `--smoke-test`.
- No code signing anywhere. Each packaging step is its own named CI step so signing can slot in after it later.
- Existing capitalized module names (`Connections.py`, `User.py`, `Host.py`) are kept; new modules are lowercase.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **`wss://` from the frozen app on a user's machine** — python.org/`setup-python` OpenSSL looks for CAs in its build prefix, which doesn't exist on users' machines, so certificate verification would fail and nobody could connect. Expect: the client verifies against certifi's bundle; the smoke test fails the build if that bundle is missing. (Task 4, Task 5.)
2. **Peer-supplied name that is not a string or is huge** (a modified client bypasses `validate_name`) — expect the relay to coerce to `""` / strip / truncate to 20 chars before storing or forwarding, so no desktop renders a 60 KB label. (Task 2.)
3. **Relay unreachable at launch** (offline, DNS failure, Fly restarting) — expect the menu to show an error and Create/Join to work again on the next click, not a dead thread that ignores clicks. (Task 4.)
4. **GitHub answers the update check with 404 (no releases yet) or 403 (rate limited)** — expect no notice and no error, just silence. (Task 6.)
5. **ARM Linux user sees the Linux button** (userAgent can't tell arch) — expect the Linux steps to state it is x86_64 only, so they aren't left with a binary that silently won't exec. (Task 10.)

---

## File map

| File | Status | Responsibility |
|---|---|---|
| `Src/version.py` | new | `VERSION` — single source of truth. |
| `Src/resources.py` | new | `sprites_dir()` — frozen-aware path to `Sprites/`. |
| `Src/smoke.py` | new | `run_smoke_test()` — headless self-check of a (frozen) build. |
| `Src/updates.py` | new | Pure: `parse_version`, `is_newer`, `latest_tag_from_json`, URLs. |
| `Src/update_checker.py` | new | Qt: `UpdateChecker` — one async GET to GitHub. |
| `Src/__main__.py` | modify | `main(argv)`, `relay_url(env)`, `DEFAULT_RELAY_URL`, `--smoke-test`. |
| `Src/Connections.py` | modify | `ssl_context_for(url)`; pass it to `websockets.connect`. |
| `Src/menu.py` | modify | Version label; `show_update(tag)`; `update_notice()`. |
| `Src/app.py` | modify | Use `sprites_dir()`; wire `UpdateChecker`. |
| `relay/room.py` | modify | `JoinError`, `MAX_MEMBERS`, `clean_name`, logging. |
| `relay/server.py` | modify | `start_server()`, `MAX_FRAME`, logging, `JoinError` → `ERROR`. |
| `relay/Dockerfile`, `.dockerignore`, `fly.toml` | new | Relay image + Fly config. |
| `tools/make_icons.py`, `packaging/icons/buddy.png` | new | App icon (PyInstaller converts PNG → icns/ico). |
| `packaging/launch.py`, `packaging/buddies.spec` | new | PyInstaller entry + spec. |
| `packaging/windows.iss` | new | Inno Setup installer. |
| `packaging/linux/AppRun`, `packaging/linux/desktop-buddies.desktop`, `packaging/linux/build_appimage.sh` | new | AppImage assembly. |
| `.github/workflows/release.yml` | new | Test → build ×4 → release. |
| `tests/test_version.py`, `tests/test_resources.py`, `tests/test_smoke_mode.py`, `tests/test_updates.py`, `tests/test_update_checker.py`, `tests/test_packaging.py` | new | Tests. |
| `tests/test_room.py`, `tests/test_server.py`, `tests/test_connections.py`, `tests/test_menu.py` | modify | Tests. |
| `requirements.txt`, `pyproject.toml`, `run.sh`, `.gitignore`, `CLAUDE.md` | modify | Deps, version, dev env, ignores, docs. |
| `desktop-buddies/lib/downloads.ts`, `desktop-buddies/lib/downloads.test.ts` | modify/new | Builds, URLs, steps, `primaryBuild`, `buildName`. |
| `desktop-buddies/components/DownloadButton.tsx`, `desktop-buddies/app/download/page.tsx`, `desktop-buddies/components/Steps.tsx`, `desktop-buddies/app/page.tsx` | modify | Live downloads + first-launch copy. |

Execution order matters: Task 3 produces the relay URL Task 4 bakes in; Task 11 produces the site URL written into `Src/updates.py`; Task 12 tags only after everything is on `main`.

Tasks marked **[USER]** contain steps only the human can do (accounts, dashboards, passwords). The executor stops at those steps, tells the user exactly what to run/click, and waits.

---

### Task 1: Release baseline and version constant

**Files:**
- Create: `Src/version.py`, `tests/test_version.py`
- Modify: `pyproject.toml`, `.gitignore`

**Interfaces:**
- Produces: `Src.version.VERSION: str` (`"1.0.0"`).

- [ ] **Step 1: Fast-forward `main` and push (confirm with the user before pushing)**

The current branch (`encounters`) contains everything on `main` plus 20+ commits. Run:

```bash
git checkout main
git merge --ff-only encounters
git log --oneline -1
```

Expected: fast-forward succeeds; HEAD is this plan's commit. Ask the user: "OK to push `main` to origin?" On yes:

```bash
git push origin main
```

- [ ] **Step 2: Create the working branch and remove the empty `website/` directory**

```bash
git checkout -b public-release
rmdir website
git status --short
```

Expected: `rmdir` succeeds (it is empty and untracked, so `git status` shows nothing new for it). If `rmdir` fails because it isn't empty, stop and show the user its contents.

- [ ] **Step 3: Ignore build output**

Append to `.gitignore`:

```gitignore

# Packaging
build/
dist/
out/
```

- [ ] **Step 4: Write the failing test**

Create `tests/test_version.py`:

```python
import tomllib
from pathlib import Path

from Src.version import VERSION
from Src.updates import parse_version

ROOT = Path(__file__).resolve().parent.parent


def test_version_is_semver():
    assert parse_version(VERSION) is not None


def test_pyproject_version_matches():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert data["project"]["version"] == VERSION
```

`Src.updates` doesn't exist yet; to keep this task self-contained, create the pure parser now (Task 6 extends the same file). Create `Src/updates.py`:

```python
"""Update-check logic. Pure: no Qt, no network.

The Qt side (Src/update_checker.py) fetches GitHub's latest release and hands
the tag to these functions; everything that can be wrong about a tag is
decided here, where it tests headless.
"""
import re

_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_version(tag) -> tuple[int, int, int] | None:
    """`"v1.2.3"` or `"1.2.3"` -> `(1, 2, 3)`; anything else -> None."""
    if not isinstance(tag, str):
        return None
    match = _VERSION.match(tag.strip())
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())
```

- [ ] **Step 5: Run to verify it fails**

Run: `python3 -m pytest tests/test_version.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'Src.version'`.

- [ ] **Step 6: Implement**

Create `Src/version.py`:

```python
"""The client's version. The single source of truth.

Bump this, commit, then tag `v<VERSION>`; CI refuses a tag that doesn't
match. A module constant rather than package metadata because PyInstaller
bundles don't reliably carry dist-info.
"""
VERSION = "1.0.0"
```

In `pyproject.toml`, change `version = "0.1.0"` to `version = "1.0.0"`.

- [ ] **Step 7: Run to verify it passes**

Run: `python3 -m pytest tests/test_version.py -v`
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add Src/version.py Src/updates.py tests/test_version.py pyproject.toml .gitignore
git commit -m "feat: VERSION constant as the single source of truth

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Relay hardening — room cap, frame cap, name cleaning, logging

**Files:**
- Modify: `relay/room.py`, `relay/server.py`, `tests/test_room.py`, `tests/test_server.py`, `requirements.txt`, `pyproject.toml`

**Interfaces:**
- Produces:
  - `relay.room.MAX_MEMBERS = 16`, `relay.room.MAX_NAME = 20`
  - `relay.room.ROOM_NOT_FOUND = "Room not found"`, `relay.room.ROOM_FULL = "Room is full"`
  - `relay.room.JoinError(reason: str)` with `.reason: str`
  - `relay.room.clean_name(name) -> str`
  - `Registry(max_members: int = MAX_MEMBERS)`; `Registry.join_room(...) -> str` (raises `JoinError`, never returns `None`)
  - `relay.server.MAX_FRAME = 64 * 1024`
  - `relay.server.start_server(host: str, port: int, registry: Registry | None = None) -> websockets.WebSocketServer` (async)

- [ ] **Step 1: Pin websockets**

In `requirements.txt` change `websockets>=12.0` to `websockets>=12,<13`. In `pyproject.toml` change `"websockets>=12.0"` to `"websockets>=12,<13"`. Run `python3 -m pip install -r requirements.txt` — expect websockets 12.x stays installed.

- [ ] **Step 2: Write failing registry tests**

In `tests/test_room.py`, change the import line to:

```python
from relay.room import (Registry, generate_code, JoinError, ROOM_FULL,
                        ROOM_NOT_FOUND, MAX_NAME)
```

Replace `test_join_unknown_code_returns_none` with:

```python
async def test_join_unknown_code_raises_not_found():
    reg = Registry()
    with pytest.raises(JoinError) as err:
        await reg.join_room("NOPE-00", "Sam", {"body": "tall",
                                              "skin": "#a4673f"},
                            FakeConn().send)
    assert err.value.reason == ROOM_NOT_FOUND
```

Append:

```python
async def test_join_full_room_raises_full_and_sends_nothing():
    reg = Registry(max_members=2)
    a, b, c = FakeConn(), FakeConn(), FakeConn()
    code, _ = await reg.create_room("A", {}, a.send)
    await reg.join_room(code, "B", {}, b.send)
    sent_before = (len(a.sent), len(b.sent))

    with pytest.raises(JoinError) as err:
        await reg.join_room(code, "C", {}, c.send)

    assert err.value.reason == ROOM_FULL
    assert c.sent == []
    assert (len(a.sent), len(b.sent)) == sent_before
    assert len(reg.rooms[code]["members"]) == 2


async def test_default_room_cap_is_sixteen():
    reg = Registry()
    code, _ = await reg.create_room("host", {}, FakeConn().send)
    for i in range(15):
        await reg.join_room(code, f"p{i}", {}, FakeConn().send)
    with pytest.raises(JoinError):
        await reg.join_room(code, "one-too-many", {}, FakeConn().send)


async def test_names_are_cleaned_before_storing_and_forwarding():
    reg = Registry()
    a, b = FakeConn(), FakeConn()
    code, a_id = await reg.create_room("  " + "x" * 500, {}, a.send)
    b_id = await reg.join_room(code, 12345, {}, b.send)

    assert reg.rooms[code]["members"][a_id]["name"] == "x" * MAX_NAME
    assert a.sent[-1]["name"] == ""          # MEMBER_JOINED for the non-str name
    assert b.sent[0]["members"][0]["name"] == "x" * MAX_NAME
    assert reg.rooms[code]["members"][b_id]["name"] == ""


async def test_last_leave_logs_room_emptied(caplog):
    caplog.set_level("INFO", logger="relay")
    reg = Registry()
    code, mid = await reg.create_room("A", {}, FakeConn().send)
    await reg.leave(code, mid)
    assert f"room {code} emptied" in caplog.text
```

- [ ] **Step 3: Run to verify they fail**

Run: `python3 -m pytest tests/test_room.py -v`
Expected: collection error — `ImportError: cannot import name 'JoinError'`.

- [ ] **Step 4: Implement the registry changes**

In `relay/room.py`, replace the imports and add constants/helpers above `class Registry`:

```python
import logging
import random

from shared import messages as m

log = logging.getLogger("relay.room")

MAX_MEMBERS = 16
MAX_NAME = 20            # matches the client's validate_name limit
ROOM_NOT_FOUND = "Room not found"
ROOM_FULL = "Room is full"


class JoinError(Exception):
    """A join the relay refuses. `reason` is shown to the joining user."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def clean_name(name) -> str:
    """Peers can bypass the client's validation, so the relay enforces the
    same limit on everything it stores and forwards: non-strings become
    "", whitespace is stripped, and length is truncated (not rejected)."""
    if not isinstance(name, str):
        return ""
    return name.strip()[:MAX_NAME]
```

Change `Registry.__init__` to:

```python
    def __init__(self, max_members: int = MAX_MEMBERS):
        self.rooms: dict[str, dict] = {}   # code -> {"code", "members": {id -> member}}
        self._next_id = 0
        self.max_members = max_members
```

In `create_room`, add `name = clean_name(name)` as the first line of the body.

Replace `join_room` with:

```python
    async def join_room(self, code: str, name: str, appearance: dict, send
                        ) -> str:
        room = self.rooms.get(code)
        if room is None:
            raise JoinError(ROOM_NOT_FOUND)
        if len(room["members"]) >= self.max_members:
            raise JoinError(ROOM_FULL)
        name = clean_name(name)
        mid = self._new_member_id()
        await send(m.encode(m.ROOM_JOINED, your_id=mid, members=self._public(room)))
        room["members"][mid] = {"id": mid, "name": name,
                                "appearance": appearance, "send": send}
        for mem in room["members"].values():
            if mem["id"] != mid:
                await mem["send"](m.encode(m.MEMBER_JOINED, id=mid,
                                           name=name, appearance=appearance))
        return mid
```

In `leave`, replace the emptied branch with:

```python
        if not room["members"]:
            del self.rooms[code]
            log.info("room %s emptied", code)
            return
```

- [ ] **Step 5: Run registry tests**

Run: `python3 -m pytest tests/test_room.py -v`
Expected: all pass.

- [ ] **Step 6: Write failing server tests**

In `tests/test_server.py`, change the imports and fixture to use the real server config:

```python
import asyncio
import pytest
import websockets
from websockets.exceptions import ConnectionClosedError

from relay.room import Registry, ROOM_FULL, ROOM_NOT_FOUND
from relay.server import MAX_FRAME, make_handler, start_server
from shared import messages as m


async def _recv(ws):
    return m.decode(await asyncio.wait_for(ws.recv(), timeout=2))


@pytest.fixture
async def server():
    srv = await start_server("localhost", 0)
    port = srv.sockets[0].getsockname()[1]
    yield port
    srv.close()
    await srv.wait_closed()


@pytest.fixture
async def tiny_server():
    srv = await start_server("localhost", 0, Registry(max_members=1))
    yield srv.sockets[0].getsockname()[1]
    srv.close()
    await srv.wait_closed()
```

(Keep every existing test body unchanged; they use `server`, and `test_abrupt_disconnect_cleans_up_without_raising` still uses `make_handler` directly.) In `test_unknown_code_errors`, replace its last line with:

```python
        reply = await _recv(guest)
        assert reply == {"type": m.ERROR, "reason": ROOM_NOT_FOUND}
```

Append:

```python
async def test_full_room_gets_room_is_full(tiny_server):
    url = f"ws://localhost:{tiny_server}"
    async with websockets.connect(url) as host, websockets.connect(url) as guest:
        await host.send(m.encode(m.CREATE_ROOM, name="A", appearance={}))
        code = (await _recv(host))["code"]
        await guest.send(m.encode(m.JOIN_ROOM, code=code, name="B",
                                  appearance={}))
        assert await _recv(guest) == {"type": m.ERROR, "reason": ROOM_FULL}


async def test_oversized_frame_closes_connection(server):
    async with websockets.connect(f"ws://localhost:{server}",
                                  max_size=None) as ws:
        await ws.send("x" * (MAX_FRAME + 1))
        with pytest.raises(ConnectionClosedError):
            await asyncio.wait_for(ws.recv(), timeout=2)
        assert ws.close_code == 1009       # "message too big"


async def test_logs_codes_but_never_names_or_chat(server, caplog):
    caplog.set_level("INFO", logger="relay")
    url = f"ws://localhost:{server}"
    async with websockets.connect(url) as host, websockets.connect(url) as guest:
        await host.send(m.encode(m.CREATE_ROOM, name="SecretName",
                                 appearance={}))
        created = await _recv(host)
        await guest.send(m.encode(m.JOIN_ROOM, code=created["code"],
                                  name="OtherSecret", appearance={}))
        await _recv(guest)
        await _recv(host)
        await host.send(m.encode(m.CHAT, id=created["your_id"],
                                 text="private words"))
        await _recv(guest)

    await asyncio.sleep(0.1)     # let the handlers' finally-blocks log
    assert created["code"] in caplog.text
    for secret in ("SecretName", "OtherSecret", "private words"):
        assert secret not in caplog.text
```

- [ ] **Step 7: Run to verify they fail**

Run: `python3 -m pytest tests/test_server.py -v`
Expected: collection error — `ImportError: cannot import name 'MAX_FRAME'`.

- [ ] **Step 8: Implement the server changes**

Replace `relay/server.py` with:

```python
import asyncio
import logging
import os

import websockets
from websockets.exceptions import ConnectionClosed

from relay.room import JoinError, Registry
from shared import messages as m

log = logging.getLogger("relay.server")

# Every real message is a few hundred bytes; the library default (1 MiB)
# only helps someone trying to fill the relay's memory.
MAX_FRAME = 64 * 1024


def make_handler(registry: Registry):
    async def handler(websocket):
        code: str | None = None
        member_id: str | None = None

        async def send(raw: str) -> None:
            await websocket.send(raw)

        log.info("connection opened")
        try:
            async for raw in websocket:
                msg = m.decode(raw)
                if msg is None:
                    continue
                mtype = msg.get("type")

                if mtype == m.CREATE_ROOM and member_id is None:
                    code, member_id = await registry.create_room(
                        msg.get("name", ""), msg.get("appearance", {}), send)
                    log.info("room %s created by member %s", code, member_id)

                elif mtype == m.JOIN_ROOM and member_id is None:
                    requested = str(msg.get("code", ""))[:16]
                    try:
                        mid = await registry.join_room(
                            msg.get("code", ""), msg.get("name", ""),
                            msg.get("appearance", {}), send)
                    except JoinError as err:
                        log.info("join refused for room %s: %s",
                                 requested, err.reason)
                        await send(m.encode(m.ERROR, reason=err.reason))
                    else:
                        code, member_id = msg["code"], mid
                        log.info("member %s joined room %s", member_id, code)

                elif mtype in (m.STATE, m.CHAT, m.POKE) and member_id is not None:
                    await registry.relay(code, member_id, raw)
        except ConnectionClosed:
            pass   # a peer that vanished without a handshake is normal
        finally:
            if code is not None and member_id is not None:
                await registry.leave(code, member_id)
            log.info("connection closed (member %s, room %s)", member_id, code)

    return handler


async def start_server(host: str, port: int,
                       registry: Registry | None = None):
    """Start listening and return the server. Tests use this directly so
    they exercise the same limits production runs with."""
    if registry is None:
        registry = Registry()
    return await websockets.serve(make_handler(registry), host, port,
                                  max_size=MAX_FRAME)


async def serve(host: str, port: int) -> None:
    server = await start_server(host, port)
    log.info("Desktop Buddies relay listening on ws://%s:%s", host, port)
    await server.wait_closed()


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    host = os.environ.get("BUDDIES_HOST", "0.0.0.0")
    port = int(os.environ.get("BUDDIES_PORT", "8765"))
    asyncio.run(serve(host, port))
```

- [ ] **Step 9: Run the relay tests, then the whole suite**

Run: `python3 -m pytest tests/test_room.py tests/test_server.py -v`
Expected: all pass.
Run: `python3 -m pytest -q`
Expected: all pass.

- [ ] **Step 10: Manual check**

Run `python3 -m relay` in one terminal; expect a timestamped `relay.server: Desktop Buddies relay listening on ws://0.0.0.0:8765` line. Stop it with Ctrl-C.

- [ ] **Step 11: Commit**

```bash
git add relay/room.py relay/server.py tests/test_room.py tests/test_server.py requirements.txt pyproject.toml
git commit -m "feat: harden relay for the open internet

Cap rooms at 16 and frames at 64 KiB, clean peer-supplied names, and log
room lifecycle (codes and ids only) instead of printing.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Deploy the relay to Fly.io [USER]

**Files:**
- Create: `relay/Dockerfile`, `.dockerignore`, `fly.toml`

**Interfaces:**
- Consumes: `python -m relay` from Task 2.
- Produces: the public relay URL, `wss://desktop-buddies-relay.fly.dev` (or `wss://<actual-app-name>.fly.dev` — record the actual name; Task 4 uses it).

- [ ] **Step 1: Write the Dockerfile**

Create `relay/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir "websockets>=12,<13"

COPY shared/ shared/
COPY relay/ relay/

EXPOSE 8765
CMD ["python", "-m", "relay"]
```

Create `.dockerignore` at the repo root (the build context is the repo root, which includes `desktop-buddies/node_modules`):

```gitignore
*
!relay/
!shared/
**/__pycache__
```

- [ ] **Step 2: Write fly.toml**

Create `fly.toml` at the repo root:

```toml
# One always-on machine: rooms live in the relay's memory, so a second
# machine would split friends across processes, and a stopped machine
# drops everyone. Fly's proxy terminates TLS and forwards the WebSocket.
app = "desktop-buddies-relay"
primary_region = "iad"

[build]
  dockerfile = "relay/Dockerfile"

[env]
  BUDDIES_HOST = "0.0.0.0"
  BUDDIES_PORT = "8765"

[[services]]
  internal_port = 8765
  protocol = "tcp"
  auto_stop_machines = "off"
  auto_start_machines = true
  min_machines_running = 1

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [[services.tcp_checks]]
    interval = "15s"
    timeout = "2s"
    grace_period = "10s"

[[vm]]
  size = "shared-cpu-1x"
  memory = "256mb"
```

(A TCP check rather than an HTTP one: the relay only speaks WebSocket, and a plain GET would fail an HTTP check.)

- [ ] **Step 3: Build the image locally (if Docker is available)**

Run: `docker build -f relay/Dockerfile -t buddies-relay . && docker run --rm -p 8765:8765 buddies-relay`
Expected: the "listening" log line. Stop with Ctrl-C. If Docker isn't installed, skip; Fly builds remotely.

- [ ] **Step 4: Commit**

```bash
git add relay/Dockerfile .dockerignore fly.toml
git commit -m "feat: Fly.io deployment for the relay

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: [USER] Create the Fly app and deploy**

Ask the user to run these (they need a Fly account with a card on file; `fly auth login` opens a browser):

```bash
brew install flyctl
fly auth login
fly launch --no-deploy --copy-config --name desktop-buddies-relay
fly deploy --ha=false
fly scale count 1 --yes
fly status
```

If `fly launch` says the name is taken, pick another (e.g. `desktop-buddies-relay-kbc`), let it rewrite `app =` in `fly.toml`, and commit that change. If they want a region closer to them than `iad`, `fly launch` offers to change `primary_region`. Expected from `fly status`: exactly **one** machine, state `started`.

- [ ] **Step 6: Verify the public relay end to end**

Run (substituting the real app name):

```bash
python3 - <<'EOF'
import asyncio, json, websockets
async def main():
    async with websockets.connect("wss://desktop-buddies-relay.fly.dev") as ws:
        await ws.send(json.dumps({"type": "create_room", "name": "probe",
                                  "appearance": {}}))
        print(await asyncio.wait_for(ws.recv(), 10))
asyncio.run(main())
EOF
```

Expected: a `room_created` JSON line with a code like `PLUM-42`. Then `fly logs` shows `room PLUM-42 created by member 1` and no name.

---

### Task 4: Client defaults to the hosted relay, verifies TLS with certifi, finds sprites when frozen

**Files:**
- Create: `Src/resources.py`, `tests/test_resources.py`
- Modify: `Src/__main__.py`, `Src/Connections.py`, `Src/app.py`, `tests/test_connections.py`, `requirements.txt`, `pyproject.toml`, `run.sh`

**Interfaces:**
- Consumes: relay URL from Task 3.
- Produces:
  - `Src.resources.sprites_dir() -> pathlib.Path`
  - `Src.__main__.DEFAULT_RELAY_URL: str`, `Src.__main__.relay_url(env: Mapping[str, str]) -> str`, `Src.__main__.main(argv: list[str] | None = None) -> int`
  - `Src.Connections.ssl_context_for(url: str) -> ssl.SSLContext | None`

- [ ] **Step 1: Add certifi**

Append `certifi>=2024.2.2` to `requirements.txt`; add `"certifi>=2024.2.2"` to `pyproject.toml`'s `dependencies`. Run `python3 -m pip install -r requirements.txt`.

- [ ] **Step 2: Write failing tests**

Create `tests/test_resources.py`:

```python
import sys
from pathlib import Path

from Src.resources import sprites_dir

ROOT = Path(__file__).resolve().parent.parent


def test_source_checkout_uses_repo_sprites(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert sprites_dir() == ROOT / "Sprites"
    assert (sprites_dir() / "manifest.json").is_file()


def test_frozen_bundle_uses_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert sprites_dir() == tmp_path / "Sprites"
```

Append to `tests/test_connections.py`:

```python
import socket
import ssl
from pathlib import Path

import certifi

from Src.Connections import ssl_context_for
from Src.__main__ import DEFAULT_RELAY_URL, relay_url


def test_plain_ws_gets_no_ssl_context():
    assert ssl_context_for("ws://localhost:8765") is None


def test_wss_verifies_against_certifi():
    ctx = ssl_context_for("wss://example.fly.dev")
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname
    assert Path(certifi.where()).is_file()


def test_default_relay_is_hosted_wss():
    assert DEFAULT_RELAY_URL.startswith("wss://")
    assert relay_url({}) == DEFAULT_RELAY_URL
    assert relay_url({"BUDDIES_URL": "ws://localhost:8765"}) == \
        "ws://localhost:8765"


def test_unreachable_relay_reports_error_and_can_retry():
    with socket.socket() as s:            # grab a port nothing listens on
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url = f"ws://127.0.0.1:{port}"

    nc = NetClient()
    errors, drops = [], []
    nc.error_occurred.connect(errors.append)
    nc.disconnected.connect(lambda: drops.append(True))

    app = _app()
    nc.start_create(url, "Kain", {})
    nc._thread.join(timeout=15)
    app.processEvents()       # signals from the net thread may be queued
    assert errors and drops == [True]

    first = nc._thread
    nc.start_create(url, "Kain", {})       # a second click must try again
    assert nc._thread is not first
    nc._thread.join(timeout=15)
    app.processEvents()
    assert drops == [True, True]
```

- [ ] **Step 3: Run to verify they fail**

Run: `python3 -m pytest tests/test_resources.py tests/test_connections.py -v`
Expected: collection errors — `No module named 'Src.resources'` and `cannot import name 'ssl_context_for'`.

- [ ] **Step 4: Implement `Src/resources.py`**

```python
"""Where bundled data lives, in a source checkout or a PyInstaller build."""
import sys
from pathlib import Path


def sprites_dir() -> Path:
    """The `Sprites/` directory.

    PyInstaller unpacks data files under `sys._MEIPASS` and sets that
    attribute only in a frozen app; a source checkout keeps `Sprites/` at
    the repo root, next to `Src/`.
    """
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root) / "Sprites"
    return Path(__file__).resolve().parent.parent / "Sprites"
```

- [ ] **Step 5: Implement `ssl_context_for` in `Src/Connections.py`**

Add at the top with the other imports:

```python
import ssl

import certifi
```

Add after the imports, before `class NetClient`:

```python
def ssl_context_for(url: str) -> ssl.SSLContext | None:
    """TLS settings for a relay URL.

    A frozen app can't rely on the system CA store: the OpenSSL bundled with
    python.org/CI Pythons looks in its own build prefix, which doesn't exist
    on users' machines. certifi ships its CA bundle inside the app.
    """
    if not url.startswith("wss://"):
        return None
    return ssl.create_default_context(cafile=certifi.where())
```

In `_session`, change `async with websockets.connect(url) as ws:` to:

```python
        async with websockets.connect(url, ssl=ssl_context_for(url)) as ws:
```

- [ ] **Step 6: Implement `Src/__main__.py`**

Replace the file (use the real app name from Task 3 if it differs):

```python
import os
import sys
from collections.abc import Mapping

DEFAULT_RELAY_URL = "wss://desktop-buddies-relay.fly.dev"


def relay_url(env: Mapping[str, str]) -> str:
    """`BUDDIES_URL` overrides the hosted relay (self-hosting, local dev)."""
    return env.get("BUDDIES_URL") or DEFAULT_RELAY_URL


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--smoke-test" in argv:
        from Src.smoke import run_smoke_test
        return run_smoke_test()
    from Src.app import AppController
    return AppController(relay_url(os.environ)).run()


if __name__ == "__main__":
    raise SystemExit(main())
```

(`Src.smoke` arrives in Task 5; nothing calls that branch until then.)

- [ ] **Step 7: Use `sprites_dir()` in `Src/app.py`**

Replace `SPRITES_DIR = Path(__file__).resolve().parent.parent / "Sprites"` with:

```python
SPRITES_DIR = sprites_dir()
```

and add `from Src.resources import sprites_dir` to the `Src.` imports (alphabetically after `Src.profile`). Leave `from pathlib import Path` — `profile_path()` still uses it.

- [ ] **Step 8: Keep local dev off production**

`run.sh` already defaults `BUDDIES_URL` to `ws://localhost:8765`. In its `client)` branch, change the `exec` line to:

```bash
    exec env BUDDIES_URL="$BUDDIES_URL" \
      BUDDIES_NO_UPDATE_CHECK="${BUDDIES_NO_UPDATE_CHECK:-1}" "$PYTHON" -m Src
```

And in the header comment's "Env overrides" list add:

```bash
#   BUDDIES_NO_UPDATE_CHECK  1 skips the GitHub update check (default here: 1)
```

- [ ] **Step 9: Run tests**

Run: `python3 -m pytest -q`
Expected: all pass (the unreachable-relay test takes a second or two).

- [ ] **Step 10: Manual check against the hosted relay**

Run `python3 -m Src` (no `BUDDIES_URL`), create a room; expect a room code in the menu within a few seconds — this proves TLS verification works against Fly. Quit it.

- [ ] **Step 11: Commit**

```bash
git add Src/resources.py Src/__main__.py Src/Connections.py Src/app.py tests/test_resources.py tests/test_connections.py requirements.txt pyproject.toml run.sh
git commit -m "feat: default to the hosted relay with certifi-verified TLS

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: `--smoke-test` mode

**Files:**
- Create: `Src/smoke.py`, `tests/test_smoke_mode.py`

**Interfaces:**
- Consumes: `sprites_dir()` (Task 4), `VERSION` (Task 1), `load_manifest`, `resolve_layers`, `composite_frames`, `MenuWindow`.
- Produces: `Src.smoke.run_smoke_test() -> int` (0 ok, 1 failure); prints `desktop-buddies <VERSION> ok` on success.

- [ ] **Step 1: Write failing tests**

Create `tests/test_smoke_mode.py`:

```python
import os
import subprocess
import sys
from pathlib import Path

from Src.version import VERSION

ROOT = Path(__file__).resolve().parent.parent


def test_smoke_test_passes_on_a_good_checkout(capsys):
    from Src.smoke import run_smoke_test
    assert run_smoke_test() == 0
    assert f"desktop-buddies {VERSION} ok" in capsys.readouterr().out


def test_smoke_test_fails_without_sprites(monkeypatch, tmp_path, capsys):
    import Src.resources
    from Src.smoke import run_smoke_test
    monkeypatch.setattr(Src.resources, "sprites_dir", lambda: tmp_path)
    assert run_smoke_test() == 1
    assert "FAILED" in capsys.readouterr().err


def test_module_entry_point_runs_smoke_test():
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run([sys.executable, "-m", "Src", "--smoke-test"],
                            cwd=ROOT, env=env, capture_output=True,
                            text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert f"desktop-buddies {VERSION} ok" in result.stdout
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_smoke_mode.py -v`
Expected: FAIL — `No module named 'Src.smoke'`.

- [ ] **Step 3: Implement `Src/smoke.py`**

```python
"""`--smoke-test`: prove a build can start, without showing anything.

CI runs this against the *packaged* binary, so a data file or hidden import
PyInstaller missed fails the build instead of a user's first launch. It
touches everything a launch needs except the network.
"""
import os
import sys
from pathlib import Path

from Src.version import VERSION


def run_smoke_test() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv[:1])  # noqa: F841

        import certifi
        from Src import resources
        from Src.appearance import Appearance
        from Src.layers import load_manifest, resolve_layers
        from Src.menu import MenuWindow
        from Src.sprite_window import composite_frames

        root = resources.sprites_dir()
        manifest = load_manifest(root)
        layers = resolve_layers(Appearance(), root, manifest)
        for anim in ("idle", "walk"):
            if not composite_frames(layers, anim):
                raise RuntimeError(f"no {anim!r} frames under {root}")

        if not Path(certifi.where()).is_file():
            raise RuntimeError("certifi CA bundle missing")

        menu = MenuWindow(root)
        menu.close()
        menu.deleteLater()

        import Src.app  # noqa: F401  (pulls in every client module)
        if sys.platform == "darwin":
            import Src._hotkey_darwin  # noqa: F401
        elif sys.platform == "win32":
            import pynput.keyboard  # noqa: F401
        # Linux: pynput's X backend refuses to import without a display, and
        # the hotkey already degrades gracefully, so it isn't checked here.
    except Exception as exc:                          # noqa: BLE001
        print(f"desktop-buddies {VERSION} smoke test FAILED: {exc!r}",
              file=sys.stderr)
        return 1
    print(f"desktop-buddies {VERSION} ok")
    return 0
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_smoke_mode.py -v`
Expected: 3 passed. Then `python3 -m pytest -q` — all pass.

- [ ] **Step 5: Commit**

```bash
git add Src/smoke.py tests/test_smoke_mode.py
git commit -m "feat: --smoke-test mode for checking packaged builds

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Update check and version label

**Files:**
- Create: `Src/update_checker.py`, `tests/test_updates.py`, `tests/test_update_checker.py`
- Modify: `Src/updates.py`, `Src/menu.py`, `Src/app.py`, `tests/test_menu.py`

**Interfaces:**
- Consumes: `parse_version` (Task 1), `VERSION`.
- Produces:
  - `Src.updates.is_newer(latest: str, current: str) -> bool`
  - `Src.updates.latest_tag_from_json(body: bytes) -> str | None`
  - `Src.updates.RELEASES_API: str`, `Src.updates.DOWNLOAD_PAGE: str` (Task 11 changes `DOWNLOAD_PAGE` to the site)
  - `Src.update_checker.UpdateChecker(url: str = RELEASES_API, timeout_ms: int = 5000)` with signals `latest_found(str)` and `done()`, method `start()`
  - `MenuWindow.show_update(tag: str) -> None`, `MenuWindow.update_notice() -> str`

- [ ] **Step 1: Write failing pure tests**

Create `tests/test_updates.py`:

```python
import json

import pytest

from Src.updates import is_newer, latest_tag_from_json, parse_version


@pytest.mark.parametrize("tag, expected", [
    ("v1.2.3", (1, 2, 3)),
    ("1.2.3", (1, 2, 3)),
    (" v10.0.12 ", (10, 0, 12)),
    ("v1.2", None),
    ("v1.2.3-rc1", None),
    ("latest", None),
    ("", None),
    (None, None),
    (123, None),
])
def test_parse_version(tag, expected):
    assert parse_version(tag) == expected


def test_is_newer_compares_numerically():
    assert is_newer("v1.10.0", "1.9.0")
    assert is_newer("v2.0.0", "1.99.99")
    assert not is_newer("v1.0.0", "1.0.0")
    assert not is_newer("v0.9.0", "1.0.0")


def test_is_newer_is_false_for_garbage():
    assert not is_newer("nightly", "1.0.0")
    assert not is_newer("v2.0.0", "dev")


def test_latest_tag_from_json():
    assert latest_tag_from_json(json.dumps({"tag_name": "v1.1.0"}).encode()) \
        == "v1.1.0"
    assert latest_tag_from_json(b"not json") is None
    assert latest_tag_from_json(b"[]") is None
    assert latest_tag_from_json(json.dumps({"message": "Not Found"}).encode()) \
        is None
    assert latest_tag_from_json(json.dumps({"tag_name": 7}).encode()) is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_updates.py -v`
Expected: collection error — `cannot import name 'is_newer'`.

- [ ] **Step 3: Implement the pure functions**

Append to `Src/updates.py` (and add `import json` beside `import re`):

```python
RELEASES_API = \
    "https://api.github.com/repos/KainBC/Desktop-Buddies/releases/latest"
# Where "Download" in the update notice goes. The site picks the right
# installer for the OS and repeats the unsigned-app instructions.
DOWNLOAD_PAGE = "https://github.com/KainBC/Desktop-Buddies/releases/latest"


def is_newer(latest, current) -> bool:
    new, cur = parse_version(latest), parse_version(current)
    return new is not None and cur is not None and new > cur


def latest_tag_from_json(body: bytes) -> str | None:
    """`tag_name` from GitHub's latest-release JSON, or None if absent."""
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    tag = data.get("tag_name")
    return tag if isinstance(tag, str) else None
```

Run: `python3 -m pytest tests/test_updates.py -v` — expect all pass.

- [ ] **Step 4: Write failing Qt checker tests**

Create `tests/test_update_checker.py`:

```python
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from Src.update_checker import UpdateChecker  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def github():
    """A local stand-in for the GitHub API. Set `.status`/`.body`."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(server.status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(server.body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.status, server.body = 200, b"{}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()


def _run(url):
    _app()
    found = []
    checker = UpdateChecker(url, timeout_ms=3000)
    checker.latest_found.connect(found.append)
    loop = QEventLoop()
    checker.done.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)
    checker.start()
    loop.exec()
    return found


def _url(server):
    return f"http://127.0.0.1:{server.server_address[1]}/latest"


def test_reports_latest_tag(github):
    github.body = json.dumps({"tag_name": "v1.4.0"}).encode()
    assert _run(_url(github)) == ["v1.4.0"]


@pytest.mark.parametrize("status", [404, 403, 500])
def test_http_errors_are_silent(github, status):
    github.status = status
    github.body = json.dumps({"message": "nope"}).encode()
    assert _run(_url(github)) == []


def test_bad_json_is_silent(github):
    github.body = b"<html>"
    assert _run(_url(github)) == []


def test_unreachable_host_is_silent():
    assert _run("http://127.0.0.1:9/latest") == []
```

- [ ] **Step 5: Run to verify they fail**

Run: `python3 -m pytest tests/test_update_checker.py -v`
Expected: FAIL — `No module named 'Src.update_checker'`.

- [ ] **Step 6: Implement `Src/update_checker.py`**

```python
"""Ask GitHub, once, what the newest release is.

Asynchronous on Qt's event loop (no thread), and silent on every failure:
the only visible outcome is `latest_found` firing with a tag. `done` always
fires exactly once, which is what tests wait on.
"""
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import (QNetworkAccessManager, QNetworkReply,
                               QNetworkRequest)

from Src.updates import RELEASES_API, latest_tag_from_json
from Src.version import VERSION


class UpdateChecker(QObject):
    latest_found = Signal(str)
    done = Signal()

    def __init__(self, url: str = RELEASES_API, timeout_ms: int = 5000):
        super().__init__()
        self._url = url
        self._timeout_ms = timeout_ms
        self._manager = QNetworkAccessManager(self)
        self._reply: QNetworkReply | None = None

    def start(self) -> None:
        request = QNetworkRequest(QUrl(self._url))
        request.setTransferTimeout(self._timeout_ms)
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"User-Agent",
                             f"desktop-buddies/{VERSION}".encode())
        self._reply = self._manager.get(request)
        self._reply.finished.connect(self._on_finished)

    def _on_finished(self) -> None:
        reply, self._reply = self._reply, None
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                tag = latest_tag_from_json(bytes(reply.readAll()))
                if tag:
                    self.latest_found.emit(tag)
        finally:
            reply.deleteLater()
            self.done.emit()
```

Run: `python3 -m pytest tests/test_update_checker.py -v` — expect all pass. (Qt reports HTTP 4xx/5xx as a reply error, which is why those are silent.)

- [ ] **Step 7: Write failing menu tests**

Append to `tests/test_menu.py`:

```python
def test_menu_shows_the_running_version():
    _qt_app()
    from PySide6.QtWidgets import QLabel
    from Src.menu import MenuWindow
    from Src.version import VERSION

    w = MenuWindow(SPRITES_DIR)
    try:
        texts = [label.text() for label in w.findChildren(QLabel)]
        assert f"v{VERSION}" in texts
    finally:
        w.close()
        w.deleteLater()


def test_update_notice_only_for_a_newer_release():
    _qt_app()
    from Src.menu import MenuWindow
    from Src.updates import DOWNLOAD_PAGE

    w = MenuWindow(SPRITES_DIR)
    try:
        assert w.update_notice() == ""
        for tag in ("v1.0.0", "v0.9.0", "garbage", "v9.9.9-beta"):
            w.show_update(tag)
            assert w.update_notice() == "", tag
        w.show_update("v9.10.0")
        notice = w.update_notice()
        assert "v9.10.0" in notice
        assert DOWNLOAD_PAGE in notice
    finally:
        w.close()
        w.deleteLater()
```

(The first loop assumes `VERSION == "1.0.0"`; that holds for this release.)

- [ ] **Step 8: Run to verify they fail**

Run: `python3 -m pytest tests/test_menu.py -v`
Expected: FAIL — no `v1.0.0` label; `AttributeError: ... 'update_notice'`.

- [ ] **Step 9: Implement the menu changes**

In `Src/menu.py`, change the imports to:

```python
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel)

from Src.appearance import Appearance
from Src.customizer import CustomizerPanel
from Src.updates import DOWNLOAD_PAGE, is_newer, parse_version
from Src.version import VERSION
```

At the end of `MenuWindow.__init__` (after `layout.addWidget(self._status)`), add:

```python
        self._version = QLabel(f"v{VERSION}")
        self._version.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._version)

        self._update = QLabel("")
        self._update.setTextFormat(Qt.RichText)
        self._update.setOpenExternalLinks(True)
        self._update.setStyleSheet("color: gray; font-size: 11px;")
        self._update.hide()
        layout.addWidget(self._update)
```

Add methods to `MenuWindow`:

```python
    def show_update(self, tag: str) -> None:
        """Show the update line if `tag` is a newer release than this build.

        The tag comes off the network, so only its parsed numbers are ever
        rendered -- never the raw string -- into this rich-text label.
        """
        if not is_newer(tag, VERSION):
            return
        shown = "v" + ".".join(str(n) for n in parse_version(tag))
        self._update.setText(
            f'Update available: {shown} — <a href="{DOWNLOAD_PAGE}">Download</a>')
        self._update.show()

    def update_notice(self) -> str:
        return "" if self._update.isHidden() else self._update.text()
```

Run: `python3 -m pytest tests/test_menu.py -v` — expect all pass.

- [ ] **Step 10: Wire the checker in `Src/app.py`**

Add `from Src.update_checker import UpdateChecker` to the `Src.` imports (after `Src.sprite_window`). At the end of `AppController.__init__` (after the timer is connected), add:

```python
        self.updates: UpdateChecker | None = None
        if os.environ.get("BUDDIES_NO_UPDATE_CHECK") != "1":
            self.updates = UpdateChecker()
            self.updates.latest_found.connect(self.menu.show_update)
```

Change `run` to:

```python
    def run(self) -> int:
        self.menu.show()
        if self.updates is not None:
            self.updates.start()   # async; never delays create/join
        return self.app.exec()
```

- [ ] **Step 11: Run everything; manual check**

Run: `python3 -m pytest -q` — all pass.
Manual: `python3 -m Src` — the menu shows `v1.0.0` and no update line (no release exists yet, so GitHub answers 404). Quit.

- [ ] **Step 12: Commit**

```bash
git add Src/updates.py Src/update_checker.py Src/menu.py Src/app.py tests/test_updates.py tests/test_update_checker.py tests/test_menu.py
git commit -m "feat: version label and GitHub-Releases update notice in the menu

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: App icon and PyInstaller spec (local macOS build)

**Files:**
- Create: `tools/make_icons.py`, `packaging/icons/buddy.png`, `packaging/launch.py`, `packaging/buddies.spec`

**Interfaces:**
- Consumes: `Src.__main__.main` (Task 4), `--smoke-test` (Task 5), `VERSION`.
- Produces: `pyinstaller --noconfirm --clean packaging/buddies.spec` → `dist/DesktopBuddies/` (one-dir; executable `DesktopBuddies`/`DesktopBuddies.exe`) and, on macOS, `dist/Desktop Buddies.app` (executable `Contents/MacOS/DesktopBuddies`).

Note (deviation from spec §3 "Icons"): only the PNG is committed. PyInstaller converts it to `.icns`/`.ico` itself when Pillow is installed, which removes the need for platform icon tooling.

- [ ] **Step 1: Write the icon generator**

Create `tools/make_icons.py`:

```python
"""Render the default buddy to packaging/icons/buddy.png for the app icon.

PyInstaller converts this PNG to .icns (macOS) and .ico (Windows) at build
time via Pillow, so the PNG is the only icon file committed. Re-run after
changing the body or face art.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from Src.appearance import Appearance  # noqa: E402
from Src.layers import resolve_layers  # noqa: E402
from Src.sprite_window import composite_frames  # noqa: E402

OUT = ROOT / "packaging" / "icons" / "buddy.png"
SIZE = 512


def main() -> int:
    app = QApplication.instance() or QApplication([])  # noqa: F841
    frames = composite_frames(resolve_layers(Appearance(), ROOT / "Sprites"),
                              "idle")
    if not frames:
        print("no idle frames for the default appearance", file=sys.stderr)
        return 1
    # Nearest-neighbour keeps the pixel art crisp at icon size.
    icon = frames[0].scaled(SIZE, SIZE, Qt.KeepAspectRatio,
                            Qt.FastTransformation)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not icon.save(str(OUT), "PNG"):
        print(f"could not write {OUT}", file=sys.stderr)
        return 1
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Run: `python3 tools/make_icons.py`
Expected: `wrote .../packaging/icons/buddy.png`. Open it and confirm it shows the round buddy with a face.

- [ ] **Step 2: Write the entry script and spec**

Create `packaging/launch.py`:

```python
"""PyInstaller entry point: PyInstaller needs a script, not `python -m`."""
from Src.__main__ import main

raise SystemExit(main())
```

Create `packaging/buddies.spec`:

```python
# PyInstaller spec for Desktop Buddies. Build from the repo root:
#   pyinstaller --noconfirm --clean packaging/buddies.spec
# One-dir (not one-file): faster start, fewer antivirus false positives,
# and required for a macOS .app bundle.
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent            # noqa: F821 (SPECPATH is injected)
sys.path.insert(0, str(ROOT))
from Src.version import VERSION        # noqa: E402

hidden = []
if sys.platform.startswith("linux"):
    hidden += ["pynput.keyboard._xorg", "pynput.mouse._xorg"]
elif sys.platform == "win32":
    hidden += ["pynput.keyboard._win32", "pynput.mouse._win32"]

icon = str(ROOT / "packaging" / "icons" / "buddy.png")

a = Analysis(                           # noqa: F821
    [str(ROOT / "packaging" / "launch.py")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "Sprites"), "Sprites")],
    hiddenimports=hidden,
    excludes=["pytest", "tkinter"],
)
pyz = PYZ(a.pure)                       # noqa: F821
exe = EXE(                              # noqa: F821
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="DesktopBuddies",
    console=False,
    icon=icon,
)
coll = COLLECT(exe, a.binaries, a.datas, name="DesktopBuddies")  # noqa: F821

if sys.platform == "darwin":
    app = BUNDLE(                       # noqa: F821
        coll,
        name="Desktop Buddies.app",
        icon=icon,
        bundle_identifier="io.github.kainbc.desktopbuddies",
        info_plist={
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "NSHighResolutionCapable": True,
        },
    )
```

- [ ] **Step 3: Build locally**

```bash
python3 -m pip install "pyinstaller>=6.10,<7" "pillow>=10"
pyinstaller --noconfirm --clean packaging/buddies.spec
```

Expected: ends with `Build complete!`; `dist/Desktop Buddies.app` exists.

- [ ] **Step 4: Smoke-test the built binary**

Run: `QT_QPA_PLATFORM=offscreen "dist/Desktop Buddies.app/Contents/MacOS/DesktopBuddies" --smoke-test; echo "exit=$?"`
Expected: `desktop-buddies 1.0.0 ok` and `exit=0`. If it fails with a missing module or file, add it to `hiddenimports`/`datas` in the spec and rebuild.

- [ ] **Step 5: Launch the real app**

Run: `open "dist/Desktop Buddies.app"`. Expected: the launch menu (with `v1.0.0`) appears with the buddy icon in the Dock; creating a room against the hosted relay shows a code and a sprite. Press ⌘⇧B and confirm the chat composer opens (checks the Carbon hotkey survived bundling). Quit.

- [ ] **Step 6: Commit**

```bash
git add tools/make_icons.py packaging/icons/buddy.png packaging/launch.py packaging/buddies.spec
git commit -m "feat: PyInstaller spec and app icon

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Windows installer and Linux AppImage packaging files

**Files:**
- Create: `packaging/windows.iss`, `packaging/linux/AppRun`, `packaging/linux/desktop-buddies.desktop`, `packaging/linux/build_appimage.sh`, `tests/test_packaging.py`

**Interfaces:**
- Consumes: `dist/DesktopBuddies/` from the spec (Task 7).
- Produces: `out/DesktopBuddies-windows-setup.exe` (via `iscc /DAppVersion=<VERSION> packaging\windows.iss`), `out/DesktopBuddies-linux-x86_64.AppImage` (via `bash packaging/linux/build_appimage.sh`); `tests/test_packaging.py::ARTIFACTS`.

- [ ] **Step 1: Write the failing packaging test**

Create `tests/test_packaging.py`:

```python
"""The artifact names are a contract between CI, the packaging scripts, and
the website's download links. These tests fail if any side drifts."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ARTIFACTS = [
    "DesktopBuddies-mac-arm64.dmg",
    "DesktopBuddies-mac-x64.dmg",
    "DesktopBuddies-windows-setup.exe",
    "DesktopBuddies-linux-x86_64.AppImage",
]


def test_inno_setup_output_name():
    iss = (ROOT / "packaging" / "windows.iss").read_text()
    assert "OutputBaseFilename=DesktopBuddies-windows-setup" in iss
    assert "PrivilegesRequired=lowest" in iss


def test_appimage_output_name_and_x11_default():
    script = (ROOT / "packaging" / "linux" / "build_appimage.sh").read_text()
    assert "out/DesktopBuddies-linux-x86_64.AppImage" in script
    apprun = ROOT / "packaging" / "linux" / "AppRun"
    assert 'QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"' in apprun.read_text()
    assert os.access(apprun, os.X_OK)
```

Run: `python3 -m pytest tests/test_packaging.py -v`
Expected: FAIL — `FileNotFoundError` for `windows.iss`.

- [ ] **Step 2: Write the Inno Setup script**

Create `packaging/windows.iss`:

```ini
; Inno Setup script. Build from the repo root after PyInstaller:
;   iscc /DAppVersion=1.0.0 packaging\windows.iss
; Paths are relative to this file. Per-user install: no admin prompt.

[Setup]
AppId={{8F1C2A57-3D4B-4E8A-9C61-5B7E2D9A4F10}
AppName=Desktop Buddies
AppVersion={#AppVersion}
AppPublisher=KainBC
AppPublisherURL=https://github.com/KainBC/Desktop-Buddies
DefaultDirName={localappdata}\Programs\Desktop Buddies
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\out
OutputBaseFilename=DesktopBuddies-windows-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\DesktopBuddies.exe
UninstallDisplayName=Desktop Buddies

[Files]
Source: "..\dist\DesktopBuddies\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{userprograms}\Desktop Buddies"; Filename: "{app}\DesktopBuddies.exe"

[Run]
Filename: "{app}\DesktopBuddies.exe"; Description: "Launch Desktop Buddies"; Flags: nowait postinstall skipifsilent
```

(The `AppId` GUID must never change between releases — it is how upgrades replace the old install.)

- [ ] **Step 3: Write the Linux files**

Create `packaging/linux/AppRun`:

```sh
#!/bin/sh
# Force X11 (XWayland on Wayland desktops): Wayland forbids the always-on-top
# and absolute window positioning the buddies rely on. Respect an explicit
# choice, e.g. QT_QPA_PLATFORM=offscreen for the CI smoke test.
HERE="$(dirname "$(readlink -f "$0")")"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
exec "$HERE/usr/DesktopBuddies" "$@"
```

Then: `chmod +x packaging/linux/AppRun` (git records the executable bit).

Create `packaging/linux/desktop-buddies.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Desktop Buddies
Comment=Your friends, as desktop pets
Exec=DesktopBuddies
Icon=desktop-buddies
Categories=Game;
```

Create `packaging/linux/build_appimage.sh`:

```bash
#!/usr/bin/env bash
# Assemble dist/DesktopBuddies (PyInstaller one-dir) into an AppImage.
# Run from anywhere after `pyinstaller packaging/buddies.spec` on Linux.
set -euo pipefail
cd "$(dirname "$0")/../.."

APPDIR=build/AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr" out
cp -R dist/DesktopBuddies/. "$APPDIR/usr/"
install -m 755 packaging/linux/AppRun "$APPDIR/AppRun"
cp packaging/linux/desktop-buddies.desktop "$APPDIR/"
cp packaging/icons/buddy.png "$APPDIR/desktop-buddies.png"

TOOL=build/appimagetool-x86_64.AppImage
if [ ! -x "$TOOL" ]; then
  curl -fsSL -o "$TOOL" \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi
# CI runners have no FUSE; extract-and-run avoids needing it.
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" "$APPDIR" \
  out/DesktopBuddies-linux-x86_64.AppImage
```

Then: `chmod +x packaging/linux/build_appimage.sh`.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_packaging.py -v` — expect 2 passed.

- [ ] **Step 5: Commit**

```bash
git add packaging/windows.iss packaging/linux tests/test_packaging.py
git commit -m "feat: Inno Setup installer and AppImage packaging

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Release workflow

**Files:**
- Create: `.github/workflows/release.yml`
- Modify: `tests/test_packaging.py`

**Interfaces:**
- Consumes: spec (Task 7), `windows.iss` and `build_appimage.sh` (Task 8), `--smoke-test` (Task 5), `VERSION`.
- Produces: on `v*` tag, a GitHub Release with the four `ARTIFACTS` + `SHA256SUMS.txt`, marked latest.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_packaging.py`:

```python
def test_workflow_builds_every_artifact():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    for name in ARTIFACTS:
        assert f"artifact: {name}" in workflow, name
    assert "--smoke-test" in workflow
    assert "SHA256SUMS.txt" in workflow
```

Run: `python3 -m pytest tests/test_packaging.py -v` — expect FAIL (`FileNotFoundError`).

- [ ] **Step 2: Write the workflow**

Create `.github/workflows/release.yml`:

```yaml
name: release

# Tag vX.Y.Z (matching Src/version.py) to publish a release. PRs that touch
# packaging, and manual runs, build and smoke-test without publishing.
on:
  push:
    tags: ["v*"]
  pull_request:
    paths:
      - "packaging/**"
      - ".github/workflows/release.yml"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  check:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Tag matches VERSION
        if: startsWith(github.ref, 'refs/tags/')
        run: |
          version=$(python -c "from Src.version import VERSION; print(VERSION)")
          if [ "$GITHUB_REF_NAME" != "v$version" ]; then
            echo "::error::tag $GITHUB_REF_NAME does not match Src/version.py (v$version)"
            exit 1
          fi
      - name: Qt system libraries
        run: |
          sudo apt-get update
          sudo apt-get install -y libegl1 libgl1 libxkbcommon0 \
            libxkbcommon-x11-0 libxcb-cursor0 libfontconfig1 libdbus-1-3
      - run: python -m pip install -r requirements.txt
      - name: Tests
        env:
          QT_QPA_PLATFORM: offscreen
        run: python -m pytest -q

  build:
    needs: check
    strategy:
      fail-fast: false
      matrix:
        include:
          - target: mac-arm64
            os: macos-14
            artifact: DesktopBuddies-mac-arm64.dmg
          - target: mac-x64
            os: macos-15-intel
            artifact: DesktopBuddies-mac-x64.dmg
          - target: windows
            os: windows-latest
            artifact: DesktopBuddies-windows-setup.exe
          - target: linux
            os: ubuntu-22.04
            artifact: DesktopBuddies-linux-x86_64.AppImage
    runs-on: ${{ matrix.os }}
    env:
      QT_QPA_PLATFORM: offscreen
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Linux system libraries
        if: matrix.target == 'linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y libegl1 libgl1 libxkbcommon0 \
            libxkbcommon-x11-0 libxcb-cursor0 libfontconfig1 libdbus-1-3
      - name: Install build dependencies
        run: python -m pip install -r requirements.txt "pyinstaller>=6.10,<7" "pillow>=10"
      - name: PyInstaller
        run: pyinstaller --noconfirm --clean packaging/buddies.spec

      # ---- macOS ----
      - name: Smoke test (macOS)
        if: startsWith(matrix.target, 'mac')
        run: '"dist/Desktop Buddies.app/Contents/MacOS/DesktopBuddies" --smoke-test'
      - name: Package dmg
        if: startsWith(matrix.target, 'mac')
        run: |
          mkdir -p out build/dmg
          cp -R "dist/Desktop Buddies.app" build/dmg/
          ln -s /Applications build/dmg/Applications
          hdiutil create -volname "Desktop Buddies" -srcfolder build/dmg \
            -ov -format UDZO "out/${{ matrix.artifact }}"
      # (future: codesign + notarytool here)

      # ---- Windows ----
      - name: Smoke test (Windows)
        if: matrix.target == 'windows'
        shell: pwsh
        run: |
          $p = Start-Process -FilePath "dist\DesktopBuddies\DesktopBuddies.exe" `
            -ArgumentList "--smoke-test" -Wait -PassThru -NoNewWindow
          if ($p.ExitCode -ne 0) { exit $p.ExitCode }
      - name: Package installer
        if: matrix.target == 'windows'
        shell: pwsh
        run: |
          choco install innosetup --no-progress -y
          $version = python -c "from Src.version import VERSION; print(VERSION)"
          & "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" "/DAppVersion=$version" packaging\windows.iss
      # (future: signtool here)

      # ---- Linux ----
      - name: Package AppImage
        if: matrix.target == 'linux'
        run: bash packaging/linux/build_appimage.sh
      - name: Smoke test (AppImage)
        if: matrix.target == 'linux'
        env:
          APPIMAGE_EXTRACT_AND_RUN: "1"
        run: ./out/${{ matrix.artifact }} --smoke-test

      - name: Artifact exists
        shell: bash
        run: test -f "out/${{ matrix.artifact }}"
      - uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.target }}
          path: out/${{ matrix.artifact }}
          if-no-files-found: error

  release:
    needs: build
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: out
          merge-multiple: true
      - name: Checksums
        run: cd out && sha256sum * > SHA256SUMS.txt && cat SHA256SUMS.txt
      - uses: softprops/action-gh-release@v2
        with:
          name: Desktop Buddies ${{ github.ref_name }}
          make_latest: "true"
          files: out/*
```

- [ ] **Step 3: Run tests**

Run: `python3 -m pytest tests/test_packaging.py -v` — expect all pass.

- [ ] **Step 4: Commit and exercise the build on a PR (confirm with the user before pushing)**

```bash
git add .github/workflows/release.yml tests/test_packaging.py
git commit -m "ci: build, smoke-test and release installers on tag

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Ask the user: "OK to push `public-release` and open a draft PR so CI builds all four installers?" On yes:

```bash
git push -u origin public-release
gh pr create --draft --base main --title "Public release v1.0.0" \
  --body "Hosted relay, installers, update notice, live site downloads.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh run watch
```

Expected: `check` and all four `build` jobs green; `release` is skipped (not a tag). If a build fails, read its log (`gh run view --log-failed`), fix, push, repeat.

- [ ] **Step 5: Try a CI build by hand on this Mac**

Download the arm64 artifact: `gh run download --name mac-arm64 --dir /tmp/buddies-ci`. Open the dmg, drag the app to a scratch folder (not /Applications if a copy exists), double-click it, and follow the Open Anyway flow. Record the exact wording macOS shows and the exact steps — Task 10's macOS steps must match them. Confirm the app launches.

---

### Task 10: Website — live downloads and first-launch instructions

**Files:**
- Modify: `desktop-buddies/lib/downloads.ts`, `desktop-buddies/components/DownloadButton.tsx`, `desktop-buddies/app/download/page.tsx`, `desktop-buddies/components/Steps.tsx`, `desktop-buddies/app/page.tsx`, `tests/test_packaging.py`
- Create: `desktop-buddies/lib/downloads.test.ts`

**Interfaces:**
- Consumes: `ARTIFACTS` names (Tasks 8–9).
- Produces: `RELEASE_BASE`, `CHECKSUMS_URL`, `Build` (with `variant?: string`, `steps: string[]`), `BUILDS`, `primaryBuild(platform: Platform | null): Build | undefined`, `buildName(build: Build): string`.

- [ ] **Step 1: Write the failing vitest**

Create `desktop-buddies/lib/downloads.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  BUILDS,
  CHECKSUMS_URL,
  RELEASE_BASE,
  buildName,
  primaryBuild,
} from "./downloads";

// Must equal ARTIFACTS in tests/test_packaging.py and the `artifact:` names
// in .github/workflows/release.yml.
const ARTIFACTS = [
  "DesktopBuddies-mac-arm64.dmg",
  "DesktopBuddies-mac-x64.dmg",
  "DesktopBuddies-windows-setup.exe",
  "DesktopBuddies-linux-x86_64.AppImage",
];

describe("BUILDS", () => {
  it("downloads every build from the latest release", () => {
    for (const build of BUILDS) {
      expect(build.url).not.toBeNull();
      expect(build.url!.startsWith(`${RELEASE_BASE}/`)).toBe(true);
    }
  });

  it("ships exactly the artifacts CI produces", () => {
    const files = BUILDS.map((b) => b.url!.slice(RELEASE_BASE.length + 1));
    expect([...files].sort()).toEqual([...ARTIFACTS].sort());
  });

  it("gives every build first-launch steps", () => {
    for (const build of BUILDS) expect(build.steps.length).toBeGreaterThan(0);
  });

  it("tells Linux users the AppImage is x86_64 only", () => {
    const linux = primaryBuild("linux")!;
    expect(linux.steps.join(" ")).toMatch(/x86_64/);
  });

  it("links the checksums", () => {
    expect(CHECKSUMS_URL).toBe(`${RELEASE_BASE}/SHA256SUMS.txt`);
  });
});

describe("primaryBuild", () => {
  it("offers Apple Silicon to macOS (userAgent can't tell the chip)", () => {
    expect(primaryBuild("macos")?.variant).toBe("Apple Silicon");
  });

  it("finds Windows and Linux", () => {
    expect(primaryBuild("windows")?.file).toBe(".exe");
    expect(primaryBuild("linux")?.file).toBe("AppImage");
  });

  it("offers nothing for an unknown platform", () => {
    expect(primaryBuild(null)).toBeUndefined();
  });
});

describe("buildName", () => {
  it("includes the variant when there is one", () => {
    const intel = BUILDS.find((b) => b.variant === "Intel")!;
    expect(buildName(intel)).toBe("macOS (Intel)");
    expect(buildName(primaryBuild("windows")!)).toBe("Windows");
  });
});
```

Run: `cd desktop-buddies && npm test`
Expected: FAIL — `RELEASE_BASE`/`primaryBuild` not exported.

- [ ] **Step 2: Implement `lib/downloads.ts`**

Replace the file. **Use the exact macOS wording recorded in Task 9 Step 5** if it differs from the text below:

```ts
import type { Platform } from "./os";

/**
 * Every build the site offers.
 *
 * URLs use GitHub's `releases/latest/download/<file>` redirect and the
 * artifact names carry no version, so these never change per release. The
 * names are a contract with .github/workflows/release.yml, checked by
 * downloads.test.ts and tests/test_packaging.py.
 */
export const RELEASE_BASE =
  "https://github.com/KainBC/Desktop-Buddies/releases/latest/download";

export const CHECKSUMS_URL = `${RELEASE_BASE}/SHA256SUMS.txt`;

export interface Build {
  platform: Platform;
  label: string;
  /** Distinguishes builds that share a platform, e.g. the two Macs. */
  variant?: string;
  file: string;
  /** `null` renders as a disabled "Coming soon" row. */
  url: string | null;
  /** First-launch instructions: the builds are unsigned. */
  steps: string[];
}

const MAC_STEPS = [
  "Open the .dmg and drag Desktop Buddies into Applications.",
  "Open Desktop Buddies. macOS says it can't verify the app — click Done.",
  "Open System Settings → Privacy & Security, scroll down, and click Open Anyway next to Desktop Buddies.",
  "Confirm with Open Anyway and your password. After this it opens normally.",
];

const WINDOWS_STEPS = [
  "Run DesktopBuddies-windows-setup.exe.",
  "If SmartScreen says “Windows protected your PC”, click More info, then Run anyway.",
  "Finish the installer. Desktop Buddies is in your Start menu.",
];

const LINUX_STEPS = [
  "This AppImage is for x86_64 PCs only (not ARM).",
  "Make it executable: chmod +x DesktopBuddies-linux-x86_64.AppImage",
  "Run it: ./DesktopBuddies-linux-x86_64.AppImage",
  "Needs a desktop with a compositor so buddies can be transparent. On Wayland it runs through XWayland.",
];

export const BUILDS: Build[] = [
  {
    platform: "macos",
    label: "macOS",
    variant: "Apple Silicon",
    file: ".dmg",
    url: `${RELEASE_BASE}/DesktopBuddies-mac-arm64.dmg`,
    steps: MAC_STEPS,
  },
  {
    platform: "macos",
    label: "macOS",
    variant: "Intel",
    file: ".dmg",
    url: `${RELEASE_BASE}/DesktopBuddies-mac-x64.dmg`,
    steps: MAC_STEPS,
  },
  {
    platform: "windows",
    label: "Windows",
    file: ".exe",
    url: `${RELEASE_BASE}/DesktopBuddies-windows-setup.exe`,
    steps: WINDOWS_STEPS,
  },
  {
    platform: "linux",
    label: "Linux",
    file: "AppImage",
    url: `${RELEASE_BASE}/DesktopBuddies-linux-x86_64.AppImage`,
    steps: LINUX_STEPS,
  },
];

/** The build the big button offers: the first one listed for the platform. */
export function primaryBuild(platform: Platform | null): Build | undefined {
  if (platform === null) return undefined;
  return BUILDS.find((b) => b.platform === platform);
}

export function buildName(build: Build): string {
  return build.variant ? `${build.label} (${build.variant})` : build.label;
}
```

Run: `npm test` — expect all pass (including the existing `os`, `buddy`, `characters` tests).

- [ ] **Step 3: Update `DownloadButton.tsx`**

Replace the imports and the `DownloadButton` function body (keep the `subscribe`/`clientPlatform`/`serverPlatform` helpers and their comments exactly as they are):

```tsx
"use client";

import { useSyncExternalStore } from "react";
import { BUILDS, primaryBuild } from "@/lib/downloads";
import { detectPlatform, type Platform } from "@/lib/os";
```

```tsx
export default function DownloadButton() {
  const platform = useSyncExternalStore(
    subscribe,
    clientPlatform,
    serverPlatform,
  );

  const build = primaryBuild(platform);
  const href = build?.url ?? "#all-platforms";
  const label = build ? `Download for ${build.label}` : "Download";
  const intel =
    platform === "macos"
      ? BUILDS.find((b) => b.platform === "macos" && b.variant === "Intel")
      : undefined;

  return (
    <div className="flex flex-col items-center gap-2">
      <a
        href={href}
        className="rounded-md bg-accent px-6 py-3 font-medium text-accent-contrast hover:opacity-90"
      >
        {label}
      </a>
      <span className="text-sm text-muted">
        {build ? (
          <>
            Unsigned app — the first launch needs one extra click.{" "}
            <a href="#first-launch" className="underline hover:text-foreground">
              How?
            </a>
          </>
        ) : (
          "macOS, Windows and Linux — pick yours below."
        )}
      </span>
      {intel?.url ? (
        <a
          href={intel.url}
          className="text-sm text-muted underline hover:text-foreground"
        >
          Intel Mac?
        </a>
      ) : null}
    </div>
  );
}
```

Also update the component's doc comment line "The OS-labelled primary CTA." to "The OS-labelled primary download link." (Server render: `platform` is `null`, so it renders the neutral `#all-platforms` link — the no-hydration-mismatch property is unchanged.)

- [ ] **Step 4: Update `app/download/page.tsx`**

Change the imports to:

```tsx
import { BUILDS, CHECKSUMS_URL, buildName, primaryBuild } from "@/lib/downloads";
```

Change `metadata.description` to:

```tsx
  description:
    "Download Desktop Buddies for macOS, Windows or Linux.",
```

In the "All platforms" section: add `id="all-platforms"` to its `<section>`, change `key={build.platform}` to `key={buildName(build)}`, and change `<span className="font-medium">{build.label}</span>` to `<span className="font-medium">{buildName(build)}</span>`.

Insert this section after "All platforms" and before "Run from source":

```tsx
        <section id="first-launch" className="pt-12">
          <h2 className="mb-4 text-xl font-semibold">First launch</h2>
          <p className="mb-6 text-muted">
            The apps aren&apos;t code-signed yet — signing certificates cost
            money, and the source is public on GitHub — so your OS asks you to
            confirm the first time. After that it opens like any other app.
          </p>
          <div className="grid gap-6 sm:grid-cols-3">
            {(["macos", "windows", "linux"] as const).map((platform) => {
              const build = primaryBuild(platform)!;
              return (
                <div key={platform}>
                  <h3 className="mb-2 font-semibold">{build.label}</h3>
                  <ol className="list-decimal space-y-1 pl-5 text-sm text-muted">
                    {build.steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </div>
              );
            })}
          </div>
          <p className="mt-6 text-sm text-muted">
            Want to verify your download?{" "}
            <a href={CHECKSUMS_URL} className="underline hover:text-foreground">
              SHA-256 checksums
            </a>
            .
          </p>
        </section>
```

In "Run from source": change the intro paragraph to `Prefer to run the Python directly? You need Python 3.11 or newer.` and replace the second paragraph's text with:

```tsx
          <p className="mt-4 text-muted">
            It connects to the hosted relay by default. To self-host, start a
            relay with{" "}
            <code className="font-mono text-sm">./run.sh relay</code> and point
            clients at it with{" "}
            <code className="font-mono text-sm">BUDDIES_URL</code>, for example{" "}
            <code className="font-mono text-sm">
              BUDDIES_URL=ws://localhost:8765 ./run.sh client
            </code>
            .
          </p>
```

- [ ] **Step 5: Update landing-page copy**

In `components/Steps.tsx`, change the first step's body to `"Download it for macOS, Windows or Linux."`.
In `app/page.tsx`, change `No accounts and no sign-up — just a relay you run
              yourself.` to `No accounts and no sign-up — just a
              short code.`.

- [ ] **Step 6: Cross-check from the Python side**

Append to `tests/test_packaging.py`:

```python
def test_site_links_every_artifact():
    downloads = (ROOT / "desktop-buddies" / "lib" / "downloads.ts").read_text()
    for name in ARTIFACTS:
        assert name in downloads, name
```

Run: `python3 -m pytest tests/test_packaging.py -v` — expect all pass.

- [ ] **Step 7: Verify the site**

```bash
cd desktop-buddies && npm test && npm run lint && npm run build
```

Expected: tests pass, lint clean, build succeeds. Then with `npm run dev`, open `http://localhost:3000/download`: the button reads "Download for macOS" with an "Intel Mac?" link; "All platforms" lists four rows with Download links; "First launch" shows three step lists; "How?" scrolls to them. (Links 404 until Task 12 publishes the release — expected.)

- [ ] **Step 8: Commit**

```bash
git add desktop-buddies/lib/downloads.ts desktop-buddies/lib/downloads.test.ts desktop-buddies/components/DownloadButton.tsx desktop-buddies/app/download/page.tsx desktop-buddies/components/Steps.tsx desktop-buddies/app/page.tsx tests/test_packaging.py
git commit -m "feat(site): live installer downloads and first-launch steps

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Deploy the site to Vercel, point the update notice at it, document the release [USER]

**Files:**
- Modify: `Src/updates.py`, `CLAUDE.md`

**Interfaces:**
- Consumes: the pushed repo (Task 9).
- Produces: the site URL `https://<project>.vercel.app`; `DOWNLOAD_PAGE = "https://<project>.vercel.app/download"`.

- [ ] **Step 1: [USER] Import the project in Vercel**

Ask the user to:
1. Sign in at vercel.com with GitHub.
2. **Add New → Project**, import `KainBC/Desktop-Buddies`.
3. Set **Root Directory** to `desktop-buddies` (framework auto-detects as Next.js; leave build settings default).
4. **Deploy**. Under **Settings → Git**, confirm the Production Branch is `main`.
5. Report the production URL (e.g. `https://desktop-buddies.vercel.app`).

Expected: the deploy succeeds and serves the site currently on `main`. The draft PR from Task 9 gets a Vercel preview link — open its `/download` page and check it looks like Task 10 Step 7.

- [ ] **Step 2: Point the update notice at the site**

In `Src/updates.py`, set (with the real URL from Step 1):

```python
DOWNLOAD_PAGE = "https://desktop-buddies.vercel.app/download"
```

Run: `python3 -m pytest tests/test_menu.py tests/test_updates.py -q` — expect all pass.

- [ ] **Step 3: Document the release in CLAUDE.md**

In `CLAUDE.md`'s module map table, add rows after the `Src/app.py` row:

```markdown
| `Src/version.py` | `VERSION` — the single source of truth; CI refuses a tag that doesn't match. |
| `Src/resources.py` | `sprites_dir()` — finds `Sprites/` in a checkout or a PyInstaller bundle. |
| `Src/updates.py` | Pure update-check logic (`parse_version`, `is_newer`) + GitHub/site URLs. |
| `Src/update_checker.py` | `UpdateChecker`: one async GET to GitHub Releases; silent on failure. |
| `Src/smoke.py` | `--smoke-test`: headless self-check CI runs against each packaged build. |
| `packaging/` | PyInstaller spec, Inno Setup script, AppImage files, app icon. |
| `desktop-buddies/lib/downloads.ts` | `BUILDS` — installer URLs (`releases/latest/download`) + first-launch steps. |
```

Replace the existing `desktop-buddies/lib/downloads.ts` row (`BUILDS — the one place a real installer URL gets filled in.`) with the new one above rather than duplicating it.

In the Commands block, change the client line to:

```bash
BUDDIES_URL=ws://localhost:8765 python -m Src  # run a client (default: hosted relay)
python -m Src --smoke-test                   # headless self-check
pyinstaller --noconfirm --clean packaging/buddies.spec  # local build (needs pyinstaller + pillow)
```

Add a new section before `## Conventions`:

```markdown
## Release

- **Cut a release:** bump `VERSION` in `Src/version.py` (and `version` in
  `pyproject.toml` — a test checks they match), merge to `main`, then
  `git tag vX.Y.Z && git push origin vX.Y.Z`. `.github/workflows/release.yml`
  tests, builds four unsigned installers, smoke-tests each binary, and
  publishes a GitHub Release marked latest. The site's download links follow
  `releases/latest/download/…`, so the site needs no change.
- **Artifact names are a contract** between the workflow, `packaging/`, and
  `desktop-buddies/lib/downloads.ts`; `tests/test_packaging.py` and
  `downloads.test.ts` fail if they drift.
- **Relay:** runs on Fly.io as exactly one machine (`fly.toml`); rooms are in
  memory, so a deploy drops every room. Deploy deliberately with
  `fly deploy --ha=false`; watch with `fly logs`.
- **Site:** Vercel builds `desktop-buddies/` from `main`; PRs get previews.
```

- [ ] **Step 4: Commit and push**

```bash
git add Src/updates.py CLAUDE.md
git commit -m "docs: release process; point the update notice at the site

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

---

### Task 12: Merge, tag v1.0.0, verify the public release

**Files:** none (release operations).

**Interfaces:**
- Consumes: everything above, on `public-release`, CI green.

- [ ] **Step 1: Full verification before merging**

```bash
python3 -m pytest -q
(cd desktop-buddies && npm test && npm run build)
gh pr checks
```

Expected: all green. Stop and fix if not.

- [ ] **Step 2: Merge and tag (confirm with the user first — this publishes the release)**

Ask: "Ready to merge to `main` and publish v1.0.0?" On yes:

```bash
gh pr ready
gh pr merge --merge
git checkout main && git pull
git tag v1.0.0
git push origin v1.0.0
gh run watch
```

Between the merge and the release finishing (~15–25 min), the site's download links 404; that window is expected.

Expected: `check`, four `build` jobs, and `release` all green.

- [ ] **Step 3: Verify the release and the links**

```bash
gh release view v1.0.0
for f in DesktopBuddies-mac-arm64.dmg DesktopBuddies-mac-x64.dmg \
         DesktopBuddies-windows-setup.exe DesktopBuddies-linux-x86_64.AppImage \
         SHA256SUMS.txt; do
  printf '%s ' "$f"
  curl -s -o /dev/null -w '%{http_code}\n' -L \
    "https://github.com/KainBC/Desktop-Buddies/releases/latest/download/$f"
done
```

Expected: the release lists 5 assets and is marked Latest; every line prints `200`.

- [ ] **Step 4: End-to-end as a stranger**

On this Mac: open the production site's `/download`, click **Download for macOS**, open the dmg, drag to Applications, follow the site's First-launch steps exactly — confirm they are accurate. Launch, create a room (hosted relay), and join it from a second client (`python3 -m Src` from source works; no `BUDDIES_URL`). Confirm both buddies appear. Confirm the menu shows `v1.0.0` and no update line.

- [ ] **Step 5: Report**

Tell the user: release URL, site URL, relay URL, and anything from Step 4 that didn't match the instructions. Ask whether to test the Windows and Linux installers on real machines (CI only smoke-tests them headless).
