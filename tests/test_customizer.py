import os
from pathlib import Path

SPRITES_DIR = Path(__file__).resolve().parent.parent / "Sprites"


def _qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_preview_composites_on_construction():
    _qt_app()
    from Src.appearance import Appearance
    from Src.customizer import PreviewWidget

    w = PreviewWidget(SPRITES_DIR, Appearance())
    try:
        assert w.frame_count() > 0
    finally:
        w.close()
        w.deleteLater()


def test_preview_recomposites_on_appearance_change():
    _qt_app()
    from Src.appearance import Appearance
    from Src.customizer import PreviewWidget

    w = PreviewWidget(SPRITES_DIR, Appearance(skin="#ff0000"))
    try:
        before = w.current_pixmap().toImage()
        w.set_appearance(Appearance(skin="#0000ff"))
        after = w.current_pixmap().toImage()
        assert before != after, "changing skin must change the preview"
    finally:
        w.close()
        w.deleteLater()


def test_panel_exposes_current_appearance():
    _qt_app()
    from Src.appearance import Appearance
    from Src.customizer import CustomizerPanel

    p = CustomizerPanel(SPRITES_DIR, Appearance(body="tall", skin="#a4673f"))
    try:
        assert p.appearance() == Appearance(body="tall", skin="#a4673f")
    finally:
        p.close()
        p.deleteLater()


def test_choosing_a_body_emits_and_updates():
    _qt_app()
    from Src.appearance import Appearance
    from Src.customizer import CustomizerPanel

    p = CustomizerPanel(SPRITES_DIR, Appearance(body="round"))
    seen = []
    p.appearance_changed.connect(seen.append)
    try:
        p.select_body("slim")
        assert p.appearance().body == "slim"
        assert seen and seen[-1].body == "slim"
    finally:
        p.close()
        p.deleteLater()


def test_choosing_a_skin_emits_and_updates():
    _qt_app()
    from Src.appearance import Appearance, SKIN_PALETTE
    from Src.customizer import CustomizerPanel

    p = CustomizerPanel(SPRITES_DIR, Appearance())
    seen = []
    p.appearance_changed.connect(seen.append)
    target = SKIN_PALETTE[-1]
    try:
        p.select_skin(target)
        assert p.appearance().skin == target
        assert seen and seen[-1].skin == target
    finally:
        p.close()
        p.deleteLater()


def test_body_choices_come_from_the_sprite_tree():
    _qt_app()
    from Src.customizer import CustomizerPanel

    p = CustomizerPanel(SPRITES_DIR)
    try:
        assert p.body_choices() == ["round", "slim", "tall"]
    finally:
        p.close()
        p.deleteLater()
