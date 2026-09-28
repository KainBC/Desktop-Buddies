import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from Src.update_checker import UpdateChecker  # noqa: E402


def _app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def github():
    """A local stand-in for the GitHub API. Set `.status`/`.body`."""
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(server.status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(server.body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.status, server.body = 200, b"{}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()


def _run(url):
    _app()
    found = []
    checker = UpdateChecker(url, timeout_ms=3000)
    checker.latest_found.connect(found.append)
    loop = QEventLoop()
    checker.done.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)
    checker.start()
    loop.exec()
    return found


def _url(server):
    return f"http://127.0.0.1:{server.server_address[1]}/latest"


def test_reports_latest_tag(github):
    github.body = json.dumps({"tag_name": "v1.4.0"}).encode()
    assert _run(_url(github)) == ["v1.4.0"]


@pytest.mark.parametrize("status", [404, 403, 500])
def test_http_errors_are_silent(github, status):
    github.status = status
    github.body = json.dumps({"message": "nope"}).encode()
    assert _run(_url(github)) == []


def test_bad_json_is_silent(github):
    github.body = b"<html>"
    assert _run(_url(github)) == []


def test_unreachable_host_is_silent():
    assert _run("http://127.0.0.1:9/latest") == []
