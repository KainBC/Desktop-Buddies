import sys

from PySide6.QtCore import QObject, Signal

DEFAULT_HOTKEY = "<cmd>+<shift>+b" if sys.platform == "darwin" \
    else "<ctrl>+<shift>+b"


class GlobalHotkey(QObject):
    """Wraps pynput's global hotkey listener. Fails gracefully: if pynput is
    unavailable or the OS denies the listener (e.g. macOS Accessibility not
    granted), start() returns False and the app keeps working without it."""

    activated = Signal()

    def __init__(self, combo: str = DEFAULT_HOTKEY):
        super().__init__()
        self._combo = combo
        self._listener = None

    def start(self) -> bool:
        try:
            from pynput import keyboard
        except Exception as exc:                       # noqa: BLE001
            print(f"[hotkey] pynput unavailable, global hotkey disabled: {exc}")
            return False
        try:
            self._listener = keyboard.GlobalHotKeys(
                {self._combo: self.activated.emit})
            self._listener.start()
            return True
        except Exception as exc:                       # noqa: BLE001
            print(f"[hotkey] could not register global hotkey: {exc}")
            self._listener = None
            return False

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
