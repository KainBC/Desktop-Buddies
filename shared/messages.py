import json

CREATE_ROOM = "create_room"
ROOM_CREATED = "room_created"
JOIN_ROOM = "join_room"
ROOM_JOINED = "room_joined"
ERROR = "error"
MEMBER_JOINED = "member_joined"
MEMBER_LEFT = "member_left"
STATE = "state"
CHAT = "chat"


def encode(msg_type: str, **fields) -> str:
    return json.dumps({"type": msg_type, **fields})


def decode(raw: str | bytes) -> dict | None:
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or "type" not in data:
        return None
    return data
