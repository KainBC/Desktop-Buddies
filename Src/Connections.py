import asyncio
import threading

import websockets
from PySide6.QtCore import QObject, Signal

from shared import messages as m


class NetClient(QObject):
    connected = Signal()
    disconnected = Signal()
    error_occurred = Signal(str)
    room_created = Signal(str, str)      # code, your_id
    room_joined = Signal(str, list)      # your_id, members
    member_joined = Signal(dict)
    member_left = Signal(str)
    remote_state = Signal(dict)

    def __init__(self):
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ws = None
        self._thread: threading.Thread | None = None
        self._hello: str | None = None   # first message to send on connect

    # ---- public API (called from the Qt/UI thread) ----
    def start_create(self, url: str, name: str, character: str) -> None:
        self._hello = m.encode(m.CREATE_ROOM, name=name, character=character)
        self._start(url)

    def start_join(self, url: str, code: str, name: str, character: str) -> None:
        self._hello = m.encode(m.JOIN_ROOM, code=code, name=name, character=character)
        self._start(url)

    def send_state(self, id: str, x: float, y: float, facing: int, anim: str) -> None:
        raw = m.encode(m.STATE, id=id, x=x, y=y, facing=facing, anim=anim)
        self._submit(raw)

    def stop(self) -> None:
        if self._loop and self._ws:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self._ws.close()))

    # ---- internals ----
    def _start(self, url: str) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, args=(url,), daemon=True)
        self._thread.start()

    def _submit(self, raw: str) -> None:
        if self._loop and self._ws:
            self._loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(self._ws.send(raw)))

    def _run(self, url: str) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._session(url))
        except Exception as exc:                      # noqa: BLE001
            self.error_occurred.emit(str(exc))
        finally:
            self.disconnected.emit()

    async def _session(self, url: str) -> None:
        async with websockets.connect(url) as ws:
            self._ws = ws
            self.connected.emit()
            await ws.send(self._hello)
            async for raw in ws:
                self._dispatch(m.decode(raw))

    def _dispatch(self, msg: dict | None) -> None:
        if msg is None:
            return
        t = msg.get("type")
        if t == m.ROOM_CREATED:
            self.room_created.emit(msg["code"], msg["your_id"])
        elif t == m.ROOM_JOINED:
            self.room_joined.emit(msg["your_id"], msg["members"])
        elif t == m.MEMBER_JOINED:
            self.member_joined.emit(msg)
        elif t == m.MEMBER_LEFT:
            self.member_left.emit(msg["id"])
        elif t == m.STATE:
            self.remote_state.emit(msg)
        elif t == m.ERROR:
            self.error_occurred.emit(msg.get("reason", "error"))
