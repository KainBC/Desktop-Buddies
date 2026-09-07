from dataclasses import dataclass, field

from Src.appearance import Appearance


@dataclass
class PlayerIdentity:
    name: str
    appearance: Appearance = field(default_factory=Appearance)
