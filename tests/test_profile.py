import json

from Src.appearance import Appearance, DEFAULT_SKIN
from Src.profile import load_profile, save_profile, DEFAULT_NAME


def test_round_trip(tmp_path):
    path = tmp_path / "profile.json"
    save_profile(path, "Kain", Appearance(body="slim", skin="#a4673f"))
    assert load_profile(path) == ("Kain", Appearance(body="slim",
                                                     skin="#a4673f"))


def test_missing_file_yields_defaults(tmp_path):
    assert load_profile(tmp_path / "nope.json") == (DEFAULT_NAME, Appearance())


def test_corrupt_json_yields_defaults(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text("{not json at all")
    assert load_profile(path) == (DEFAULT_NAME, Appearance())


def test_non_object_json_yields_defaults(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text("[1, 2, 3]")
    assert load_profile(path) == (DEFAULT_NAME, Appearance())


def test_unknown_appearance_field_is_ignored(tmp_path):
    """An appearance saved by a future build must still load here."""
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"name": "Sam",
                                "appearance": {"body": "tall",
                                               "hair": "spiky"}}))
    name, appearance = load_profile(path)
    assert name == "Sam"
    assert appearance == Appearance(body="tall", skin=DEFAULT_SKIN)


def test_non_string_name_falls_back(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"name": 42, "appearance": {}}))
    assert load_profile(path)[0] == DEFAULT_NAME


def test_save_creates_missing_directories(tmp_path):
    path = tmp_path / "nested" / "deeper" / "profile.json"
    save_profile(path, "Kain", Appearance())
    assert path.is_file()
