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


import socket  # noqa: E402
import ssl  # noqa: E402
from pathlib import Path  # noqa: E402

import certifi  # noqa: E402

from Src.Connections import ssl_context_for  # noqa: E402
from Src.__main__ import DEFAULT_RELAY_URL, relay_url  # noqa: E402


def test_plain_ws_gets_no_ssl_context():
    assert ssl_context_for("ws://localhost:8765") is None


def test_wss_verifies_against_certifi():
    ctx = ssl_context_for("wss://example.fly.dev")
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname
    assert Path(certifi.where()).is_file()


def test_default_relay_is_hosted_wss():
    assert DEFAULT_RELAY_URL.startswith("wss://")
    assert relay_url({}) == DEFAULT_RELAY_URL
    assert relay_url({"BUDDIES_URL": "ws://localhost:8765"}) == \
        "ws://localhost:8765"


def test_unreachable_relay_reports_error_and_can_retry():
    with socket.socket() as s:            # grab a port nothing listens on
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    url = f"ws://127.0.0.1:{port}"

    nc = NetClient()
    errors, drops = [], []
    nc.error_occurred.connect(errors.append)
    nc.disconnected.connect(lambda: drops.append(True))

    app = _app()
    nc.start_create(url, "Kain", {})
    nc._thread.join(timeout=15)
    app.processEvents()       # signals from the net thread may be queued
    assert errors and drops == [True]

    first = nc._thread
    nc.start_create(url, "Kain", {})       # a second click must try again
    assert nc._thread is not first
    nc._thread.join(timeout=15)
    app.processEvents()
    assert drops == [True, True]
