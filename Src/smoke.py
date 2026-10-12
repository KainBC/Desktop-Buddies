"""`--smoke-test`: prove a build can start, without showing anything.

CI runs this against the *packaged* binary, so a data file or hidden import
PyInstaller missed fails the build instead of a user's first launch. It
touches everything a launch needs except the network.
"""
import os
import sys
from pathlib import Path

from Src.version import VERSION


def run_smoke_test() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication(sys.argv[:1])  # noqa: F841

        import certifi
        from Src import resources
        from Src.appearance import Appearance
        from Src.layers import load_manifest, resolve_layers
        from Src.menu import MenuWindow
        from Src.sprite_window import composite_frames

        root = resources.sprites_dir()
        manifest = load_manifest(root)
        layers = resolve_layers(Appearance(), root, manifest)
        for anim in ("idle", "walk"):
            if not composite_frames(layers, anim):
                raise RuntimeError(f"no {anim!r} frames under {root}")

        if not Path(certifi.where()).is_file():
            raise RuntimeError("certifi CA bundle missing")

        menu = MenuWindow(root)
        menu.close()
        menu.deleteLater()

        import Src.app  # noqa: F401  (pulls in every client module)
        if sys.platform == "darwin":
            import Src._hotkey_darwin  # noqa: F401
        elif sys.platform == "win32":
            import pynput.keyboard  # noqa: F401
        # Linux: pynput's X backend refuses to import without a display, and
        # the hotkey already degrades gracefully, so it isn't checked here.
    except Exception as exc:                          # noqa: BLE001
        print(f"desktop-buddies {VERSION} smoke test FAILED: {exc!r}",
              file=sys.stderr)
        return 1
    print(f"desktop-buddies {VERSION} ok")
    return 0
