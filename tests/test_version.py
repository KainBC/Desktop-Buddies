import tomllib
from pathlib import Path

from Src.version import VERSION
from Src.updates import parse_version

ROOT = Path(__file__).resolve().parent.parent


def test_version_is_semver():
    assert parse_version(VERSION) is not None


def test_pyproject_version_matches():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert data["project"]["version"] == VERSION
