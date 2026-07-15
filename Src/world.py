import random
from dataclasses import dataclass

IDLE = "idle"
WALK = "walk"

WALK_SPEED = 0.12   # fraction of screen width per second
LERP_RATE = 8.0     # remote interpolation responsiveness


@dataclass
class Sprite:
    id: str
    name: str
    character: str
    x: float = 0.5
    y: float = 0.9
    target_x: float = 0.5
    target_y: float = 0.9
    facing: int = 1
    anim: str = IDLE


class OwnController:
    """Drives one Sprite with a simple idle/walk wander loop (horizontal)."""

    def __init__(self, sprite: Sprite, rng: random.Random | None = None):
        self.sprite = sprite
        self.rng = rng or random.Random()
        self._idle_timer = self._idle_time()

    def _idle_time(self) -> float:
        return self.rng.uniform(2.0, 5.0)

    def update(self, dt: float) -> bool:
        s = self.sprite
        if s.anim == IDLE:
            self._idle_timer -= dt
            if self._idle_timer <= 0:
                s.target_x = self.rng.uniform(0.05, 0.95)
                s.anim = WALK
                s.facing = 1 if s.target_x >= s.x else -1
                return True
            return False

        # WALK
        step = WALK_SPEED * dt
        remaining = s.target_x - s.x
        if abs(remaining) <= step:
            s.x = s.target_x
            s.anim = IDLE
            self._idle_timer = self._idle_time()
        else:
            s.x += step if remaining > 0 else -step
            s.facing = 1 if remaining > 0 else -1
        return True


class World:
    """Local model: own sprite driven by AI, remotes driven by network."""

    def __init__(self, own: Sprite):
        self.own = own
        self.controller = OwnController(own)
        self.remotes: dict[str, Sprite] = {}

    def add_member(self, id: str, name: str, character: str) -> None:
        self.remotes[id] = Sprite(id=id, name=name, character=character)

    def remove_member(self, id: str) -> None:
        self.remotes.pop(id, None)

    def apply_state(self, id: str, x: float, y: float, facing: int, anim: str) -> None:
        s = self.remotes.get(id)
        if s is None:
            return
        s.target_x, s.target_y, s.facing, s.anim = x, y, facing, anim

    def tick(self, dt: float) -> bool:
        changed = self.controller.update(dt)
        alpha = min(1.0, dt * LERP_RATE)
        for s in self.remotes.values():
            s.x += (s.target_x - s.x) * alpha
            s.y += (s.target_y - s.y) * alpha
        return changed

    def all_sprites(self) -> list[Sprite]:
        return [self.own, *self.remotes.values()]
