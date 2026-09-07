import json
from pathlib import Path

from Src.appearance import Appearance
from Src.layers import (LayerSpec, load_manifest, resolve_layers,
                        slot_options, body_options)

REAL_SPRITES = Path(__file__).resolve().parent.parent / "Sprites"


def _fake_tree(tmp_path: Path) -> Path:
    """A miniature Sprites/ dir: two body types, one face, one hair style."""
    manifest = {
        "fps": 6,
        "scale": 1,
        "slots": [
            {"name": "body", "z": 0, "dir": "Bodies",
             "field": "body", "tint_field": "skin", "default": "round"},
            {"name": "shoes", "z": 10, "dir": "Shoes",
             "field": "shoes", "tint_field": "shoe_color"},
            {"name": "face", "z": 30, "dir": "Faces",
             "field": "face", "tint_field": None, "default": "default"},
            {"name": "hair", "z": 40, "dir": "Hair",
             "field": "hair", "tint_field": "hair_color"},
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    for rel in ("Bodies/round", "Bodies/tall", "Faces/default", "Hair/spiky"):
        (tmp_path / rel / "idle").mkdir(parents=True)
    (tmp_path / "Shoes").mkdir()
    return tmp_path


def test_resolves_body_and_face_in_draw_order(tmp_path):
    root = _fake_tree(tmp_path)
    layers = resolve_layers(Appearance(body="tall", skin="#ff0000"), root)
    assert [l.z for l in layers] == [0, 30]
    assert layers[0].frames_dir == root / "Bodies" / "tall"
    assert layers[1].frames_dir == root / "Faces" / "default"


def test_only_tintable_slots_get_a_tint(tmp_path):
    root = _fake_tree(tmp_path)
    layers = resolve_layers(Appearance(skin="#ff0000"), root)
    assert layers[0].tint == "#ff0000"    # body tinted by skin
    assert layers[1].tint is None         # face is never tinted


def test_slot_with_no_art_contributes_nothing(tmp_path):
    """Shoes has an empty directory and the appearance has no shoes field,
    so it must not produce a layer."""
    root = _fake_tree(tmp_path)
    layers = resolve_layers(Appearance(), root)
    assert all("Shoes" not in str(l.frames_dir) for l in layers)


def test_future_slot_appears_once_the_appearance_carries_it(tmp_path):
    """The seam this phase exists to install: a hair field starts drawing
    hair with no change to resolve_layers itself."""
    root = _fake_tree(tmp_path)

    class Future(Appearance):
        pass

    future = Future()
    object.__setattr__(future, "hair", "spiky")
    object.__setattr__(future, "hair_color", "#333333")
    layers = resolve_layers(future, root)
    assert layers[-1].z == 40
    assert layers[-1].frames_dir == root / "Hair" / "spiky"
    assert layers[-1].tint == "#333333"


def test_missing_chosen_directory_is_skipped(tmp_path):
    root = _fake_tree(tmp_path)
    layers = resolve_layers(Appearance(body="doesnotexist"), root)
    assert all("Bodies" not in str(l.frames_dir) for l in layers)


def test_slot_options_lists_subdirectories(tmp_path):
    root = _fake_tree(tmp_path)
    manifest = load_manifest(root)
    body_slot = manifest["slots"][0]
    assert slot_options(root, body_slot) == ["round", "tall"]


def test_slot_options_empty_when_directory_absent(tmp_path):
    root = _fake_tree(tmp_path)
    missing = {"name": "outfit", "z": 20, "dir": "Outfits",
               "field": "outfit", "tint_field": None}
    assert slot_options(root, missing) == []


def test_real_sprite_tree_resolves(tmp_path):
    """Guards against the shipped manifest and generated art drifting apart."""
    layers = resolve_layers(Appearance(), REAL_SPRITES)
    assert [l.z for l in layers] == [0, 30]
    assert layers[0].tint == Appearance().skin


def test_real_body_options():
    assert body_options(REAL_SPRITES) == ["round", "slim", "tall"]
