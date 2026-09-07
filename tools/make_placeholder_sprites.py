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
    body type. Real art would ship a face per body.

    0.45 is not arbitrary: the shortest body ("round") starts at y=22.3, so
    anything above that floats the eyes off the head. 0.45 -> y=28.8 lands
    inside all three."""
    img = _canvas()
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(INK))
    eye_y = SIZE * 0.45
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
