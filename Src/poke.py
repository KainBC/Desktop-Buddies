import math


class Hop:
    """A short vertical hop: one arc up from the ground and back down.

    `offset()` is a fraction of screen height (like `Sprite.x`/`y`), applied
    at render time so a hopping sprite keeps walking underneath it."""

    def __init__(self, height: float = 0.04, duration: float = 0.45):
        self.height = height
        self.duration = duration
        self._elapsed = 0.0

    def advance(self, dt: float) -> None:
        self._elapsed += dt

    def offset(self) -> float:
        if self.done:
            return 0.0
        return self.height * math.sin(math.pi * self._elapsed / self.duration)

    @property
    def done(self) -> bool:
        return self._elapsed >= self.duration

    def reset(self) -> None:
        self._elapsed = 0.0
