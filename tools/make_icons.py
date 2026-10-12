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
