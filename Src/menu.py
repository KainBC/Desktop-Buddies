from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel)

from Src.appearance import Appearance
from Src.customizer import CustomizerPanel
from Src.updates import DOWNLOAD_PAGE, is_newer, parse_version
from Src.version import VERSION


def validate_name(name: str) -> bool:
    stripped = name.strip()
    return 0 < len(stripped) <= 20


def normalize_code(code: str) -> str:
    return code.strip().upper()


class MenuWindow(QWidget):
    create_requested = Signal(str, object)        # name, Appearance
    join_requested = Signal(str, str, object)     # code, name, Appearance

    def __init__(self, sprites_dir, name: str = "",
                 appearance: Appearance | None = None):
        super().__init__()
        self.setWindowTitle("Desktop Buddies")
        layout = QVBoxLayout(self)

        self._name = QLineEdit(placeholderText="Your name")
        self._name.setText(name)
        layout.addWidget(self._name)

        self.customizer = CustomizerPanel(sprites_dir, appearance)
        layout.addWidget(self.customizer)

        create_btn = QPushButton("Create room")
        create_btn.clicked.connect(self._on_create)
        layout.addWidget(create_btn)

        join_row = QHBoxLayout()
        self._code = QLineEdit(placeholderText="Room code")
        join_btn = QPushButton("Join")
        join_btn.clicked.connect(self._on_join)
        join_row.addWidget(self._code)
        join_row.addWidget(join_btn)
        layout.addLayout(join_row)

        self._status = QLabel("")
        layout.addWidget(self._status)

        self._version = QLabel(f"v{VERSION}")
        self._version.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._version)

        self._update = QLabel("")
        self._update.setTextFormat(Qt.RichText)
        self._update.setOpenExternalLinks(True)
        self._update.setStyleSheet("color: gray; font-size: 11px;")
        self._update.hide()
        layout.addWidget(self._update)

    def name(self) -> str:
        return self._name.text().strip()

    def appearance(self) -> Appearance:
        return self.customizer.appearance()

    def _on_create(self) -> None:
        if not validate_name(self._name.text()):
            self.show_error("Enter a name (1-20 chars).")
            return
        self.create_requested.emit(self.name(), self.appearance())

    def _on_join(self) -> None:
        if not validate_name(self._name.text()):
            self.show_error("Enter a name (1-20 chars).")
            return
        code = normalize_code(self._code.text())
        if not code:
            self.show_error("Enter a room code.")
            return
        self.join_requested.emit(code, self.name(), self.appearance())

    def show_code(self, code: str) -> None:
        self._status.setText(f"Room code: {code}  (share this)")

    def show_error(self, msg: str) -> None:
        self._status.setText(msg)

    def show_update(self, tag: str) -> None:
        """Show the update line if `tag` is a newer release than this build.

        The tag comes off the network, so only its parsed numbers are ever
        rendered -- never the raw string -- into this rich-text label.
        """
        if not is_newer(tag, VERSION):
            return
        shown = "v" + ".".join(str(n) for n in parse_version(tag))
        self._update.setText(
            f'Update available: {shown} — <a href="{DOWNLOAD_PAGE}">Download</a>')
        self._update.show()

    def update_notice(self) -> str:
        return "" if self._update.isHidden() else self._update.text()
