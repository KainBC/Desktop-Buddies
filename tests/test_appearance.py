from Src.appearance import (Appearance, DEFAULT_BODY, DEFAULT_SKIN,
                            SKIN_PALETTE)


def test_defaults_are_renderable():
    a = Appearance()
    assert a.body == DEFAULT_BODY
    assert a.skin == DEFAULT_SKIN


def test_round_trip():
    a = Appearance(body="tall", skin="#123456")
    assert Appearance.from_dict(a.to_dict()) == a


def test_unknown_keys_are_dropped():
    """A future client sends hair; this build must render a bald buddy,
    not crash."""
    a = Appearance.from_dict({"body": "slim", "skin": "#abcdef",
                              "hair": "spiky", "hair_color": "#000000"})
    assert a == Appearance(body="slim", skin="#abcdef")


def test_missing_keys_default():
    a = Appearance.from_dict({"body": "tall"})
    assert a == Appearance(body="tall", skin=DEFAULT_SKIN)


def test_malformed_input_yields_defaults():
    assert Appearance.from_dict(None) == Appearance()
    assert Appearance.from_dict("nonsense") == Appearance()
    assert Appearance.from_dict([]) == Appearance()


def test_non_string_values_are_ignored():
    assert Appearance.from_dict({"body": 7}) == Appearance()


def test_appearance_is_hashable():
    """Frozen, so it can key a cache."""
    assert {Appearance(): 1}[Appearance()] == 1


def test_palette_is_nonempty_hex():
    assert SKIN_PALETTE
    assert all(c.startswith("#") and len(c) == 7 for c in SKIN_PALETTE)
    assert DEFAULT_SKIN in SKIN_PALETTE
