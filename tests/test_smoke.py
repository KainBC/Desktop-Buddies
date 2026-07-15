import importlib


def test_packages_import():
    for name in ("shared", "relay", "Src"):
        importlib.import_module(name)
