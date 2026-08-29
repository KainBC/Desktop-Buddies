import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from Src.Connections import NetClient  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


def test_dispatch_chat_emits_signal():
    _app()
    nc = NetClient()
    got = []
    nc.chat_received.connect(got.append)
    nc._dispatch({"type": "chat", "id": "3", "text": "hi"})
    assert got == [{"type": "chat", "id": "3", "text": "hi"}]


def test_dispatch_poke_emits_signal():
    _app()
    nc = NetClient()
    got = []
    nc.poke_received.connect(got.append)
    nc._dispatch({"type": "poke", "id": "3", "target_id": "7"})
    assert got == [{"type": "poke", "id": "3", "target_id": "7"}]
