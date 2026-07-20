import sys

from PySide6.QtCore import QObject, Signal

DEFAULT_HOTKEY = "<cmd>+<shift>+b" if sys.platform == "darwin" \
    else "<ctrl>+<shift>+b"


class GlobalHotkey(QObject):
    """System-wide hotkey that emits :attr:`activated` when pressed.

    macOS uses a native Carbon ``RegisterEventHotKey`` (see
    :mod:`Src._hotkey_darwin`); other platforms use pynput. Both fail
    gracefully: if the backend is unavailable or the OS refuses the hotkey,
    :meth:`start` returns ``False`` and the app keeps working (clicking a
    sprite still opens the composer)."""

    activated = Signal()

    def __init__(self, combo: str = DEFAULT_HOTKEY):
        super().__init__()
        self._combo = combo
        self._backend = None

    def start(self) -> bool:
        if sys.platform == "darwin":
            return self._start_darwin()
        return self._start_pynput()

    def _start_darwin(self) -> bool:
        try:
            from Src._hotkey_darwin import CarbonHotkey, parse_combo
        except Exception as exc:                       # noqa: BLE001
            print(f"[hotkey] macOS backend unavailable: {exc}")
            return False
        parsed = parse_combo(self._combo)
        if parsed is None:
            print(f"[hotkey] cannot parse combo {self._combo!r}")
            return False
        backend = CarbonHotkey(self.activated.emit)
        try:
            ok = backend.register(*parsed)
        except Exception as exc:                       # noqa: BLE001
            print(f"[hotkey] could not register global hotkey: {exc}")
            return False
        if ok:
            self._backend = backend
        return ok

    def _start_pynput(self) -> bool:
        try:
            from pynput import keyboard
        except Exception as exc:                       # noqa: BLE001
            print(f"[hotkey] pynput unavailable, global hotkey disabled: {exc}")
            return False
        try:
            self._backend = keyboard.GlobalHotKeys(
                {self._combo: self.activated.emit})
            self._backend.start()
            return True
        except Exception as exc:                       # noqa: BLE001
            print(f"[hotkey] could not register global hotkey: {exc}")
            self._backend = None
            return False

    def stop(self) -> None:
        if self._backend is None:
            return
        try:
            if sys.platform == "darwin":
                self._backend.unregister()
            else:
                self._backend.stop()
        finally:
            self._backend = None
