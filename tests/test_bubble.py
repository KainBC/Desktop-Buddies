import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from Src.bubble import BubbleWindow  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def test_bubble_expires_after_lifetime():
    _app()
    b = BubbleWindow(hold=0.1, fade=0.1)
    b.set_text("hello")
    assert not b.done
    b.tick(0.1)      # end of hold
    b.tick(0.1)      # end of fade
    assert b.done
    b.close()


def test_set_text_resets_lifetime():
    _app()
    b = BubbleWindow(hold=0.1, fade=0.1)
    b.set_text("a")
    b.tick(0.2)      # would be done
    assert b.done
    b.set_text("b")  # replaces + resets
    assert not b.done
    b.close()
