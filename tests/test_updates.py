import json

import pytest

from Src.updates import is_newer, latest_tag_from_json, parse_version


@pytest.mark.parametrize("tag, expected", [
    ("v1.2.3", (1, 2, 3)),
    ("1.2.3", (1, 2, 3)),
    (" v10.0.12 ", (10, 0, 12)),
    ("v1.2", None),
    ("v1.2.3-rc1", None),
    ("latest", None),
    ("", None),
    (None, None),
    (123, None),
])
def test_parse_version(tag, expected):
    assert parse_version(tag) == expected


def test_is_newer_compares_numerically():
    assert is_newer("v1.10.0", "1.9.0")
    assert is_newer("v2.0.0", "1.99.99")
    assert not is_newer("v1.0.0", "1.0.0")
    assert not is_newer("v0.9.0", "1.0.0")


def test_is_newer_is_false_for_garbage():
    assert not is_newer("nightly", "1.0.0")
    assert not is_newer("v2.0.0", "dev")


def test_latest_tag_from_json():
    assert latest_tag_from_json(json.dumps({"tag_name": "v1.1.0"}).encode()) \
        == "v1.1.0"
    assert latest_tag_from_json(b"not json") is None
    assert latest_tag_from_json(b"[]") is None
    assert latest_tag_from_json(json.dumps({"message": "Not Found"}).encode()) \
        is None
    assert latest_tag_from_json(json.dumps({"tag_name": 7}).encode()) is None
