# Chat Bubbles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let room members send short text messages that appear as fading speech bubbles above the sender's sprite on every member's desktop.

**Architecture:** Add a `chat` message to the shared schema; the dumb relay fans it out like `state`. Clients open a composer by clicking their own sprite or pressing a global hotkey, sanitize the text, send it, and render a bubble window above the sender's sprite (including a local echo). Pure logic (sanitizing, bubble lifetime, positioning) lives in `Src/chat.py` and is unit-tested headless; Qt widgets stay thin.

**Tech Stack:** Python 3.11+, PySide6, `websockets`, `pynput` (new — global hotkey), pytest.

## Global Constraints

- Python 3.11+, PySide6 (not PyQt), `websockets` for transport.
- Sprite/wire coordinates are fractional floats `0.0`–`1.0`; pixels only at render time.
- Never hand-build JSON — always go through `shared/messages.py` `encode()`/`decode()`.
- Client-side pure logic stays separate from Qt so it can be unit-tested headless.
- Existing scaffold filenames stay capitalized (`Connections.py`); new modules are lowercase (`chat.py`, `bubble.py`, `chat_input.py`, `hotkey.py`).
- Max message length: **140 chars** (truncated, not rejected). Bubble timing: **~5s hold, ~0.5s fade**.
- Global hotkey default: **Cmd+Shift+B** on macOS, **Ctrl+Shift+B** elsewhere; fixed (not user-configurable this phase).
- Qt widget tests run headless with `QT_QPA_PLATFORM=offscreen`.
- Run the full suite with `python3 -m pytest -q` (interpreter is `python3` on this machine).

---

### Task 1: `chat` message type + schema round-trip

**Files:**
- Modify: `shared/messages.py`
- Test: `tests/test_messages.py`

**Interfaces:**
- Produces: `messages.CHAT == "chat"`; wire shape `{"type": "chat", "id": <str>, "text": <str>}`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_messages.py`:

```python
def test_chat_roundtrips_through_decode():
    raw = m.encode(m.CHAT, id="7", text="hello world")
    assert m.decode(raw) == {"type": "chat", "id": "7", "text": "hello world"}
```

Also add `m.CHAT` to the constants list inside `test_constants_are_distinct_strings`:

```python
    values = [m.CREATE_ROOM, m.ROOM_CREATED, m.JOIN_ROOM, m.ROOM_JOINED,
              m.ERROR, m.MEMBER_JOINED, m.MEMBER_LEFT, m.STATE, m.CHAT]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_messages.py -q`
Expected: FAIL with `AttributeError: module 'shared.messages' has no attribute 'CHAT'`.

- [ ] **Step 3: Add the constant**

In `shared/messages.py`, after the `STATE = "state"` line:

```python
CHAT = "chat"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_messages.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add shared/messages.py tests/test_messages.py
git commit -m "feat: add CHAT message type to shared schema"
```

---

### Task 2: Relay forwards `chat`

**Files:**
- Modify: `relay/server.py` (the handler branch that currently relays only `STATE`)
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `messages.CHAT` (Task 1), existing `Registry.relay(code, sender_id, raw)`.
- Produces: relay fans a `chat` message out to all room members except the sender.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_server.py` (reuses the existing `_recv` helper and `server` fixture):

```python
async def test_relay_forwards_chat(server):
    url = f"ws://localhost:{server}"
    async with websockets.connect(url) as host, websockets.connect(url) as guest:
        await host.send(m.encode(m.CREATE_ROOM, name="Kain", character="cat"))
        created = await _recv(host)
        host_id = created["your_id"]
        await guest.send(m.encode(m.JOIN_ROOM, code=created["code"],
                                  name="Sam", character="dog"))
        await _recv(guest)   # room_joined
        await _recv(host)    # member_joined

        raw = m.encode(m.CHAT, id=host_id, text="hi there")
        await host.send(raw)
        assert await _recv(guest) == m.decode(raw)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_server.py::test_relay_forwards_chat -q`
Expected: FAIL — the guest never receives the chat (times out), because the handler ignores `CHAT`.

- [ ] **Step 3: Widen the relay branch**

In `relay/server.py`, change:

```python
                elif mtype == m.STATE and member_id is not None:
                    await registry.relay(code, member_id, raw)
```

to:

```python
                elif mtype in (m.STATE, m.CHAT) and member_id is not None:
                    await registry.relay(code, member_id, raw)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_server.py -q`
Expected: PASS (all server tests).

- [ ] **Step 5: Commit**

```bash
git add relay/server.py tests/test_server.py
git commit -m "feat: relay forwards chat messages to room peers"
```

---

### Task 3: Pure chat logic — sanitize, lifetime, positioning

**Files:**
- Create: `Src/chat.py`
- Test: `tests/test_chat.py`

**Interfaces:**
- Produces:
  - `sanitize_chat(text: str, max_len: int = 140) -> str` — trims, collapses internal whitespace to single spaces, caps to `max_len`; returns `""` for empty/whitespace-only input.
  - `BubbleLifetime(hold: float = 5.0, fade: float = 0.5)` with `advance(dt: float) -> None`, `opacity() -> float`, `done` (property, bool), `reset() -> None`.
  - `bubble_position(sprite_x, sprite_y, sprite_w, bubble_w, bubble_h, screen_w, gap=8) -> tuple[int, int]` — centers the bubble horizontally over the sprite, `gap` px above its top edge, clamped on-screen.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_chat.py`:

```python
from Src.chat import sanitize_chat, BubbleLifetime, bubble_position


def test_sanitize_trims_and_collapses_whitespace():
    assert sanitize_chat("  hello    world  ") == "hello world"
    assert sanitize_chat("line1\n\nline2") == "line1 line2"


def test_sanitize_empty_returns_empty():
    assert sanitize_chat("") == ""
    assert sanitize_chat("    \n\t ") == ""


def test_sanitize_caps_length():
    assert sanitize_chat("a" * 200, max_len=140) == "a" * 140


def test_lifetime_full_opacity_during_hold():
    life = BubbleLifetime(hold=5.0, fade=0.5)
    assert life.opacity() == 1.0
    assert not life.done
    life.advance(5.0)
    assert life.opacity() == 1.0
    assert not life.done


def test_lifetime_fades_then_done():
    life = BubbleLifetime(hold=5.0, fade=0.5)
    life.advance(5.25)                       # halfway through the fade
    assert abs(life.opacity() - 0.5) < 1e-6
    life.advance(0.25)                       # end of fade
    assert life.opacity() == 0.0
    assert life.done


def test_lifetime_reset():
    life = BubbleLifetime(hold=0.1, fade=0.1)
    life.advance(1.0)
    assert life.done
    life.reset()
    assert not life.done
    assert life.opacity() == 1.0


def test_bubble_position_centers_and_sits_above():
    x, y = bubble_position(sprite_x=100, sprite_y=300, sprite_w=64,
                           bubble_w=120, bubble_h=40, screen_w=1000, gap=8)
    assert x == 100 + (64 - 120) // 2        # centered (may be left of sprite_x)
    assert y == 300 - 40 - 8


def test_bubble_position_clamps_to_screen():
    # far left sprite -> bubble clamped to x=0
    x, _ = bubble_position(0, 300, 20, 120, 40, 1000)
    assert x == 0
    # far right sprite -> bubble clamped to screen_w - bubble_w
    x, _ = bubble_position(980, 300, 20, 120, 40, 1000)
    assert x == 1000 - 120
    # near top -> bubble clamped to y=0
    _, y = bubble_position(100, 10, 64, 120, 40, 1000)
    assert y == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_chat.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'Src.chat'`.

- [ ] **Step 3: Implement `Src/chat.py`**

```python
import re

_WS_RUN = re.compile(r"\s+")


def sanitize_chat(text: str, max_len: int = 140) -> str:
    """Collapse whitespace, trim, and cap length. Empty/whitespace -> ''."""
    collapsed = _WS_RUN.sub(" ", text).strip()
    return collapsed[:max_len]


class BubbleLifetime:
    """Tracks how long a bubble has been shown: full opacity during `hold`,
    a linear fade over `fade`, then done."""

    def __init__(self, hold: float = 5.0, fade: float = 0.5):
        self.hold = hold
        self.fade = fade
        self._elapsed = 0.0

    def advance(self, dt: float) -> None:
        self._elapsed += dt

    def opacity(self) -> float:
        if self._elapsed <= self.hold:
            return 1.0
        if self._elapsed >= self.hold + self.fade:
            return 0.0
        return 1.0 - (self._elapsed - self.hold) / self.fade

    @property
    def done(self) -> bool:
        return self._elapsed >= self.hold + self.fade

    def reset(self) -> None:
        self._elapsed = 0.0


def bubble_position(sprite_x: int, sprite_y: int, sprite_w: int,
                    bubble_w: int, bubble_h: int, screen_w: int,
                    gap: int = 8) -> tuple[int, int]:
    """Center the bubble over the sprite, `gap` px above its top edge,
    clamped so it stays on the primary screen."""
    x = sprite_x + (sprite_w - bubble_w) // 2
    y = sprite_y - bubble_h - gap
    x = max(0, min(x, screen_w - bubble_w))
    y = max(0, y)
    return x, y
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_chat.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add Src/chat.py tests/test_chat.py
git commit -m "feat: pure chat helpers (sanitize, bubble lifetime, positioning)"
```

---

### Task 4: `NetClient` send + receive for chat

**Files:**
- Modify: `Src/Connections.py`
- Test: `tests/test_connections.py` (new)

**Interfaces:**
- Consumes: `messages.CHAT` (Task 1).
- Produces:
  - `NetClient.chat_received = Signal(dict)` — emits the decoded `{"type","id","text"}` dict.
  - `NetClient.send_chat(id: str, text: str) -> None` — encodes and submits a `CHAT` message.

- [ ] **Step 1: Write the failing test**

Create `tests/test_connections.py`:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from Src.Connections import NetClient  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def test_dispatch_chat_emits_signal():
    _app()
    nc = NetClient()
    got = []
    nc.chat_received.connect(got.append)
    nc._dispatch({"type": "chat", "id": "3", "text": "hi"})
    assert got == [{"type": "chat", "id": "3", "text": "hi"}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_connections.py -q`
Expected: FAIL with `AttributeError: 'NetClient' object has no attribute 'chat_received'`.

- [ ] **Step 3: Add the signal, sender, and dispatch branch**

In `Src/Connections.py`, add the signal alongside the others (after `remote_state = Signal(dict)`):

```python
    chat_received = Signal(dict)
```

Add a sender method after `send_state`:

```python
    def send_chat(self, id: str, text: str) -> None:
        raw = m.encode(m.CHAT, id=id, text=text)
        self._submit(raw)
```

Add a branch in `_dispatch`, after the `STATE` branch:

```python
        elif t == m.CHAT:
            self.chat_received.emit(msg)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_connections.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add Src/Connections.py tests/test_connections.py
git commit -m "feat: NetClient send_chat + chat_received signal"
```

---

### Task 5: `BubbleWindow` (Qt render + fade)

**Files:**
- Create: `Src/bubble.py`
- Test: `tests/test_bubble.py` (new)

**Interfaces:**
- Consumes: `Src.chat.BubbleLifetime` (Task 3).
- Produces: `BubbleWindow(hold=5.0, fade=0.5)` with `set_text(text: str) -> None`, `tick(dt: float) -> None`, `done` (property, bool). Frameless, translucent, always-on-top, click-through, and visible when the app is not frontmost.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bubble.py`:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from Src.bubble import BubbleWindow  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def test_bubble_expires_after_lifetime():
    _app()
    b = BubbleWindow(hold=0.1, fade=0.1)
    b.set_text("hello")
    assert not b.done
    b.tick(0.1)      # end of hold
    b.tick(0.1)      # end of fade
    assert b.done
    b.close()


def test_set_text_resets_lifetime():
    _app()
    b = BubbleWindow(hold=0.1, fade=0.1)
    b.set_text("a")
    b.tick(0.2)      # would be done
    assert b.done
    b.set_text("b")  # replaces + resets
    assert not b.done
    b.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_bubble.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'Src.bubble'`.

- [ ] **Step 3: Implement `Src/bubble.py`**

```python
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QWidget

from Src.chat import BubbleLifetime

MAX_WIDTH = 220
PAD_X = 10
PAD_Y = 6


class BubbleWindow(QWidget):
    def __init__(self, hold: float = 5.0, fade: float = 0.5):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._font = QFont()
        self._text = ""
        self._text_rect = None
        self._life = BubbleLifetime(hold, fade)
        self.show()

    def set_text(self, text: str) -> None:
        self._text = text
        self._life.reset()
        self._relayout()
        self.setWindowOpacity(1.0)
        self.update()

    def _relayout(self) -> None:
        fm = QFontMetrics(self._font)
        rect = fm.boundingRect(0, 0, MAX_WIDTH, 10_000,
                               Qt.TextWordWrap, self._text)
        self._text_rect = rect
        self.resize(rect.width() + 2 * PAD_X, rect.height() + 2 * PAD_Y)

    def tick(self, dt: float) -> None:
        self._life.advance(dt)
        self.setWindowOpacity(self._life.opacity())
        self.update()

    @property
    def done(self) -> bool:
        return self._life.done

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(255, 255, 255, 235))
        p.setPen(QColor(0, 0, 0, 40))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)
        p.setPen(QColor(20, 20, 20))
        p.setFont(self._font)
        p.drawText(self.rect().adjusted(PAD_X, PAD_Y, -PAD_X, -PAD_Y),
                   Qt.TextWordWrap | Qt.AlignCenter, self._text)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_bubble.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add Src/bubble.py tests/test_bubble.py
git commit -m "feat: BubbleWindow speech-bubble widget with fade"
```

---

### Task 6: `ChatInputWindow` (composer)

**Files:**
- Create: `Src/chat_input.py`
- Test: `tests/test_chat_input.py` (new)

**Interfaces:**
- Consumes: `Src.chat.sanitize_chat` (Task 3).
- Produces: `ChatInputWindow(max_len=140)` with `submitted = Signal(str)`, `open_at(x: int, y: int) -> None`, and an internal `edit` (QLineEdit). Enter submits sanitized non-empty text and hides; empty input hides without emitting; Escape / focus-out cancels.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_chat_input.py`:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from Src.chat_input import ChatInputWindow  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def test_emits_sanitized_text():
    _app()
    w = ChatInputWindow()
    got = []
    w.submitted.connect(got.append)
    w.edit.setText("  hi   there  ")
    w._submit()
    assert got == ["hi there"]


def test_ignores_empty_input():
    _app()
    w = ChatInputWindow()
    got = []
    w.submitted.connect(got.append)
    w.edit.setText("     ")
    w._submit()
    assert got == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_chat_input.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'Src.chat_input'`.

- [ ] **Step 3: Implement `Src/chat_input.py`**

```python
from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtWidgets import QWidget, QLineEdit, QVBoxLayout

from Src.chat import sanitize_chat


class ChatInputWindow(QWidget):
    submitted = Signal(str)

    def __init__(self, max_len: int = 140):
        super().__init__(None)
        self._max_len = max_len
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setMaxLength(max_len)
        self.edit.setPlaceholderText("Say something…")
        self.edit.returnPressed.connect(self._submit)
        self.edit.installEventFilter(self)
        layout.addWidget(self.edit)
        self.resize(200, 32)

    def open_at(self, x: int, y: int) -> None:
        self.move(x, y)
        self.edit.clear()
        self.show()
        self.raise_()
        self.activateWindow()
        self.edit.setFocus()

    def _submit(self) -> None:
        text = sanitize_chat(self.edit.text(), self._max_len)
        self.hide()
        if text:
            self.submitted.emit(text)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.edit:
            if (event.type() == QEvent.KeyPress
                    and event.key() == Qt.Key_Escape):
                self.hide()
                return True
            if event.type() == QEvent.FocusOut:
                self.hide()
        return super().eventFilter(obj, event)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_chat_input.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add Src/chat_input.py tests/test_chat_input.py
git commit -m "feat: ChatInputWindow composer"
```

---

### Task 7: `GlobalHotkey` (pynput wrapper, graceful)

**Files:**
- Create: `Src/hotkey.py`
- Modify: `requirements.txt`
- Test: `tests/test_hotkey.py` (new)

**Interfaces:**
- Produces: `GlobalHotkey(combo: str = DEFAULT_HOTKEY)` (a `QObject`) with `activated = Signal()`, `start() -> bool` (True if listening; False if pynput missing or the OS denied it — never raises), and `stop() -> None`. `DEFAULT_HOTKEY` is `"<cmd>+<shift>+b"` on macOS, `"<ctrl>+<shift>+b"` elsewhere.

- [ ] **Step 1: Add the dependency and install it**

Add to `requirements.txt`:

```
pynput>=1.7
```

Run: `python3 -m pip install "pynput>=1.7"`
Expected: pynput installs successfully.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_hotkey.py`:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from Src.hotkey import GlobalHotkey, DEFAULT_HOTKEY  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def test_default_hotkey_is_a_combo_string():
    assert "+" in DEFAULT_HOTKEY and DEFAULT_HOTKEY.endswith("b")


def test_activated_signal_is_connectable():
    _app()
    hk = GlobalHotkey()
    fired = []
    hk.activated.connect(lambda: fired.append(True))
    hk.activated.emit()
    assert fired == [True]


def test_bad_combo_fails_gracefully():
    _app()
    hk = GlobalHotkey(combo="not-a-real-combo!!")
    assert hk.start() is False   # must not raise
    hk.stop()                    # safe even though nothing started


def test_stop_before_start_is_noop():
    _app()
    hk = GlobalHotkey()
    hk.stop()                    # must not raise
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_hotkey.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'Src.hotkey'`.

- [ ] **Step 4: Implement `Src/hotkey.py`**

```python
import sys

from PySide6.QtCore import QObject, Signal

DEFAULT_HOTKEY = "<cmd>+<shift>+b" if sys.platform == "darwin" \
    else "<ctrl>+<shift>+b"


class GlobalHotkey(QObject):
    """Wraps pynput's global hotkey listener. Fails gracefully: if pynput is
    unavailable or the OS denies the listener (e.g. macOS Accessibility not
    granted), start() returns False and the app keeps working without it."""

    activated = Signal()

    def __init__(self, combo: str = DEFAULT_HOTKEY):
        super().__init__()
        self._combo = combo
        self._listener = None

    def start(self) -> bool:
        try:
            from pynput import keyboard
        except Exception as exc:                       # noqa: BLE001
            print(f"[hotkey] pynput unavailable, global hotkey disabled: {exc}")
            return False
        try:
            self._listener = keyboard.GlobalHotKeys(
                {self._combo: self.activated.emit})
            self._listener.start()
            return True
        except Exception as exc:                       # noqa: BLE001
            print(f"[hotkey] could not register global hotkey: {exc}")
            self._listener = None
            return False

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_hotkey.py -q`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add Src/hotkey.py tests/test_hotkey.py requirements.txt
git commit -m "feat: GlobalHotkey pynput wrapper with graceful fallback"
```

---

### Task 8: Wire chat into `AppController`

**Files:**
- Modify: `Src/app.py`
- Test: manual integration (Task 9). No unit test — this is Qt/network glue; the trickiest pure piece (`bubble_position`) is already covered in Task 3.

**Interfaces:**
- Consumes: `NetClient.send_chat` / `chat_received` (Task 4), `BubbleWindow` (Task 5), `ChatInputWindow` (Task 6), `GlobalHotkey` (Task 7), `sanitize_chat` / `bubble_position` (Task 3), existing `SpriteWindow.clicked`.

- [ ] **Step 1: Add imports**

In `Src/app.py`, extend the imports near the top:

```python
from Src.bubble import BubbleWindow
from Src.chat import bubble_position
from Src.chat_input import ChatInputWindow
from Src.hotkey import GlobalHotkey
```

- [ ] **Step 2: Initialize chat state and wiring in `__init__`**

In `AppController.__init__`, after `self.windows: dict[str, SpriteWindow] = {}` add:

```python
        self.bubbles: dict[str, BubbleWindow] = {}   # sprite id -> bubble
        self._hotkey_attempted = False
```

After the existing `self.net.*` connections, add:

```python
        self.net.chat_received.connect(self._on_chat)
```

After `self.menu = MenuWindow()` block (once `self.net` exists), add the composer and hotkey:

```python
        self.chat_input = ChatInputWindow()
        self.chat_input.submitted.connect(self._on_chat_submit)
        self.hotkey = GlobalHotkey()
        self.hotkey.activated.connect(self._open_composer_for_own)
```

- [ ] **Step 3: Open the composer from the owned sprite click and the hotkey**

In `_begin_world`, after `self.windows[your_id] = SpriteWindow(...)`, connect the click and start the hotkey once:

```python
        self.windows[your_id].clicked.connect(self._open_composer_for_own)
        if not self._hotkey_attempted:
            self._hotkey_attempted = True
            self.hotkey.start()   # False if the OS denied it; click still works
```

Add these methods to `AppController`:

```python
    def _open_composer_for_own(self):
        if not self.world:
            return
        win = self.windows.get(self.world.own.id)
        if win is None:
            return
        self.chat_input.open_at(win.x(), win.y() - 36)

    def _on_chat_submit(self, text):
        if not self.world:
            return
        own = self.world.own
        self.net.send_chat(own.id, text)
        self._show_bubble(own.id, text)      # local echo

    def _on_chat(self, msg):
        self._show_bubble(msg["id"], msg["text"])

    def _show_bubble(self, sid, text):
        if sid not in self.windows:
            return
        bub = self.bubbles.get(sid)
        if bub is None:
            bub = BubbleWindow()
            self.bubbles[sid] = bub
        bub.set_text(text)
```

- [ ] **Step 4: Tick and position bubbles in `_tick`**

In `_tick`, after the `for sp in self.world.all_sprites():` loop that positions sprite windows (and with `screen` already computed above it), add:

```python
        for sid, bub in list(self.bubbles.items()):
            bub.tick(dt)
            win = self.windows.get(sid)
            if bub.done or win is None:
                bub.close()
                del self.bubbles[sid]
                continue
            bx, by = bubble_position(win.x(), win.y(), win.width(),
                                     bub.width(), bub.height(), screen.width())
            bub.move(bx, by)
```

- [ ] **Step 5: Clean up bubbles on member-left and disconnect**

In `_on_member_left`, after closing the sprite window, add:

```python
        b = self.bubbles.pop(mid, None)
        if b:
            b.close()
```

In `_on_disconnected`, after `self.windows.clear()`, add:

```python
        for b in self.bubbles.values():
            b.close()
        self.bubbles.clear()
```

- [ ] **Step 6: Run the full suite (nothing regressed)**

Run: `python3 -m pytest -q`
Expected: PASS — all prior tests plus the new chat tests.

- [ ] **Step 7: Commit**

```bash
git add Src/app.py
git commit -m "feat: wire chat composer, bubbles, and hotkey into AppController"
```

---

### Task 9: Manual integration verification

**Files:** none (verification only).

- [ ] **Step 1: Start the relay**

```bash
BUDDIES_HOST=127.0.0.1 python3 -m relay
```

- [ ] **Step 2: Launch two clients in a shared room**

In two more terminals:

```bash
BUDDIES_URL=ws://127.0.0.1:8765 python3 -m Src
```

Create a room in the first (pick the cat), join with the code in the second (pick the dog).

- [ ] **Step 3: Send a chat by clicking your own sprite**

Click your own sprite → the input box opens beside it. Type a message, press Enter.
Expected: a bubble appears above the sender's sprite **on both desktops** and fades after ~5s. The sender sees their own bubble (local echo).

- [ ] **Step 4: Send a chat via the global hotkey**

Press **Cmd+Shift+B** (macOS) / **Ctrl+Shift+B** while another app is focused.
Expected: the input opens; typing + Enter shows a bubble as above. (On macOS, if nothing happens, grant the Python process Accessibility permission in System Settings → Privacy & Security → Accessibility, or rely on click-to-chat — the app still works.)

- [ ] **Step 5: Verify replace-not-queue**

Send a second message before the first fades.
Expected: the bubble text is replaced and the timer resets (no stacking/queue).

- [ ] **Step 6: Verify cleanup**

Close one client.
Expected: its sprite and any bubble disappear on the other desktop.

---

## Self-Review

**Spec coverage:**
- `CHAT` wire type + shape → Task 1. ✓
- Relay forwards chat (dumb, no inspection) → Task 2. ✓
- Click own sprite trigger → Task 8 (`SpriteWindow.clicked` → `_open_composer_for_own`). ✓
- Global hotkey trigger + graceful macOS fallback → Task 7 + Task 8 wiring. ✓
- Sanitize (trim/collapse/cap 140, empty→ignore) → Task 3 + used in Tasks 6, 8. ✓
- Bubble render above sprite, ~5s hold + ~0.5s fade, replace+reset → Tasks 3 (lifetime), 5 (window), 8 (show/replace). ✓
- Local echo above own sprite → Task 8 `_on_chat_submit`. ✓
- Bubble follows sprite + on-screen clamp → Task 3 `bubble_position` + Task 8 `_tick`. ✓
- macOS always-show + click-through bubble → Task 5 window attributes. ✓
- Cleanup on member-left / disconnect → Task 8 Step 5. ✓
- Unknown-id chat ignored → Task 8 `_show_bubble` guard. ✓
- Malformed chat ignored → existing `decode` returns None (Task 4 dispatch only emits on decoded dict). ✓
- Testing: headless units (schema, relay, sanitize, lifetime, positioning, dispatch, bubble, input, hotkey) + manual integration → Tasks 1–7, 9. ✓
- `pynput` dependency added → Task 7. ✓

**Placeholder scan:** No TBD/TODO anywhere; every code step contains full, self-contained code.

**Type consistency:** `send_chat(id, text)` / `chat_received(dict)` (Task 4) match usage in Task 8. `BubbleLifetime.advance/opacity/done/reset` (Task 3) match `BubbleWindow` usage (Task 5). `bubble_position(...)` signature (Task 3) matches the call in Task 8 Step 4. `ChatInputWindow.submitted` / `open_at` / `edit` (Task 6) match Task 8. `GlobalHotkey.activated` / `start` / `stop` (Task 7) match Task 8. Message shape `{type,id,text}` consistent across Tasks 1, 2, 4, 8.
