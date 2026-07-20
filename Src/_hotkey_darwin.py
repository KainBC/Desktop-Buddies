"""Native macOS global hotkey via Carbon ``RegisterEventHotKey``.

pynput's macOS backend runs a ``CGEventTap`` on a *background* thread and
translates key codes with ``CGEventKeyboardGetUnicodeString``. On modern macOS
that routes into the Text Input Source manager, which asserts it must run on the
main thread -> ``SIGTRAP`` (the whole process aborts, so the try/except around
``start()`` never sees it).

Carbon's ``RegisterEventHotKey`` is the supported way to get a system-wide
hotkey: it needs no Accessibility grant and delivers its event on the **main**
thread through the application's Carbon event target, which Qt's Cocoa run loop
pumps. No cross-thread call happens, so there is no crash.

The combo parser (:func:`parse_combo`) is pure Python and unit tested headless;
the ctypes wiring in :class:`CarbonHotkey` is only exercised on a real desktop.
"""
import ctypes
import ctypes.util

# --- Carbon virtual key codes (kVK_ANSI_*), enough for letters + digits. ----
_VK = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8,
    "v": 9, "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17,
    "o": 31, "u": 32, "i": 34, "p": 35, "l": 37, "j": 38, "k": 40, "n": 45,
    "m": 46,
    "1": 18, "2": 19, "3": 20, "4": 21, "6": 22, "5": 23, "9": 25, "7": 26,
    "8": 28, "0": 29, "space": 49,
}

# --- Carbon modifier masks (Events.h). --------------------------------------
_CMD = 0x0100
_SHIFT = 0x0200
_OPTION = 0x0800
_CONTROL = 0x1000

_MODS = {
    "cmd": _CMD, "command": _CMD, "cmd_l": _CMD, "cmd_r": _CMD,
    "shift": _SHIFT, "shift_l": _SHIFT, "shift_r": _SHIFT,
    "alt": _OPTION, "option": _OPTION, "alt_l": _OPTION, "alt_r": _OPTION,
    "ctrl": _CONTROL, "control": _CONTROL, "ctrl_l": _CONTROL,
    "ctrl_r": _CONTROL,
}


def parse_combo(combo):
    """Parse a pynput-style combo (``"<cmd>+<shift>+b"``) into
    ``(keycode, modifiers)`` for Carbon.

    Returns ``None`` if the combo is empty, contains an unknown token, or does
    not name exactly one non-modifier key -- callers treat ``None`` as "cannot
    register" and fail gracefully.
    """
    mods = 0
    keycode = None
    for raw in combo.split("+"):
        token = raw.strip().lower().lstrip("<").rstrip(">")
        if not token:
            return None
        if token in _MODS:
            mods |= _MODS[token]
        elif token in _VK:
            if keycode is not None:
                return None            # more than one non-modifier key
            keycode = _VK[token]
        else:
            return None                # unknown token
    if keycode is None:
        return None                    # modifiers only, no key
    return keycode, mods


# --- ctypes bindings for the Carbon Event Manager. --------------------------
class _EventTypeSpec(ctypes.Structure):
    _fields_ = [("eventClass", ctypes.c_uint32), ("eventKind", ctypes.c_uint32)]


class _EventHotKeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("id", ctypes.c_uint32)]


# OSStatus (*)(EventHandlerCallRef, EventRef, void *userData)
_HANDLER = ctypes.CFUNCTYPE(
    ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

_K_EVENT_CLASS_KEYBOARD = 0x6B657962   # 'keyb'
_K_EVENT_HOTKEY_PRESSED = 6
_NO_ERR = 0


def _load_carbon():
    path = ctypes.util.find_library("Carbon") \
        or "/System/Library/Frameworks/Carbon.framework/Carbon"
    carbon = ctypes.CDLL(path)
    carbon.GetApplicationEventTarget.restype = ctypes.c_void_p
    carbon.InstallEventHandler.argtypes = [
        ctypes.c_void_p, _HANDLER, ctypes.c_uint32,
        ctypes.POINTER(_EventTypeSpec), ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p)]
    carbon.InstallEventHandler.restype = ctypes.c_int32
    carbon.RegisterEventHotKey.argtypes = [
        ctypes.c_uint32, ctypes.c_uint32, _EventHotKeyID,
        ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]
    carbon.RegisterEventHotKey.restype = ctypes.c_int32
    carbon.UnregisterEventHotKey.argtypes = [ctypes.c_void_p]
    carbon.UnregisterEventHotKey.restype = ctypes.c_int32
    carbon.RemoveEventHandler.argtypes = [ctypes.c_void_p]
    carbon.RemoveEventHandler.restype = ctypes.c_int32
    return carbon


class CarbonHotkey:
    """Registers a single global hotkey and calls ``on_activate`` when pressed.

    All calls happen on the main thread; the handler callback is invoked by the
    Carbon event dispatcher that Qt's run loop pumps, so ``on_activate`` runs on
    the Qt thread and may touch Qt objects directly.
    """

    def __init__(self, on_activate):
        self._on_activate = on_activate
        self._carbon = None
        self._hotkey_ref = None
        self._handler_ref = None
        self._callback = None          # keep the UPP alive while registered

    def register(self, keycode, modifiers) -> bool:
        carbon = _load_carbon()
        target = carbon.GetApplicationEventTarget()

        def _cb(_call_ref, _event, _user):
            try:
                self._on_activate()
            except Exception:          # noqa: BLE001 - never let it reach C
                pass
            return _NO_ERR

        callback = _HANDLER(_cb)
        spec = _EventTypeSpec(_K_EVENT_CLASS_KEYBOARD, _K_EVENT_HOTKEY_PRESSED)
        handler_ref = ctypes.c_void_p()
        if carbon.InstallEventHandler(
                target, callback, 1, ctypes.byref(spec), None,
                ctypes.byref(handler_ref)) != _NO_ERR:
            return False

        hotkey_id = _EventHotKeyID(0x42554459, 1)   # 'BUDY'
        hotkey_ref = ctypes.c_void_p()
        if carbon.RegisterEventHotKey(
                keycode, modifiers, hotkey_id, target, 0,
                ctypes.byref(hotkey_ref)) != _NO_ERR:
            carbon.RemoveEventHandler(handler_ref)
            return False

        self._carbon = carbon
        self._callback = callback
        self._handler_ref = handler_ref
        self._hotkey_ref = hotkey_ref
        return True

    def unregister(self) -> None:
        if self._carbon is None:
            return
        if self._hotkey_ref is not None:
            self._carbon.UnregisterEventHotKey(self._hotkey_ref)
            self._hotkey_ref = None
        if self._handler_ref is not None:
            self._carbon.RemoveEventHandler(self._handler_ref)
            self._handler_ref = None
        self._callback = None
        self._carbon = None
