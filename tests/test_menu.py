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


def test_menu_shows_the_running_version():
    _qt_app()
    from PySide6.QtWidgets import QLabel
    from Src.menu import MenuWindow
    from Src.version import VERSION

    w = MenuWindow(SPRITES_DIR)
    try:
        texts = [label.text() for label in w.findChildren(QLabel)]
        assert f"v{VERSION}" in texts
    finally:
        w.close()
        w.deleteLater()


def test_update_notice_only_for_a_newer_release():
    _qt_app()
    from Src.menu import MenuWindow
    from Src.updates import DOWNLOAD_PAGE

    w = MenuWindow(SPRITES_DIR)
    try:
        assert w.update_notice() == ""
        for tag in ("v1.0.0", "v0.9.0", "garbage", "v9.9.9-beta"):
            w.show_update(tag)
            assert w.update_notice() == "", tag
        w.show_update("v9.10.0")
        notice = w.update_notice()
        assert "v9.10.0" in notice
        assert DOWNLOAD_PAGE in notice
    finally:
        w.close()
        w.deleteLater()
