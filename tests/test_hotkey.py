import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from Src.hotkey import GlobalHotkey, DEFAULT_HOTKEY  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def test_default_hotkey_is_a_combo_string():
    assert "+" in DEFAULT_HOTKEY and DEFAULT_HOTKEY.endswith("b")


def test_activated_signal_is_connectable():
    _app()
    hk = GlobalHotkey()
    fired = []
    hk.activated.connect(lambda: fired.append(True))
    hk.activated.emit()
    assert fired == [True]


def test_bad_combo_fails_gracefully():
    _app()
    hk = GlobalHotkey(combo="not-a-real-combo!!")
    assert hk.start() is False   # must not raise
    hk.stop()                    # safe even though nothing started


def test_stop_before_start_is_noop():
    _app()
    hk = GlobalHotkey()
    hk.stop()                    # must not raise
