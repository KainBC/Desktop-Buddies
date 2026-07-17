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

    win = SpriteWindow("placeholder_cat", SPRITES_DIR)
    try:
        assert win.testAttribute(Qt.WA_MacAlwaysShowToolWindow)
    finally:
        win.close()
        win.deleteLater()
