"""Turn an Appearance into an ordered stack of drawable layers.

This module is the ONLY place that knows what a layer means. The compositor,
the preview, and SpriteWindow all consume an anonymous list of LayerSpec, so
adding hair or outfits later is a change here plus art — nothing downstream.

No Qt import: resolution is pure path logic and unit tests headless.
"""
import json
from dataclasses import dataclass
from pathlib import Path

MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True)
class LayerSpec:
    frames_dir: Path   # the character dir; callers append the animation name
    tint: str | None   # hex color, or None to draw the art as authored
    z: int             # draw order, ascending = further back


def load_manifest(sprites_dir) -> dict:
    return json.loads((Path(sprites_dir) / MANIFEST_NAME).read_text())


def slot_options(sprites_dir, slot: dict) -> list[str]:
    """Available choices for a slot: the subdirectories of its directory.

    Discovery rather than declaration is what makes importing new art a
    content change instead of a code change.
    """
    folder = Path(sprites_dir) / slot["dir"]
    if not folder.is_dir():
        return []
    return sorted(p.name for p in folder.iterdir() if p.is_dir())


def body_options(sprites_dir) -> list[str]:
    manifest = load_manifest(sprites_dir)
    for slot in manifest["slots"]:
        if slot["name"] == "body":
            return slot_options(sprites_dir, slot)
    return []


def resolve_layers(appearance, sprites_dir, manifest: dict | None = None
                   ) -> list[LayerSpec]:
    sprites_dir = Path(sprites_dir)
    manifest = manifest if manifest is not None else load_manifest(sprites_dir)
    specs: list[LayerSpec] = []
    for slot in manifest["slots"]:
        choice = getattr(appearance, slot["field"], None) or slot.get("default")
        if not choice:
            continue
        frames_dir = sprites_dir / slot["dir"] / choice
        if not frames_dir.is_dir():
            continue
        tint_field = slot.get("tint_field")
        tint = getattr(appearance, tint_field, None) if tint_field else None
        specs.append(LayerSpec(frames_dir=frames_dir, tint=tint, z=slot["z"]))
    return sorted(specs, key=lambda s: s.z)
