"""Update-check logic. Pure: no Qt, no network.

The Qt side (Src/update_checker.py) fetches GitHub's latest release and hands
the tag to these functions; everything that can be wrong about a tag is
decided here, where it tests headless.
"""
import re

_VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_version(tag) -> tuple[int, int, int] | None:
    """`"v1.2.3"` or `"1.2.3"` -> `(1, 2, 3)`; anything else -> None."""
    if not isinstance(tag, str):
        return None
    match = _VERSION.match(tag.strip())
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())
