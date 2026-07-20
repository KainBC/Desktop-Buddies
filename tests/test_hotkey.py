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


def test_parse_combo_reads_modifiers_and_key():
    from Src._hotkey_darwin import (
        parse_combo, _CMD, _SHIFT, _CONTROL)

    keycode, mods = parse_combo("<cmd>+<shift>+b")
    assert keycode == 11                       # kVK_ANSI_B
    assert mods == _CMD | _SHIFT

    keycode, mods = parse_combo("<ctrl>+<shift>+b")
    assert keycode == 11
    assert mods == _CONTROL | _SHIFT


def test_parse_combo_rejects_bad_input():
    from Src._hotkey_darwin import parse_combo

    assert parse_combo("not-a-real-combo!!") is None   # unknown token
    assert parse_combo("<cmd>+<shift>") is None        # no non-modifier key
    assert parse_combo("<cmd>+a+b") is None            # two non-modifier keys
    assert parse_combo("") is None
