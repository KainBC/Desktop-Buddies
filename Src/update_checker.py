"""Ask GitHub, once, what the newest release is.

Asynchronous on Qt's event loop (no thread), and silent on every failure:
the only visible outcome is `latest_found` firing with a tag. `done` always
fires exactly once, which is what tests wait on.
"""
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import (QNetworkAccessManager, QNetworkReply,
                               QNetworkRequest)

from Src.updates import RELEASES_API, latest_tag_from_json
from Src.version import VERSION


class UpdateChecker(QObject):
    latest_found = Signal(str)
    done = Signal()

    def __init__(self, url: str = RELEASES_API, timeout_ms: int = 5000):
        super().__init__()
        self._url = url
        self._timeout_ms = timeout_ms
        self._manager = QNetworkAccessManager(self)
        self._reply: QNetworkReply | None = None

    def start(self) -> None:
        request = QNetworkRequest(QUrl(self._url))
        request.setTransferTimeout(self._timeout_ms)
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"User-Agent",
                             f"desktop-buddies/{VERSION}".encode())
        self._reply = self._manager.get(request)
        self._reply.finished.connect(self._on_finished)

    def _on_finished(self) -> None:
        reply, self._reply = self._reply, None
        try:
            if reply.error() == QNetworkReply.NetworkError.NoError:
                tag = latest_tag_from_json(bytes(reply.readAll()))
                if tag:
                    self.latest_found.emit(tag)
        finally:
            reply.deleteLater()
            self.done.emit()
