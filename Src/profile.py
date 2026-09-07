"""Remember the player's name and buddy between launches.

A broken profile must never stop the app from starting, so every failure
path falls back to defaults rather than raising. The path is passed in so
tests never touch the real config directory.
"""
import json
from pathlib import Path

from Src.appearance import Appearance

DEFAULT_NAME = ""


def load_profile(path) -> tuple[str, Appearance]:
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return DEFAULT_NAME, Appearance()
    if not isinstance(data, dict):
        return DEFAULT_NAME, Appearance()
    name = data.get("name")
    if not isinstance(name, str):
        name = DEFAULT_NAME
    return name, Appearance.from_dict(data.get("appearance"))


def save_profile(path, name: str, appearance: Appearance) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"name": name,
                             "appearance": appearance.to_dict()}, indent=2))
