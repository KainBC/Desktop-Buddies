from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel)

from Src.appearance import Appearance


def validate_name(name: str) -> bool:
    stripped = name.strip()
    return 0 < len(stripped) <= 20


def normalize_code(code: str) -> str:
    return code.strip().upper()


class MenuWindow(QWidget):
    create_requested = Signal(str, object)        # name, Appearance
    join_requested = Signal(str, str, object)     # code, name, Appearance

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Buddies")
        self._appearance_value = Appearance()
        layout = QVBoxLayout(self)

        self._name = QLineEdit(placeholderText="Your name")
        layout.addWidget(self._name)

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

    def _appearance(self) -> Appearance:
        return self._appearance_value

    def _on_create(self) -> None:
        if not validate_name(self._name.text()):
            self.show_error("Enter a name (1-20 chars).")
            return
        self.create_requested.emit(self._name.text().strip(), self._appearance())

    def _on_join(self) -> None:
        if not validate_name(self._name.text()):
            self.show_error("Enter a name (1-20 chars).")
            return
        code = normalize_code(self._code.text())
        if not code:
            self.show_error("Enter a room code.")
            return
        self.join_requested.emit(code, self._name.text().strip(), self._appearance())

    def show_code(self, code: str) -> None:
        self._status.setText(f"Room code: {code}  (share this)")

    def show_error(self, msg: str) -> None:
        self._status.setText(msg)
