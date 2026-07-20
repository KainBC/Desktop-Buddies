from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtWidgets import QWidget, QLineEdit, QVBoxLayout

from Src.chat import sanitize_chat


class ChatInputWindow(QWidget):
    submitted = Signal(str)

    def __init__(self, max_len: int = 140):
        super().__init__(None)
        self._max_len = max_len
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setMaxLength(max_len)
        self.edit.setPlaceholderText("Say something…")
        self.edit.returnPressed.connect(self._submit)
        self.edit.installEventFilter(self)
        layout.addWidget(self.edit)
        self.resize(200, 32)

    def open_at(self, x: int, y: int) -> None:
        self.move(x, y)
        self.edit.clear()
        self.show()
        self.raise_()
        self.activateWindow()
        self.edit.setFocus()

    def _submit(self) -> None:
        text = sanitize_chat(self.edit.text(), self._max_len)
        self.hide()
        if text:
            self.submitted.emit(text)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.edit:
            if (event.type() == QEvent.KeyPress
                    and event.key() == Qt.Key_Escape):
                self.hide()
                return True
            if event.type() == QEvent.FocusOut:
                self.hide()
        return super().eventFilter(obj, event)
