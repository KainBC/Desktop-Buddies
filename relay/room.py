import logging
import random

from shared import messages as m

log = logging.getLogger("relay.room")

MAX_MEMBERS = 16
MAX_NAME = 20            # matches the client's validate_name limit
ROOM_NOT_FOUND = "Room not found"
ROOM_FULL = "Room is full"

WORDS = ["PLUM", "MOSS", "FERN", "SAGE", "PEAR", "LARK", "WREN", "REED",
         "DUSK", "MINT", "CLAY", "ONYX", "JADE", "CORA", "IRIS", "FLAX"]


def generate_code() -> str:
    return f"{random.choice(WORDS)}-{random.randint(10, 99)}"


class JoinError(Exception):
    """A join the relay refuses. `reason` is shown to the joining user."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def clean_name(name) -> str:
    """Peers can bypass the client's validation, so the relay enforces the
    same limit on everything it stores and forwards: non-strings become
    "", whitespace is stripped, and length is truncated (not rejected)."""
    if not isinstance(name, str):
        return ""
    return name.strip()[:MAX_NAME]


class Registry:
    def __init__(self, max_members: int = MAX_MEMBERS):
        self.rooms: dict[str, dict] = {}   # code -> {"code", "members": {id -> member}}
        self._next_id = 0
        self.max_members = max_members

    def _new_member_id(self) -> str:
        self._next_id += 1
        return str(self._next_id)

    def _unique_code(self) -> str:
        code = generate_code()
        while code in self.rooms:
            code = generate_code()
        return code

    @staticmethod
    def _public(room: dict) -> list[dict]:
        return [{"id": mem["id"], "name": mem["name"],
                 "appearance": mem["appearance"]}
                for mem in room["members"].values()]

    async def create_room(self, name: str, appearance: dict, send
                          ) -> tuple[str, str]:
        name = clean_name(name)
        code = self._unique_code()
        mid = self._new_member_id()
        room = {"code": code, "members": {}}
        room["members"][mid] = {"id": mid, "name": name,
                                "appearance": appearance, "send": send}
        self.rooms[code] = room
        await send(m.encode(m.ROOM_CREATED, code=code, your_id=mid))
        return code, mid

    async def join_room(self, code: str, name: str, appearance: dict, send
                        ) -> str:
        room = self.rooms.get(code)
        if room is None:
            raise JoinError(ROOM_NOT_FOUND)
        if len(room["members"]) >= self.max_members:
            raise JoinError(ROOM_FULL)
        name = clean_name(name)
        mid = self._new_member_id()
        await send(m.encode(m.ROOM_JOINED, your_id=mid, members=self._public(room)))
        room["members"][mid] = {"id": mid, "name": name,
                                "appearance": appearance, "send": send}
        for mem in room["members"].values():
            if mem["id"] != mid:
                await mem["send"](m.encode(m.MEMBER_JOINED, id=mid,
                                           name=name, appearance=appearance))
        return mid

    async def relay(self, code: str, sender_id: str, raw: str) -> None:
        room = self.rooms.get(code)
        if room is None:
            return
        for mem in room["members"].values():
            if mem["id"] != sender_id:
                await mem["send"](raw)

    async def leave(self, code: str, member_id: str) -> None:
        room = self.rooms.get(code)
        if room is None:
            return
        room["members"].pop(member_id, None)
        if not room["members"]:
            del self.rooms[code]
            log.info("room %s emptied", code)
            return
        for mem in room["members"].values():
            await mem["send"](m.encode(m.MEMBER_LEFT, id=member_id))
