from Src.menu import validate_name, normalize_code


def test_validate_name():
    assert validate_name("Kain")
    assert not validate_name("   ")
    assert not validate_name("")
    assert not validate_name("x" * 21)


def test_normalize_code():
    assert normalize_code("  plum-42 ") == "PLUM-42"
