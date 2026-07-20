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
