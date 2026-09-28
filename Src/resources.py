"""Where bundled data lives, in a source checkout or a PyInstaller build."""
import sys
from pathlib import Path


def sprites_dir() -> Path:
    """The `Sprites/` directory.

    PyInstaller unpacks data files under `sys._MEIPASS` and sets that
    attribute only in a frozen app; a source checkout keeps `Sprites/` at
    the repo root, next to `Src/`.
    """
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root) / "Sprites"
    return Path(__file__).resolve().parent.parent / "Sprites"
