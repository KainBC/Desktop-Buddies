"""The player's buddy appearance. Pure data — no Qt, no filesystem.

Every future customization slot (hair, outfit, shoes) is added here as an
optional field with a default. `from_dict` deliberately ignores keys it does
not know and defaults keys that are missing, so a client running a newer or
older build degrades instead of crashing.
"""
from dataclasses import dataclass, fields

SKIN_PALETTE = [
    "#f6d5bd", "#e8b48c", "#d9a066", "#c98d63",
    "#a4673f", "#8d5524", "#7a4a2b", "#5a3520",
]

DEFAULT_BODY = "round"
DEFAULT_SKIN = "#e8b48c"


@dataclass(frozen=True)
class Appearance:
    body: str = DEFAULT_BODY
    skin: str = DEFAULT_SKIN

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data) -> "Appearance":
        if not isinstance(data, dict):
            return cls()
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items()
                  if k in known and isinstance(v, str)}
        return cls(**kwargs)
