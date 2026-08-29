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


class PokeCooldown:
    """Per-target send throttle.

    `now` is supplied by the caller rather than read from a clock inside, so
    tests can drive time without sleeping. A denied attempt does not extend
    the window — otherwise held-down spam would lock a target out forever."""

    def __init__(self, seconds: float = 1.0):
        self.seconds = seconds
        self._last: dict[str, float] = {}

    def try_send(self, target_id: str, now: float) -> bool:
        last = self._last.get(target_id)
        if last is not None and now - last < self.seconds:
            return False
        self._last[target_id] = now
        return True
