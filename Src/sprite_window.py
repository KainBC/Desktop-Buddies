from pathlib import Path

from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QPixmap, QPainter, QTransform, QColor
from PySide6.QtWidgets import QWidget

from Src.layers import load_manifest, resolve_layers


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

    # `stacks[0]` is the lowest-z layer that actually has frames for this
    # anim (ordinarily the body, since body is z=0). Its frame count drives
    # the timeline every other layer loops or truncates against. A body
    # missing art for this anim demotes the base to the next layer up --
    # e.g. a body with no walk/ art would let a 1-frame face become the
    # walk base, so the buddy would render as floating eyes.
    base = stacks[0]
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


class SpriteWindow(QWidget):
    clicked = Signal()

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
        self._anim = "idle"
        self._facing = 1
        self._cycler = FrameCycler(len(self._frames["idle"]), self._fps)
        if self._frames["idle"]:
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
