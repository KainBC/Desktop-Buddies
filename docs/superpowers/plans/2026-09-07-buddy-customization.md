# Buddy Customization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a player pick their buddy's body type and skin color in the launch menu against a live animated preview, built on a layer compositor so hair, outfits, and shoes can be added later without reworking the renderer.

**Architecture:** An `Appearance` value object replaces the `character` string everywhere, including on the wire. A manifest declares ordered sprite *slots* (body, shoes, outfit, face, hair); `resolve_layers()` turns an appearance into an ordered list of `LayerSpec`s; the compositor stacks and tints them into finished frames. Only `resolve_layers()` knows what a layer means, so future slots are a change to one function plus art. The relay keeps treating appearance as an opaque blob.

**Tech Stack:** Python 3.11+, PySide6 (not PyQt), `websockets`, pytest.

**Spec:** `docs/superpowers/specs/2026-09-07-buddy-customization-design.md`

## Global Constraints

- Python 3.11+, PySide6 (never PyQt), `websockets` for transport.
- Sprite coordinates on the wire and in the world model are fractional floats `0.0`–`1.0`. Pixels only at render time.
- `facing` is `1` (right) or `-1` (left).
- Logic must be testable headless. Keep pure logic (`appearance`, `layers`, `profile`) free of any Qt import.
- Existing scaffold filenames stay capitalized (`Connections.py`, `User.py`, `Host.py`); new modules are lowercase.
- Qt tests must set `QT_QPA_PLATFORM=offscreen` before importing QtWidgets, following `tests/test_sprite_frames.py`.
- Run the whole suite with `python -m pytest -v`. Every task ends green.
- The branch is `buddy-customization`, rebased onto `pokes`. Do not merge or rebase it during execution.
- Never hand-build wire JSON — always go through `shared/messages.py` `encode()`/`decode()`.
- The old `Sprites/placeholder_{cat,dog,blob}/` folders stay in place until Task 9, so every intermediate commit still runs.

## File Structure

**Created:**
- `Src/appearance.py` — `Appearance` value object, defaults, skin palette. No Qt.
- `Src/layers.py` — manifest loading, slot option discovery, `resolve_layers()`. No Qt.
- `Src/profile.py` — load/save name + appearance JSON. No Qt.
- `Src/customizer.py` — `PreviewWidget` and `CustomizerPanel`. Qt.
- `Sprites/manifest.json` — slot declarations, `fps`, `scale`.
- `tests/test_appearance.py`, `tests/test_layers.py`, `tests/test_profile.py`, `tests/test_customizer.py`

**Modified:**
- `tools/make_placeholder_sprites.py` — emits the layered tree instead of flat characters.
- `Src/sprite_window.py` — compositing replaces `load_frames`; `SpriteWindow` takes an `Appearance`.
- `Src/User.py`, `Src/world.py` — carry `Appearance` instead of `character`.
- `Src/Connections.py`, `relay/room.py`, `relay/server.py` — `character` → `appearance` dict on the wire.
- `Src/menu.py` — customizer panel replaces the character radio buttons.
- `Src/app.py` — builds `Appearance`, loads/saves the profile.
- `tests/test_menu.py`, `tests/test_room.py`, `tests/test_server.py`, `tests/test_world.py`, `tests/test_sprite_frames.py` — updated for the new type.
  (`tests/test_connections.py` and `tests/test_smoke.py` are listed in the spec's testing section but reference no `character` field, so they need no change. Confirm with `grep -rn character tests/` before assuming otherwise.)
- `CLAUDE.md` — module map and conventions.

---

### Task 1: Appearance value object

**Files:**
- Create: `Src/appearance.py`
- Test: `tests/test_appearance.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Appearance(body: str = DEFAULT_BODY, skin: str = DEFAULT_SKIN)`, frozen dataclass with `.to_dict() -> dict` and classmethod `.from_dict(data) -> Appearance`. Module constants `DEFAULT_BODY: str`, `DEFAULT_SKIN: str`, `SKIN_PALETTE: list[str]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_appearance.py`:

```python
from Src.appearance import (Appearance, DEFAULT_BODY, DEFAULT_SKIN,
                            SKIN_PALETTE)


def test_defaults_are_renderable():
    a = Appearance()
    assert a.body == DEFAULT_BODY
    assert a.skin == DEFAULT_SKIN


def test_round_trip():
    a = Appearance(body="tall", skin="#123456")
    assert Appearance.from_dict(a.to_dict()) == a


def test_unknown_keys_are_dropped():
    """A future client sends hair; this build must render a bald buddy,
    not crash."""
    a = Appearance.from_dict({"body": "slim", "skin": "#abcdef",
                              "hair": "spiky", "hair_color": "#000000"})
    assert a == Appearance(body="slim", skin="#abcdef")


def test_missing_keys_default():
    a = Appearance.from_dict({"body": "tall"})
    assert a == Appearance(body="tall", skin=DEFAULT_SKIN)


def test_malformed_input_yields_defaults():
    assert Appearance.from_dict(None) == Appearance()
    assert Appearance.from_dict("nonsense") == Appearance()
    assert Appearance.from_dict([]) == Appearance()


def test_non_string_values_are_ignored():
    assert Appearance.from_dict({"body": 7}) == Appearance()


def test_appearance_is_hashable():
    """Frozen, so it can key a cache."""
    assert {Appearance(): 1}[Appearance()] == 1


def test_palette_is_nonempty_hex():
    assert SKIN_PALETTE
    assert all(c.startswith("#") and len(c) == 7 for c in SKIN_PALETTE)
    assert DEFAULT_SKIN in SKIN_PALETTE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_appearance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'Src.appearance'`

- [ ] **Step 3: Write minimal implementation**

Create `Src/appearance.py`:

```python
"""The player's buddy appearance. Pure data — no Qt, no filesystem.

Every future customization slot (hair, outfit, shoes) is added here as an
optional field with a default. `from_dict` deliberately ignores keys it does
not know and defaults keys that are missing, so a client running a newer or
older build degrades instead of crashing.
"""
from dataclasses import dataclass, fields

SKIN_PALETTE = [
    "#f6d5bd", "#e8b48c", "#d9a066", "#c98d63",
    "#a4673f", "#8d5524", "#7a4a2b", "#5a3520",
]

DEFAULT_BODY = "round"
DEFAULT_SKIN = "#e8b48c"


@dataclass(frozen=True)
class Appearance:
    body: str = DEFAULT_BODY
    skin: str = DEFAULT_SKIN

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data) -> "Appearance":
        if not isinstance(data, dict):
            return cls()
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items()
                  if k in known and isinstance(v, str)}
        return cls(**kwargs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_appearance.py -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Commit**

```bash
git add Src/appearance.py tests/test_appearance.py
git commit -m "feat: Appearance value object with forward-compatible parsing"
```

---

### Task 2: Layered sprite tree and manifest

Rewrites the placeholder generator to emit tintable white body silhouettes and a separate face layer, plus the manifest that declares slot order. The old `Sprites/placeholder_*` folders are left alone so the app keeps running; Task 9 deletes them.

**Files:**
- Modify: `tools/make_placeholder_sprites.py` (full rewrite)
- Create: `Sprites/manifest.json` (written by the script)
- Test: none — this is an asset generator; Task 3 asserts against its output.

**Interfaces:**
- Consumes: nothing.
- Produces: `Sprites/manifest.json` with keys `fps: int`, `scale: int`, `slots: list[dict]`. Each slot dict has `name`, `z`, `dir`, `field`, `tint_field` (string or null), and optionally `default`. Directories `Sprites/Bodies/{round,tall,slim}/{idle,walk}/*.png` (white silhouettes) and `Sprites/Faces/default/{idle,walk}/0.png`.

- [ ] **Step 1: Rewrite the generator**

Replace the entire contents of `tools/make_placeholder_sprites.py`:

```python
"""Generate placeholder buddy layers with PySide6 (no external art).

Bodies are drawn WHITE on transparent so they can be tinted to any skin
color at load time. The face is a separate, untinted layer. Faces get a
single frame per animation on purpose: it exercises the compositor's rule
that a short layer repeats via modulo against the body's frame count.
"""
import json
import math
import sys
from pathlib import Path

from PySide6.QtGui import QImage, QPainter, QColor, QBrush
from PySide6.QtCore import Qt, QRectF

ROOT = Path(__file__).resolve().parent.parent / "Sprites"
SIZE = 64
WHITE = QColor(255, 255, 255)
INK = QColor(30, 30, 30)

# name -> (width fraction, height fraction)
BODIES = {
    "round": (0.72, 0.62),
    "tall": (0.56, 0.78),
    "slim": (0.46, 0.70),
}

MANIFEST = {
    "fps": 6,
    "scale": 1,
    "slots": [
        {"name": "body", "z": 0, "dir": "Bodies",
         "field": "body", "tint_field": "skin", "default": "round"},
        {"name": "shoes", "z": 10, "dir": "Shoes",
         "field": "shoes", "tint_field": "shoe_color"},
        {"name": "outfit", "z": 20, "dir": "Outfits",
         "field": "outfit", "tint_field": "outfit_color"},
        {"name": "face", "z": 30, "dir": "Faces",
         "field": "face", "tint_field": None, "default": "default"},
        {"name": "hair", "z": 40, "dir": "Hair",
         "field": "hair", "tint_field": "hair_color"},
    ],
}

FUTURE_DIRS = ["Hair", "Outfits", "Shoes"]


def _canvas() -> QImage:
    img = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    return img


def _body_rect(wf: float, hf: float, squash: float) -> QRectF:
    h = SIZE * hf * squash
    w = SIZE * wf / squash
    return QRectF((SIZE - w) / 2, SIZE - h - 2, w, h)


def _body_frame(wf: float, hf: float, squash: float, step: int) -> QImage:
    img = _canvas()
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(WHITE))
    body = _body_rect(wf, hf, squash)
    p.drawRoundedRect(body, 12, 12)
    foot_dy = 3 * math.sin(step * math.pi / 2)
    p.drawEllipse(QRectF(body.left() + 6, SIZE - 6 + foot_dy, 10, 6))
    p.drawEllipse(QRectF(body.right() - 16, SIZE - 6 - foot_dy, 10, 6))
    p.end()
    return img


def _face_frame() -> QImage:
    """Eyes at a fixed head height so one face reads acceptably on every
    body type. Real art would ship a face per body."""
    img = _canvas()
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(INK))
    eye_y = SIZE * 0.30
    cx = SIZE / 2
    p.drawEllipse(QRectF(cx - 11, eye_y, 6, 6))
    p.drawEllipse(QRectF(cx + 5, eye_y, 6, 6))
    p.end()
    return img


def build() -> None:
    for name, (wf, hf) in BODIES.items():
        base = ROOT / "Bodies" / name
        (base / "idle").mkdir(parents=True, exist_ok=True)
        (base / "walk").mkdir(parents=True, exist_ok=True)
        for i in range(2):
            _body_frame(wf, hf, 1.0 + 0.03 * (i % 2), i).save(
                str(base / "idle" / f"{i}.png"))
        for i in range(4):
            _body_frame(wf, hf, 1.0, i).save(str(base / "walk" / f"{i}.png"))
        print(f"wrote Bodies/{name}")

    face = ROOT / "Faces" / "default"
    for anim in ("idle", "walk"):
        (face / anim).mkdir(parents=True, exist_ok=True)
        _face_frame().save(str(face / anim / "0.png"))
    print("wrote Faces/default")

    for d in FUTURE_DIRS:
        (ROOT / d).mkdir(parents=True, exist_ok=True)

    (ROOT / "manifest.json").write_text(json.dumps(MANIFEST, indent=2))
    print("wrote manifest.json")


if __name__ == "__main__":
    sys.exit(build())
```

- [ ] **Step 2: Run the generator**

Run: `python tools/make_placeholder_sprites.py`
Expected: prints `wrote Bodies/round`, `wrote Bodies/tall`, `wrote Bodies/slim`, `wrote Faces/default`, `wrote manifest.json`

- [ ] **Step 3: Verify the tree and that bodies really are white**

Run:

```bash
find Sprites/Bodies Sprites/Faces -type f | sort
python -c "
from PySide6.QtGui import QImage
img = QImage('Sprites/Bodies/round/idle/0.png')
c = img.pixelColor(32, 40)
print('body pixel:', c.red(), c.green(), c.blue(), 'alpha', c.alpha())
assert (c.red(), c.green(), c.blue()) == (255, 255, 255), 'body must be white to tint'
assert c.alpha() > 0
print('OK')
"
```

Expected: 20 files listed — 3 bodies x 6 frames (2 idle + 4 walk) = 18 body PNGs, plus 2 face PNGs — and `OK` from the pixel check.

- [ ] **Step 4: Confirm nothing regressed**

Run: `python -m pytest -v`
Expected: PASS — the old `Sprites/placeholder_*` folders are untouched, so existing sprite tests still work.

- [ ] **Step 5: Commit**

```bash
git add tools/make_placeholder_sprites.py Sprites/manifest.json Sprites/Bodies Sprites/Faces
git commit -m "feat: generate layered white-silhouette sprite tree and slot manifest"
```

---

### Task 3: Slot discovery and layer resolution

**Files:**
- Create: `Src/layers.py`
- Test: `tests/test_layers.py`

**Interfaces:**
- Consumes: `Appearance` from Task 1; `Sprites/manifest.json` from Task 2.
- Produces: `LayerSpec(frames_dir: Path, tint: str | None, z: int)` frozen dataclass; `load_manifest(sprites_dir) -> dict`; `slot_options(sprites_dir, slot: dict) -> list[str]`; `body_options(sprites_dir) -> list[str]`; `resolve_layers(appearance, sprites_dir, manifest=None) -> list[LayerSpec]` sorted ascending by `z`. `frames_dir` points at the *character* directory — callers append the animation name.

- [ ] **Step 1: Write the failing test**

Create `tests/test_layers.py`:

```python
import json
from pathlib import Path

from Src.appearance import Appearance
from Src.layers import (LayerSpec, load_manifest, resolve_layers,
                        slot_options, body_options)

REAL_SPRITES = Path(__file__).resolve().parent.parent / "Sprites"


def _fake_tree(tmp_path: Path) -> Path:
    """A miniature Sprites/ dir: two body types, one face, one hair style."""
    manifest = {
        "fps": 6,
        "scale": 1,
        "slots": [
            {"name": "body", "z": 0, "dir": "Bodies",
             "field": "body", "tint_field": "skin", "default": "round"},
            {"name": "shoes", "z": 10, "dir": "Shoes",
             "field": "shoes", "tint_field": "shoe_color"},
            {"name": "face", "z": 30, "dir": "Faces",
             "field": "face", "tint_field": None, "default": "default"},
            {"name": "hair", "z": 40, "dir": "Hair",
             "field": "hair", "tint_field": "hair_color"},
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    for rel in ("Bodies/round", "Bodies/tall", "Faces/default", "Hair/spiky"):
        (tmp_path / rel / "idle").mkdir(parents=True)
    (tmp_path / "Shoes").mkdir()
    return tmp_path


def test_resolves_body_and_face_in_draw_order(tmp_path):
    root = _fake_tree(tmp_path)
    layers = resolve_layers(Appearance(body="tall", skin="#ff0000"), root)
    assert [l.z for l in layers] == [0, 30]
    assert layers[0].frames_dir == root / "Bodies" / "tall"
    assert layers[1].frames_dir == root / "Faces" / "default"


def test_only_tintable_slots_get_a_tint(tmp_path):
    root = _fake_tree(tmp_path)
    layers = resolve_layers(Appearance(skin="#ff0000"), root)
    assert layers[0].tint == "#ff0000"    # body tinted by skin
    assert layers[1].tint is None         # face is never tinted


def test_slot_with_no_art_contributes_nothing(tmp_path):
    """Shoes has an empty directory and the appearance has no shoes field,
    so it must not produce a layer."""
    root = _fake_tree(tmp_path)
    layers = resolve_layers(Appearance(), root)
    assert all("Shoes" not in str(l.frames_dir) for l in layers)


def test_future_slot_appears_once_the_appearance_carries_it(tmp_path):
    """The seam this phase exists to install: a hair field starts drawing
    hair with no change to resolve_layers itself."""
    root = _fake_tree(tmp_path)

    class Future(Appearance):
        pass

    future = Future()
    object.__setattr__(future, "hair", "spiky")
    object.__setattr__(future, "hair_color", "#333333")
    layers = resolve_layers(future, root)
    assert layers[-1].z == 40
    assert layers[-1].frames_dir == root / "Hair" / "spiky"
    assert layers[-1].tint == "#333333"


def test_missing_chosen_directory_is_skipped(tmp_path):
    root = _fake_tree(tmp_path)
    layers = resolve_layers(Appearance(body="doesnotexist"), root)
    assert all("Bodies" not in str(l.frames_dir) for l in layers)


def test_slot_options_lists_subdirectories(tmp_path):
    root = _fake_tree(tmp_path)
    manifest = load_manifest(root)
    body_slot = manifest["slots"][0]
    assert slot_options(root, body_slot) == ["round", "tall"]


def test_slot_options_empty_when_directory_absent(tmp_path):
    root = _fake_tree(tmp_path)
    missing = {"name": "outfit", "z": 20, "dir": "Outfits",
               "field": "outfit", "tint_field": None}
    assert slot_options(root, missing) == []


def test_real_sprite_tree_resolves(tmp_path):
    """Guards against the shipped manifest and generated art drifting apart."""
    layers = resolve_layers(Appearance(), REAL_SPRITES)
    assert [l.z for l in layers] == [0, 30]
    assert layers[0].tint == Appearance().skin


def test_real_body_options():
    assert body_options(REAL_SPRITES) == ["round", "slim", "tall"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_layers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'Src.layers'`

- [ ] **Step 3: Write minimal implementation**

Create `Src/layers.py`:

```python
"""Turn an Appearance into an ordered stack of drawable layers.

This module is the ONLY place that knows what a layer means. The compositor,
the preview, and SpriteWindow all consume an anonymous list of LayerSpec, so
adding hair or outfits later is a change here plus art — nothing downstream.

No Qt import: resolution is pure path logic and unit tests headless.
"""
import json
from dataclasses import dataclass
from pathlib import Path

MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class LayerSpec:
    frames_dir: Path   # the character dir; callers append the animation name
    tint: str | None   # hex color, or None to draw the art as authored
    z: int             # draw order, ascending = further back


def load_manifest(sprites_dir) -> dict:
    return json.loads((Path(sprites_dir) / MANIFEST_NAME).read_text())


def slot_options(sprites_dir, slot: dict) -> list[str]:
    """Available choices for a slot: the subdirectories of its directory.

    Discovery rather than declaration is what makes importing new art a
    content change instead of a code change.
    """
    folder = Path(sprites_dir) / slot["dir"]
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir() if p.is_dir())


def body_options(sprites_dir) -> list[str]:
    manifest = load_manifest(sprites_dir)
    for slot in manifest["slots"]:
        if slot["name"] == "body":
            return slot_options(sprites_dir, slot)
    return []


def resolve_layers(appearance, sprites_dir, manifest: dict | None = None
                   ) -> list[LayerSpec]:
    sprites_dir = Path(sprites_dir)
    manifest = manifest if manifest is not None else load_manifest(sprites_dir)
    specs: list[LayerSpec] = []
    for slot in manifest["slots"]:
        choice = getattr(appearance, slot["field"], None) or slot.get("default")
        if not choice:
            continue
        frames_dir = sprites_dir / slot["dir"] / choice
        if not frames_dir.is_dir():
            continue
        tint_field = slot.get("tint_field")
        tint = getattr(appearance, tint_field, None) if tint_field else None
        specs.append(LayerSpec(frames_dir=frames_dir, tint=tint, z=slot["z"]))
    return sorted(specs, key=lambda s: s.z)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_layers.py -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add Src/layers.py tests/test_layers.py
git commit -m "feat: slot discovery and appearance-to-layer resolution"
```

---

### Task 4: Frame compositing

Adds the drawing half: load each layer's frames, tint them, stack them. `SpriteWindow` is not rewired yet — that happens in Task 5.

**Files:**
- Modify: `Src/sprite_window.py` (add functions; leave `load_frames` and `SpriteWindow` in place)
- Test: `tests/test_sprite_frames.py` (append)

**Interfaces:**
- Consumes: `LayerSpec` from Task 3.
- Produces: `load_layer_frames(frames_dir, anim) -> list[QPixmap]`; `tinted(pix: QPixmap, color: str) -> QPixmap`; `composite_frames(layers: list[LayerSpec], anim: str) -> list[QPixmap]`. The first layer's frame count is canonical; shorter layers index modulo their own length.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sprite_frames.py`:

```python
def _qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_tint_replaces_color_and_keeps_alpha():
    _qt_app()
    from PySide6.QtGui import QPixmap, QColor
    from Src.sprite_window import tinted

    src = QPixmap(str(SPRITES_DIR / "Bodies" / "round" / "idle" / "0.png"))
    out = tinted(src, "#ff0000")
    img = out.toImage()
    # find an opaque pixel; it must now be pure red, still opaque
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() == 255:
                assert (c.red(), c.green(), c.blue()) == (255, 0, 0)
                return
    raise AssertionError("body silhouette had no opaque pixel")


def test_composite_stacks_layers_and_uses_base_frame_count():
    _qt_app()
    from Src.appearance import Appearance
    from Src.layers import resolve_layers
    from Src.sprite_window import composite_frames

    layers = resolve_layers(Appearance(skin="#00ff00"), SPRITES_DIR)
    walk = composite_frames(layers, "walk")
    # body has 4 walk frames, the face only 1 -> base count wins
    assert len(walk) == 4
    assert all(not p.isNull() for p in walk)


def test_composite_draws_face_over_tinted_body():
    """The face is untinted ink, so a green-skinned buddy must still have
    dark eye pixels — proof the face layer landed on top."""
    _qt_app()
    from Src.appearance import Appearance
    from Src.layers import resolve_layers
    from Src.sprite_window import composite_frames

    frames = composite_frames(
        resolve_layers(Appearance(skin="#00ff00"), SPRITES_DIR), "idle")
    img = frames[0].toImage()
    dark = sum(1 for y in range(img.height()) for x in range(img.width())
               if img.pixelColor(x, y).alpha() == 255
               and img.pixelColor(x, y).green() < 100)
    assert dark > 0, "face layer was not drawn over the body"


def test_composite_with_no_layers_returns_empty():
    _qt_app()
    from Src.sprite_window import composite_frames
    assert composite_frames([], "idle") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sprite_frames.py -v`
Expected: FAIL with `ImportError: cannot import name 'tinted' from 'Src.sprite_window'`

- [ ] **Step 3: Write minimal implementation**

In `Src/sprite_window.py`, add `QColor` to the existing `PySide6.QtGui` import so the line reads:

```python
from PySide6.QtGui import QPixmap, QPainter, QTransform, QColor
```

Then add these functions immediately after the existing `load_frames`:

```python
def load_layer_frames(frames_dir: Path, anim: str) -> list[QPixmap]:
    folder = Path(frames_dir) / anim
    if not folder.is_dir():
        return []
    files = sorted(folder.glob("*.png"), key=lambda p: int(p.stem))
    return [QPixmap(str(f)) for f in files]


def tinted(pix: QPixmap, color: str) -> QPixmap:
    """Recolor art while preserving its alpha.

    SourceIn keeps the destination alpha and replaces RGB, which is right for
    the flat silhouettes this project ships. Shaded art would want Multiply
    over a greyscale source instead.
    """
    out = pix.copy()
    p = QPainter(out)
    p.setCompositionMode(QPainter.CompositionMode_SourceIn)
    p.fillRect(out.rect(), QColor(color))
    p.end()
    return out


def composite_frames(layers, anim: str) -> list[QPixmap]:
    """Stack resolved layers back to front into finished frames.

    Called once per SpriteWindow, never per tick.
    """
    stacks = []
    for spec in layers:
        frames = load_layer_frames(spec.frames_dir, anim)
        if not frames:
            continue
        if spec.tint:
            frames = [tinted(f, spec.tint) for f in frames]
        stacks.append(frames)
    if not stacks:
        return []

    base = stacks[0]                 # the body drives the timeline
    size = base[0].size()
    out = []
    for i in range(len(base)):
        canvas = QPixmap(size)
        canvas.fill(Qt.transparent)
        p = QPainter(canvas)
        for frames in stacks:
            p.drawPixmap(0, 0, frames[i % len(frames)])
        p.end()
        out.append(canvas)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sprite_frames.py -v`
Expected: PASS — the 5 pre-existing tests plus 4 new ones

- [ ] **Step 5: Commit**

```bash
git add Src/sprite_window.py tests/test_sprite_frames.py
git commit -m "feat: tint and composite layered sprite frames"
```

---

### Task 5: Carry Appearance end to end

The type swap: `character: str` becomes `appearance` everywhere, including the wire. Atomic by necessity — a half-renamed wire format does not run. The menu emits a default `Appearance` for now; its controls arrive in Task 8.

**Files:**
- Modify: `Src/User.py`, `Src/world.py:15`, `Src/world.py:67-68`, `Src/sprite_window.py:41-56`, `Src/menu.py:19-20,55,62,72`, `Src/Connections.py:29-34`, `relay/room.py:30,33,38,43,50,54`, `relay/server.py:27,32`, `Src/app.py:72-78,90,95,132,135,142-144`
- Test: `tests/test_world.py`, `tests/test_room.py`, `tests/test_server.py`, `tests/test_menu.py`, `tests/test_sprite_frames.py`

**Interfaces:**
- Consumes: `Appearance` (Task 1), `resolve_layers` (Task 3), `composite_frames` (Task 4).
- Produces: `PlayerIdentity(name: str, appearance: Appearance)`; `Sprite(id, name, appearance: Appearance, ...)`; `World.add_member(id, name, appearance: Appearance)`; `SpriteWindow(appearance: Appearance, sprites_dir: Path)`; `NetClient.start_create(url, name, appearance: dict)` and `start_join(url, code, name, appearance: dict)`; `Registry.create_room(name, appearance: dict, send)` and `join_room(code, name, appearance: dict, send)`; menu signals `create_requested(str, object)` and `join_requested(str, str, object)` carrying an `Appearance`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_world.py`, replace the `character="cat"` usages. The first test becomes:

```python
from Src.appearance import Appearance


def test_identity_holds_name_and_appearance():
    ident = PlayerIdentity(name="Kain", appearance=Appearance(body="tall"))
    assert ident.name == "Kain"
    assert ident.appearance.body == "tall"
```

For the remaining five occurrences, replace `character="cat"` with `appearance=Appearance()` in the `Sprite(...)` and `World(Sprite(...))` constructions at lines 12, 21, 34, 43, and 58.

In `tests/test_room.py`, replace the two `"character"` payload fields:

```python
                         "members": [{"id": a_id, "name": "Kain",
                                      "appearance": {"body": "round",
                                                     "skin": "#e8b48c"}}]}
```

and

```python
                          "name": "Sam", "appearance": {"body": "tall",
                                                        "skin": "#a4673f"}}
```

Update the corresponding `create_room` / `join_room` calls in that file to pass those same dicts as the `appearance` argument instead of a `character` string.

In `tests/test_server.py`, replace every `character="cat"` with `appearance={"body": "round", "skin": "#e8b48c"}` and every `character="dog"` with `appearance={"body": "tall", "skin": "#a4673f"}`, including inside the expected `member_joined` assertion at line 35.

In `tests/test_menu.py`, delete `test_characters_nonempty` and the `CHARACTERS` import — the constant is gone. The file's remaining imports become:

```python
from Src.menu import validate_name, normalize_code
```

In `tests/test_sprite_frames.py`, update the window construction:

```python
    from Src.appearance import Appearance
    win = SpriteWindow(Appearance(), SPRITES_DIR)
```

Add a new test to `tests/test_world.py` proving remote appearance survives a round trip through a dict:

```python
def test_add_member_stores_appearance():
    world = World(Sprite(id="me", name="Kain", appearance=Appearance()))
    world.add_member("2", "Sam", Appearance.from_dict({"body": "slim"}))
    assert world.remotes["2"].appearance.body == "slim"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest -v`
Expected: FAIL — `TypeError: PlayerIdentity.__init__() got an unexpected keyword argument 'appearance'` and similar across the suite.

- [ ] **Step 3: Write the implementation**

`Src/User.py` — replace the whole file:

```python
from dataclasses import dataclass, field

from Src.appearance import Appearance


@dataclass
class PlayerIdentity:
    name: str
    appearance: Appearance = field(default_factory=Appearance)
```

`Src/world.py` — line 15, replace `character: str` with:

```python
    appearance: "Appearance" = field(default_factory=Appearance)
```

Add to the imports at the top of `Src/world.py`:

```python
from dataclasses import dataclass, field

from Src.appearance import Appearance
```

Note the field has a default, so it must move below `name` but above the other defaulted fields — it already is.

`Src/world.py` lines 67-68 become:

```python
    def add_member(self, id: str, name: str, appearance: Appearance) -> None:
        self.remotes[id] = Sprite(id=id, name=name, appearance=appearance)
```

`Src/sprite_window.py` — replace the `SpriteWindow.__init__` signature and frame setup (lines 41-56):

```python
    def __init__(self, appearance, sprites_dir: Path):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # macOS hides Qt.Tool windows whenever the app is not frontmost;
        # this keeps the sprite on screen even when another app has focus.
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)

        manifest = load_manifest(sprites_dir)
        self._fps = manifest.get("fps", 6)
        layers = resolve_layers(appearance, sprites_dir, manifest)
        self._frames = {
            "idle": composite_frames(layers, "idle"),
            "walk": composite_frames(layers, "walk"),
        }
```

Add to the imports of `Src/sprite_window.py`:

```python
from Src.layers import load_manifest, resolve_layers
```

Delete the now-unused `import json` line only if nothing else in the file uses it.

`Src/menu.py` — replace the signal declarations at lines 19-20:

```python
    create_requested = Signal(str, object)        # name, Appearance
    join_requested = Signal(str, str, object)     # code, name, Appearance
```

Delete the `CHARACTERS` constant and the `_char_group` radio block (lines 27-40 of the current file), and replace `_character()` at line 55 with:

```python
    def _appearance(self) -> Appearance:
        return self._appearance_value
```

Add `self._appearance_value = Appearance()` in `__init__` before the layout is built, and add the import:

```python
from Src.appearance import Appearance
```

Update the two emit sites (lines 62 and 72) to call `self._appearance()` instead of `self._character()`.

`Src/Connections.py` — lines 29-34:

```python
    def start_create(self, url: str, name: str, appearance: dict) -> None:
        self._hello = m.encode(m.CREATE_ROOM, name=name, appearance=appearance)
        self._start(url)

    def start_join(self, url: str, code: str, name: str,
                   appearance: dict) -> None:
        self._hello = m.encode(m.JOIN_ROOM, code=code, name=name,
                               appearance=appearance)
        self._start(url)
```

`relay/room.py` — rename the field in four places. Line 30:

```python
        return [{"id": mem["id"], "name": mem["name"],
                 "appearance": mem["appearance"]}
```

Line 33 signature and line 38 body:

```python
    async def create_room(self, name: str, appearance: dict, send
                          ) -> tuple[str, str]:
```
```python
        room["members"][mid] = {"id": mid, "name": name,
                                "appearance": appearance, "send": send}
```

Line 43 signature, line 50 body, line 54 broadcast:

```python
    async def join_room(self, code: str, name: str, appearance: dict, send
                        ) -> str | None:
```
```python
        room["members"][mid] = {"id": mid, "name": name,
                                "appearance": appearance, "send": send}
```
```python
                await mem["send"](m.encode(m.MEMBER_JOINED, id=mid,
                                           name=name, appearance=appearance))
```

`relay/server.py` — lines 27 and 32, swap the default from `""` to `{}`:

```python
                        msg.get("name", ""), msg.get("appearance", {}), send)
```
```python
                        msg.get("appearance", {}), send)
```

`Src/app.py` — lines 72-78:

```python
    def _on_create(self, name, appearance):
        self.identity = PlayerIdentity(name, appearance)
        self.net.start_create(self.relay_url, name, appearance.to_dict())

    def _on_join(self, code, name, appearance):
        self.identity = PlayerIdentity(name, appearance)
        self.net.start_join(self.relay_url, code, name, appearance.to_dict())
```

Lines 90 and 95 both become:

```python
            self._add_remote(mem["id"], mem["name"], mem["appearance"])
```

Line 132 (inside `_begin_world`):

```python
                     appearance=self.identity.appearance, y=FLOOR_FRACTION,
```

Line 135:

```python
        self.windows[your_id] = SpriteWindow(self.identity.appearance,
                                             SPRITES_DIR)
```

Lines 142-144:

```python
    def _add_remote(self, mid, name, appearance):
        appearance = Appearance.from_dict(appearance)
        self.world.add_member(mid, name, appearance)
        win = SpriteWindow(appearance, SPRITES_DIR)
```

Replace only those three lines. The poke wiring that follows them —
the default-arg-capture comment, `win.clicked.connect(...)`, and
`self.windows[mid] = win` (`Src/app.py:145-147`) — stays exactly as it is.

Add the import to `Src/app.py`:

```python
from Src.appearance import Appearance
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest -v`
Expected: PASS, full suite green

- [ ] **Step 5: Run the app end to end**

Run in one terminal: `python -m relay`
Run in two more: `BUDDIES_URL=ws://localhost:8765 python -m Src`

Create a room in one, join with the code in the other. Expected: two identical default buddies (round body, default skin, dark eyes) idle and walk on the desktop. Poking and chat still work.

- [ ] **Step 6: Commit**

```bash
git add Src/ relay/ tests/
git commit -m "refactor: carry Appearance end to end, replacing the character string"
```

---

### Task 6: Profile persistence

**Files:**
- Create: `Src/profile.py`
- Test: `tests/test_profile.py`

**Interfaces:**
- Consumes: `Appearance` from Task 1.
- Produces: `load_profile(path) -> tuple[str, Appearance]`; `save_profile(path, name: str, appearance: Appearance) -> None`; constant `DEFAULT_NAME: str`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_profile.py`:

```python
import json

from Src.appearance import Appearance, DEFAULT_SKIN
from Src.profile import load_profile, save_profile, DEFAULT_NAME


def test_round_trip(tmp_path):
    path = tmp_path / "profile.json"
    save_profile(path, "Kain", Appearance(body="slim", skin="#a4673f"))
    assert load_profile(path) == ("Kain", Appearance(body="slim",
                                                     skin="#a4673f"))


def test_missing_file_yields_defaults(tmp_path):
    assert load_profile(tmp_path / "nope.json") == (DEFAULT_NAME, Appearance())


def test_corrupt_json_yields_defaults(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text("{not json at all")
    assert load_profile(path) == (DEFAULT_NAME, Appearance())


def test_non_object_json_yields_defaults(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text("[1, 2, 3]")
    assert load_profile(path) == (DEFAULT_NAME, Appearance())


def test_unknown_appearance_field_is_ignored(tmp_path):
    """An appearance saved by a future build must still load here."""
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"name": "Sam",
                                "appearance": {"body": "tall",
                                               "hair": "spiky"}}))
    name, appearance = load_profile(path)
    assert name == "Sam"
    assert appearance == Appearance(body="tall", skin=DEFAULT_SKIN)


def test_non_string_name_falls_back(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"name": 42, "appearance": {}}))
    assert load_profile(path)[0] == DEFAULT_NAME


def test_save_creates_missing_directories(tmp_path):
    path = tmp_path / "nested" / "deeper" / "profile.json"
    save_profile(path, "Kain", Appearance())
    assert path.is_file()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_profile.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'Src.profile'`

- [ ] **Step 3: Write minimal implementation**

Create `Src/profile.py`:

```python
"""Remember the player's name and buddy between launches.

A broken profile must never stop the app from starting, so every failure
path falls back to defaults rather than raising. The path is passed in so
tests never touch the real config directory.
"""
import json
from pathlib import Path

from Src.appearance import Appearance

DEFAULT_NAME = ""


def load_profile(path) -> tuple[str, Appearance]:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return DEFAULT_NAME, Appearance()
    if not isinstance(data, dict):
        return DEFAULT_NAME, Appearance()
    name = data.get("name")
    if not isinstance(name, str):
        name = DEFAULT_NAME
    return name, Appearance.from_dict(data.get("appearance"))


def save_profile(path, name: str, appearance: Appearance) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"name": name,
                             "appearance": appearance.to_dict()}, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_profile.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add Src/profile.py tests/test_profile.py
git commit -m "feat: save and restore name and appearance between launches"
```

---

### Task 7: Preview and customizer widgets

**Files:**
- Create: `Src/customizer.py`
- Test: `tests/test_customizer.py`

**Interfaces:**
- Consumes: `Appearance`, `SKIN_PALETTE` (Task 1); `body_options` (Task 3); `composite_frames`, `resolve_layers`, `FrameCycler` (Task 4).
- Produces: `PreviewWidget(sprites_dir, appearance=None, scale=2)` with `.set_appearance(Appearance)`; `CustomizerPanel(sprites_dir, appearance=None)` with `.appearance() -> Appearance`, `.set_appearance(Appearance)`, and signal `appearance_changed(object)`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_customizer.py`:

```python
import os
from pathlib import Path

SPRITES_DIR = Path(__file__).resolve().parent.parent / "Sprites"


def _qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_preview_composites_on_construction():
    _qt_app()
    from Src.appearance import Appearance
    from Src.customizer import PreviewWidget

    w = PreviewWidget(SPRITES_DIR, Appearance())
    try:
        assert w.frame_count() > 0
    finally:
        w.close()
        w.deleteLater()


def test_preview_recomposites_on_appearance_change():
    _qt_app()
    from Src.appearance import Appearance
    from Src.customizer import PreviewWidget

    w = PreviewWidget(SPRITES_DIR, Appearance(skin="#ff0000"))
    try:
        before = w.current_pixmap().toImage()
        w.set_appearance(Appearance(skin="#0000ff"))
        after = w.current_pixmap().toImage()
        assert before != after, "changing skin must change the preview"
    finally:
        w.close()
        w.deleteLater()


def test_panel_exposes_current_appearance():
    _qt_app()
    from Src.appearance import Appearance
    from Src.customizer import CustomizerPanel

    p = CustomizerPanel(SPRITES_DIR, Appearance(body="tall", skin="#a4673f"))
    try:
        assert p.appearance() == Appearance(body="tall", skin="#a4673f")
    finally:
        p.close()
        p.deleteLater()


def test_choosing_a_body_emits_and_updates():
    _qt_app()
    from Src.appearance import Appearance
    from Src.customizer import CustomizerPanel

    p = CustomizerPanel(SPRITES_DIR, Appearance(body="round"))
    seen = []
    p.appearance_changed.connect(seen.append)
    try:
        p.select_body("slim")
        assert p.appearance().body == "slim"
        assert seen and seen[-1].body == "slim"
    finally:
        p.close()
        p.deleteLater()


def test_choosing_a_skin_emits_and_updates():
    _qt_app()
    from Src.appearance import Appearance, SKIN_PALETTE
    from Src.customizer import CustomizerPanel

    p = CustomizerPanel(SPRITES_DIR, Appearance())
    seen = []
    p.appearance_changed.connect(seen.append)
    target = SKIN_PALETTE[-1]
    try:
        p.select_skin(target)
        assert p.appearance().skin == target
        assert seen and seen[-1].skin == target
    finally:
        p.close()
        p.deleteLater()


def test_body_choices_come_from_the_sprite_tree():
    _qt_app()
    from Src.customizer import CustomizerPanel

    p = CustomizerPanel(SPRITES_DIR)
    try:
        assert p.body_choices() == ["round", "slim", "tall"]
    finally:
        p.close()
        p.deleteLater()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_customizer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'Src.customizer'`

- [ ] **Step 3: Write minimal implementation**

Create `Src/customizer.py`:

```python
"""Buddy customization: an animated preview plus the controls that drive it.

Controls are concrete rather than generated from the manifest. When hair and
outfits arrive they get their own widgets here; a generic slot-control factory
for slots that have no art yet would be speculative.
"""
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPixmap, QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QPushButton)

from Src.appearance import Appearance, SKIN_PALETTE
from Src.layers import body_options, resolve_layers
from Src.sprite_window import composite_frames, FrameCycler

PREVIEW_ANIM = "idle"
TICK_MS = 16


class PreviewWidget(QWidget):
    """Plays the idle loop of whatever appearance it is given."""

    def __init__(self, sprites_dir, appearance: Appearance | None = None,
                 scale: int = 2):
        super().__init__()
        self._sprites_dir = Path(sprites_dir)
        self._scale = scale
        self._frames: list[QPixmap] = []
        self._cycler = FrameCycler(0, 6)
        self.set_appearance(appearance or Appearance())
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(TICK_MS)

    def set_appearance(self, appearance: Appearance) -> None:
        layers = resolve_layers(appearance, self._sprites_dir)
        self._frames = composite_frames(layers, PREVIEW_ANIM)
        self._cycler = FrameCycler(len(self._frames), 6)
        if self._frames:
            size = self._frames[0].size()
            self.setFixedSize(size.width() * self._scale,
                              size.height() * self._scale)
        self.update()

    def frame_count(self) -> int:
        return len(self._frames)

    def current_pixmap(self) -> QPixmap:
        if not self._frames:
            return QPixmap()
        return self._frames[self._cycler.index]

    def _tick(self) -> None:
        self._cycler.advance(TICK_MS / 1000.0)
        self.update()

    def paintEvent(self, event) -> None:
        pix = self.current_pixmap()
        if pix.isNull():
            return
        p = QPainter(self)
        p.drawPixmap(self.rect(), pix)
        p.end()


class CustomizerPanel(QWidget):
    """Preview plus the body-type and skin-tone controls."""

    appearance_changed = Signal(object)   # Appearance

    def __init__(self, sprites_dir, appearance: Appearance | None = None):
        super().__init__()
        self._sprites_dir = Path(sprites_dir)
        self._appearance = appearance or Appearance()

        layout = QVBoxLayout(self)
        self._preview = PreviewWidget(self._sprites_dir, self._appearance)
        layout.addWidget(self._preview, alignment=Qt.AlignHCenter)

        layout.addWidget(QLabel("Body"))
        self._body = QComboBox()
        self._body.addItems(self.body_choices())
        if self._appearance.body in self.body_choices():
            self._body.setCurrentText(self._appearance.body)
        self._body.currentTextChanged.connect(self.select_body)
        layout.addWidget(self._body)

        layout.addWidget(QLabel("Skin"))
        swatches = QHBoxLayout()
        for color in SKIN_PALETTE:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(
                f"background-color: {color}; border: 1px solid #555;")
            btn.clicked.connect(
                lambda _checked=False, c=color: self.select_skin(c))
            swatches.addWidget(btn)
        layout.addLayout(swatches)

    def body_choices(self) -> list[str]:
        return body_options(self._sprites_dir)

    def appearance(self) -> Appearance:
        return self._appearance

    def set_appearance(self, appearance: Appearance) -> None:
        self._appearance = appearance
        self._preview.set_appearance(appearance)
        if appearance.body in self.body_choices():
            self._body.setCurrentText(appearance.body)

    def select_body(self, body: str) -> None:
        self._apply(replace(self._appearance, body=body))

    def select_skin(self, skin: str) -> None:
        self._apply(replace(self._appearance, skin=skin))

    def _apply(self, appearance: Appearance) -> None:
        if appearance == self._appearance:
            return
        self._appearance = appearance
        self._preview.set_appearance(appearance)
        self.appearance_changed.emit(appearance)
```

Note the swatch lambda binds `c=color` as a default argument — a bare closure would read the final loop value, the same trap already handled in `Src/app.py:146`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_customizer.py -v`
Expected: PASS, 6 tests

- [ ] **Step 5: Commit**

```bash
git add Src/customizer.py tests/test_customizer.py
git commit -m "feat: animated buddy preview and body/skin controls"
```

---

### Task 8: Wire the panel into the menu and load the profile

**Files:**
- Modify: `Src/menu.py`, `Src/app.py`
- Test: `tests/test_menu.py`

**Interfaces:**
- Consumes: `CustomizerPanel` (Task 7), `load_profile`/`save_profile` (Task 6).
- Produces: `MenuWindow(sprites_dir, name="", appearance=None)`; `AppController` reads the profile at startup and writes it on create/join.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_menu.py`:

```python
import os
from pathlib import Path

SPRITES_DIR = Path(__file__).resolve().parent.parent / "Sprites"


def _qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_menu_seeds_from_a_saved_profile():
    _qt_app()
    from Src.appearance import Appearance
    from Src.menu import MenuWindow

    w = MenuWindow(SPRITES_DIR, name="Kain",
                   appearance=Appearance(body="slim", skin="#a4673f"))
    try:
        assert w.name() == "Kain"
        assert w.appearance() == Appearance(body="slim", skin="#a4673f")
    finally:
        w.close()
        w.deleteLater()


def test_create_emits_current_appearance():
    _qt_app()
    from Src.menu import MenuWindow

    w = MenuWindow(SPRITES_DIR, name="Kain")
    seen = []
    w.create_requested.connect(lambda n, a: seen.append((n, a)))
    try:
        w.customizer.select_body("tall")
        w._on_create()
        assert seen[-1][0] == "Kain"
        assert seen[-1][1].body == "tall"
    finally:
        w.close()
        w.deleteLater()


def test_join_requires_a_code():
    _qt_app()
    from Src.menu import MenuWindow

    w = MenuWindow(SPRITES_DIR, name="Kain")
    seen = []
    w.join_requested.connect(lambda c, n, a: seen.append(c))
    try:
        w._on_join()
        assert seen == []
    finally:
        w.close()
        w.deleteLater()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_menu.py -v`
Expected: FAIL with `TypeError: MenuWindow.__init__() takes 1 positional argument but 2 were given`

- [ ] **Step 3: Write the implementation**

In `Src/menu.py`, replace `__init__` and the appearance accessor. The class body becomes:

```python
class MenuWindow(QWidget):
    create_requested = Signal(str, object)        # name, Appearance
    join_requested = Signal(str, str, object)     # code, name, Appearance

    def __init__(self, sprites_dir, name: str = "",
                 appearance: Appearance | None = None):
        super().__init__()
        self.setWindowTitle("Desktop Buddies")
        layout = QVBoxLayout(self)

        self._name = QLineEdit(placeholderText="Your name")
        self._name.setText(name)
        layout.addWidget(self._name)

        self.customizer = CustomizerPanel(sprites_dir, appearance)
        layout.addWidget(self.customizer)

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

    def name(self) -> str:
        return self._name.text().strip()

    def appearance(self) -> Appearance:
        return self.customizer.appearance()
```

Update the two emit methods to use the accessors:

```python
    def _on_create(self) -> None:
        if not validate_name(self._name.text()):
            self.show_error("Enter a name (1-20 chars).")
            return
        self.create_requested.emit(self.name(), self.appearance())

    def _on_join(self) -> None:
        if not validate_name(self._name.text()):
            self.show_error("Enter a name (1-20 chars).")
            return
        code = normalize_code(self._code.text())
        if not code:
            self.show_error("Enter a room code.")
            return
        self.join_requested.emit(code, self.name(), self.appearance())
```

Replace the radio-button imports with:

```python
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel)

from Src.appearance import Appearance
from Src.customizer import CustomizerPanel
```

Delete the leftover `_appearance_value` assignment added in Task 5 — `CustomizerPanel` now owns that state.

In `Src/app.py`, add the imports:

```python
from PySide6.QtCore import QStandardPaths
from Src.profile import load_profile, save_profile
```

Add a module-level helper below `SEND_INTERVAL`:

```python
def profile_path() -> Path:
    root = QStandardPaths.writableLocation(
        QStandardPaths.AppConfigLocation) or str(Path.home() / ".config")
    return Path(root) / "desktop-buddies" / "profile.json"
```

In `AppController.__init__`, replace the `self.menu = MenuWindow()` line with:

```python
        self.profile_path = profile_path()
        saved_name, saved_appearance = load_profile(self.profile_path)
        self.menu = MenuWindow(SPRITES_DIR, saved_name, saved_appearance)
```

`QApplication` must exist before `QStandardPaths` is queried; it already does, since `self.app` is assigned on the first line of `__init__`.

Save the profile at the moment appearance is locked in — extend both menu handlers:

```python
    def _on_create(self, name, appearance):
        self.identity = PlayerIdentity(name, appearance)
        save_profile(self.profile_path, name, appearance)
        self.net.start_create(self.relay_url, name, appearance.to_dict())

    def _on_join(self, code, name, appearance):
        self.identity = PlayerIdentity(name, appearance)
        save_profile(self.profile_path, name, appearance)
        self.net.start_join(self.relay_url, code, name, appearance.to_dict())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest -v`
Expected: PASS, full suite green

- [ ] **Step 5: Verify the preview and persistence by hand**

Run: `python -m relay` in one terminal, `BUDDIES_URL=ws://localhost:8765 python -m Src` in another.

Expected: the menu shows an animated buddy above a Body dropdown and eight skin swatches. Changing either updates the preview immediately. Create a room, quit, relaunch — the name and buddy come back. Then launch a second client, pick a different body and skin, and join: the two desktop sprites look different from each other.

- [ ] **Step 6: Commit**

```bash
git add Src/menu.py Src/app.py tests/test_menu.py
git commit -m "feat: customizer panel in the launch menu, seeded from saved profile"
```

---

### Task 9: Retire the old sprite tree and update docs

**Files:**
- Delete: `Sprites/placeholder_cat/`, `Sprites/placeholder_dog/`, `Sprites/placeholder_blob/`
- Modify: `Src/sprite_window.py` (drop `load_frames`), `CLAUDE.md`
- Test: full suite

**Interfaces:**
- Consumes: everything above.
- Produces: no new interfaces.

- [ ] **Step 1: Confirm nothing references the old art or the old loader**

Run:

```bash
grep -rn "placeholder_cat\|placeholder_dog\|placeholder_blob\|load_frames" --include="*.py" --include="*.md" . | grep -v __pycache__
```

Expected: only the definition of `load_frames` in `Src/sprite_window.py` and any mentions inside `docs/superpowers/specs/` (historical specs — leave those alone). If a live code reference appears, fix it before continuing.

- [ ] **Step 2: Delete the old art and the dead loader**

```bash
git rm -r Sprites/placeholder_cat Sprites/placeholder_dog Sprites/placeholder_blob
```

Delete the `load_frames` function from `Src/sprite_window.py` — `load_layer_frames` replaced it.

- [ ] **Step 3: Update CLAUDE.md**

In the key module map table, add these rows after the `Src/world.py` row:

```markdown
| `Src/appearance.py` | `Appearance` value object + skin palette. Forward-compatible `from_dict`. |
| `Src/layers.py` | Manifest, slot discovery, `resolve_layers()`. **The only place that knows what a layer means.** |
| `Src/profile.py` | Load/save the player's name and appearance. |
| `Src/customizer.py` | `PreviewWidget` + `CustomizerPanel` (body type, skin color). |
```

In the Conventions section, add:

```markdown
- A buddy's look is an **`Appearance`**, not a character name. It travels the
  wire as a plain dict and the relay never inspects it, so new customization
  slots are a client-only change.
- Sprite art is **layered**: `Sprites/manifest.json` declares slots and draw
  order, and a slot's options are the subdirectories of its folder. Bodies are
  authored white and tinted at load. Dropping in `Sprites/Hair/<style>/` adds
  that style with no code change.
```

- [ ] **Step 4: Run the full suite and the app**

Run: `python -m pytest -v`
Expected: PASS

Run: `python tools/make_placeholder_sprites.py && python -m pytest -v`
Expected: regenerating art from scratch still leaves the suite green.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: retire flat placeholder characters, document the layer system"
```
