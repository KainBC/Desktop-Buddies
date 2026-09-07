import os
from pathlib import Path

import pytest

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


SPRITES_DIR = Path(__file__).resolve().parent.parent / "Sprites"


def test_sprite_window_stays_visible_when_app_inactive():
    """On macOS a Qt.Tool window is hidden whenever the app is not frontmost.
    WA_MacAlwaysShowToolWindow keeps the sprite on screen regardless."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    from Src.sprite_window import SpriteWindow

    from Src.appearance import Appearance
    win = SpriteWindow(Appearance(), SPRITES_DIR)
    try:
        assert win.testAttribute(Qt.WA_MacAlwaysShowToolWindow)
    finally:
        win.close()
        win.deleteLater()


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
