from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QWidget

from Src.chat import BubbleLifetime

MAX_WIDTH = 220
PAD_X = 10
PAD_Y = 6


class BubbleWindow(QWidget):
    def __init__(self, hold: float = 5.0, fade: float = 0.5):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_MacAlwaysShowToolWindow, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._font = QFont()
        self._text = ""
        self._text_rect = None
        self._life = BubbleLifetime(hold, fade)
        self.show()

    def set_text(self, text: str) -> None:
        self._text = text
        self._life.reset()
        self._relayout()
        self.setWindowOpacity(1.0)
        self.update()

    def _relayout(self) -> None:
        fm = QFontMetrics(self._font)
        rect = fm.boundingRect(0, 0, MAX_WIDTH, 10_000,
                               Qt.TextWordWrap, self._text)
        self._text_rect = rect
        self.resize(rect.width() + 2 * PAD_X, rect.height() + 2 * PAD_Y)

    def tick(self, dt: float) -> None:
        self._life.advance(dt)
        self.setWindowOpacity(self._life.opacity())
        self.update()

    @property
    def done(self) -> bool:
        return self._life.done

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(255, 255, 255, 235))
        p.setPen(QColor(0, 0, 0, 40))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)
        p.setPen(QColor(20, 20, 20))
        p.setFont(self._font)
        p.drawText(self.rect().adjusted(PAD_X, PAD_Y, -PAD_X, -PAD_Y),
                   Qt.TextWordWrap | Qt.AlignCenter, self._text)
