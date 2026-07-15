import pytest
from relay.room import Registry, generate_code
from shared import messages as m


class FakeConn:
    def __init__(self):
        self.sent = []

    async def send(self, raw):
        self.sent.append(m.decode(raw))


def test_generate_code_shape():
    code = generate_code()
    word, _, num = code.partition("-")
    assert word.isalpha() and num.isdigit()


async def test_create_room_sends_room_created():
    reg = Registry()
    a = FakeConn()
    code, mid = await reg.create_room("Kain", "cat", a.send)
    assert a.sent == [{"type": m.ROOM_CREATED, "code": code, "your_id": mid}]


async def test_join_notifies_both_sides():
    reg = Registry()
    a = FakeConn()
    code, a_id = await reg.create_room("Kain", "cat", a.send)
    b = FakeConn()
    b_id = await reg.join_room(code, "Sam", "dog", b.send)

    # joiner learns the existing member
    assert b.sent[0] == {"type": m.ROOM_JOINED, "your_id": b_id,
                         "members": [{"id": a_id, "name": "Kain", "character": "cat"}]}
    # existing member is told about the joiner
    assert a.sent[-1] == {"type": m.MEMBER_JOINED, "id": b_id,
                          "name": "Sam", "character": "dog"}


async def test_join_unknown_code_returns_none():
    reg = Registry()
    assert await reg.join_room("NOPE-00", "Sam", "dog", FakeConn().send) is None


async def test_relay_fans_out_to_others_only():
    reg = Registry()
    a, b = FakeConn(), FakeConn()
    code, a_id = await reg.create_room("Kain", "cat", a.send)
    await reg.join_room(code, "Sam", "dog", b.send)
    a.sent.clear(); b.sent.clear()

    raw = m.encode(m.STATE, id=a_id, x=0.3, y=0.9, facing=1, anim="walk")
    await reg.relay(code, a_id, raw)
    assert a.sent == []                 # sender does not get its own message
    assert b.sent == [m.decode(raw)]    # others do


async def test_leave_notifies_and_cleans_up():
    reg = Registry()
    a, b = FakeConn(), FakeConn()
    code, a_id = await reg.create_room("Kain", "cat", a.send)
    b_id = await reg.join_room(code, "Sam", "dog", b.send)
    a.sent.clear()

    await reg.leave(code, b_id)
    assert a.sent[-1] == {"type": m.MEMBER_LEFT, "id": b_id}

    await reg.leave(code, a_id)         # room now empty
    assert code not in reg.rooms
