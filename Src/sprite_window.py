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
        # macOS hides Qt.Tool windows whenever the app is not frontmost;
        # this keeps the sprite on screen even when another app has focus.
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)

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
