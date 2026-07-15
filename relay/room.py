import random

from shared import messages as m

WORDS = ["PLUM", "MOSS", "FERN", "SAGE", "PEAR", "LARK", "WREN", "REED",
         "DUSK", "MINT", "CLAY", "ONYX", "JADE", "CORA", "IRIS", "FLAX"]


def generate_code() -> str:
    return f"{random.choice(WORDS)}-{random.randint(10, 99)}"


class Registry:
    def __init__(self):
        self.rooms: dict[str, dict] = {}   # code -> {"code", "members": {id -> member}}
        self._next_id = 0

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
        return [{"id": mem["id"], "name": mem["name"], "character": mem["character"]}
                for mem in room["members"].values()]

    async def create_room(self, name: str, character: str, send) -> tuple[str, str]:
        code = self._unique_code()
        mid = self._new_member_id()
        room = {"code": code, "members": {}}
        room["members"][mid] = {"id": mid, "name": name,
                                "character": character, "send": send}
        self.rooms[code] = room
        await send(m.encode(m.ROOM_CREATED, code=code, your_id=mid))
        return code, mid

    async def join_room(self, code: str, name: str, character: str, send) -> str | None:
        room = self.rooms.get(code)
        if room is None:
            return None
        mid = self._new_member_id()
        await send(m.encode(m.ROOM_JOINED, your_id=mid, members=self._public(room)))
        room["members"][mid] = {"id": mid, "name": name,
                                "character": character, "send": send}
        for mem in room["members"].values():
            if mem["id"] != mid:
                await mem["send"](m.encode(m.MEMBER_JOINED, id=mid,
                                           name=name, character=character))
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
            return
        for mem in room["members"].values():
            await mem["send"](m.encode(m.MEMBER_LEFT, id=member_id))
