from Src.menu import validate_name, normalize_code, CHARACTERS


def test_validate_name():
    assert validate_name("Kain")
    assert not validate_name("   ")
    assert not validate_name("")
    assert not validate_name("x" * 21)


def test_normalize_code():
    assert normalize_code("  plum-42 ") == "PLUM-42"


def test_characters_nonempty():
    assert CHARACTERS and all(isinstance(c, str) for c in CHARACTERS)
