import re

_WS_RUN = re.compile(r"\s+")


def sanitize_chat(text: str, max_len: int = 140) -> str:
    """Collapse whitespace, trim, and cap length. Empty/whitespace -> ''."""
    collapsed = _WS_RUN.sub(" ", text).strip()
    return collapsed[:max_len]


class BubbleLifetime:
    """Tracks how long a bubble has been shown: full opacity during `hold`,
    a linear fade over `fade`, then done."""

    def __init__(self, hold: float = 5.0, fade: float = 0.5):
        self.hold = hold
        self.fade = fade
        self._elapsed = 0.0

    def advance(self, dt: float) -> None:
        self._elapsed += dt

    def opacity(self) -> float:
        if self._elapsed <= self.hold:
            return 1.0
        if self._elapsed >= self.hold + self.fade:
            return 0.0
        return 1.0 - (self._elapsed - self.hold) / self.fade

    @property
    def done(self) -> bool:
        return self._elapsed >= self.hold + self.fade

    def reset(self) -> None:
        self._elapsed = 0.0


def bubble_position(sprite_x: int, sprite_y: int, sprite_w: int,
                    bubble_w: int, bubble_h: int, screen_w: int,
                    gap: int = 8) -> tuple[int, int]:
    """Center the bubble over the sprite, `gap` px above its top edge,
    clamped so it stays on the primary screen."""
    x = sprite_x + (sprite_w - bubble_w) // 2
    y = sprite_y - bubble_h - gap
    x = max(0, min(x, screen_w - bubble_w))
    y = max(0, y)
    return x, y
