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
