import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from Src.chat_input import ChatInputWindow  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def test_emits_sanitized_text():
    _app()
    w = ChatInputWindow()
    got = []
    w.submitted.connect(got.append)
    w.edit.setText("  hi   there  ")
    w._submit()
    assert got == ["hi there"]


def test_ignores_empty_input():
    _app()
    w = ChatInputWindow()
    got = []
    w.submitted.connect(got.append)
    w.edit.setText("     ")
    w._submit()
    assert got == []
