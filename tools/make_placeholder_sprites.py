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
