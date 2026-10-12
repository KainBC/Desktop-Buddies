"""Update-check logic. Pure: no Qt, no network.

The Qt side (Src/update_checker.py) fetches GitHub's latest release and hands
the tag to these functions; everything that can be wrong about a tag is
decided here, where it tests headless.
"""
import json
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


RELEASES_API = \
    "https://api.github.com/repos/KainBC/Desktop-Buddies/releases/latest"
# Where "Download" in the update notice goes. The site picks the right
# installer for the OS and repeats the unsigned-app instructions.
DOWNLOAD_PAGE = "https://desktop-buddies.vercel.app/download"


def is_newer(latest, current) -> bool:
    new, cur = parse_version(latest), parse_version(current)
    return new is not None and cur is not None and new > cur


def latest_tag_from_json(body: bytes) -> str | None:
    """`tag_name` from GitHub's latest-release JSON, or None if absent."""
    try:
        data = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    tag = data.get("tag_name")
    return tag if isinstance(tag, str) else None
