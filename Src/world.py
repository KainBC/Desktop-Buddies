import random
from dataclasses import dataclass, field

from Src.appearance import Appearance
from Src.poke import Hop

IDLE = "idle"
WALK = "walk"

WALK_SPEED = 0.12   # fraction of screen width per second
LERP_RATE = 8.0     # remote interpolation responsiveness


@dataclass
class Sprite:
    id: str
    name: str
    appearance: "Appearance" = field(default_factory=Appearance)
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
        self.hops: dict[str, Hop] = {}

    def add_member(self, id: str, name: str, appearance: Appearance) -> None:
        self.remotes[id] = Sprite(id=id, name=name, appearance=appearance)

    def remove_member(self, id: str) -> None:
        self.remotes.pop(id, None)
        self.hops.pop(id, None)

    def _sprite(self, id: str) -> Sprite | None:
        return self.own if id == self.own.id else self.remotes.get(id)

    def poke(self, target_id: str) -> None:
        """Start (or restart) a hop on a known sprite; ignore unknown ids."""
        if self._sprite(target_id) is None:
            return
        hop = self.hops.get(target_id)
        if hop is None:
            self.hops[target_id] = Hop()
        else:
            hop.reset()

    def hop_offset(self, id: str) -> float:
        hop = self.hops.get(id)
        return hop.offset() if hop is not None else 0.0

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
        for hid, hop in list(self.hops.items()):
            hop.advance(dt)
            if hop.done:
                del self.hops[hid]
        return changed

    def all_sprites(self) -> list[Sprite]:
        return [self.own, *self.remotes.values()]
