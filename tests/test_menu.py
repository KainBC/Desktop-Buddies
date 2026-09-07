import os
from pathlib import Path

from Src.menu import validate_name, normalize_code

SPRITES_DIR = Path(__file__).resolve().parent.parent / "Sprites"


def _qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_validate_name():
    assert validate_name("Kain")
    assert not validate_name("   ")
    assert not validate_name("")
    assert not validate_name("x" * 21)


def test_normalize_code():
    assert normalize_code("  plum-42 ") == "PLUM-42"


def test_menu_seeds_from_a_saved_profile():
    _qt_app()
    from Src.appearance import Appearance
    from Src.menu import MenuWindow

    w = MenuWindow(SPRITES_DIR, name="Kain",
                   appearance=Appearance(body="slim", skin="#a4673f"))
    try:
        assert w.name() == "Kain"
        assert w.appearance() == Appearance(body="slim", skin="#a4673f")
    finally:
        w.close()
        w.deleteLater()


def test_create_emits_current_appearance():
    _qt_app()
    from Src.menu import MenuWindow

    w = MenuWindow(SPRITES_DIR, name="Kain")
    seen = []
    w.create_requested.connect(lambda n, a: seen.append((n, a)))
    try:
        w.customizer.select_body("tall")
        w._on_create()
        assert seen[-1][0] == "Kain"
        assert seen[-1][1].body == "tall"
    finally:
        w.close()
        w.deleteLater()


def test_join_requires_a_code():
    _qt_app()
    from Src.menu import MenuWindow

    w = MenuWindow(SPRITES_DIR, name="Kain")
    seen = []
    w.join_requested.connect(lambda c, n, a: seen.append(c))
    try:
        w._on_join()
        assert seen == []
    finally:
        w.close()
        w.deleteLater()
