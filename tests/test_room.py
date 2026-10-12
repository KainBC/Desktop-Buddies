import pytest
from relay.room import (Registry, generate_code, JoinError, ROOM_FULL,
                        ROOM_NOT_FOUND, MAX_NAME)
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
    code, mid = await reg.create_room("Kain", {"body": "round",
                                               "skin": "#e8b48c"}, a.send)
    assert a.sent == [{"type": m.ROOM_CREATED, "code": code, "your_id": mid}]


async def test_join_notifies_both_sides():
    reg = Registry()
    a = FakeConn()
    code, a_id = await reg.create_room("Kain", {"body": "round",
                                               "skin": "#e8b48c"}, a.send)
    b = FakeConn()
    b_id = await reg.join_room(code, "Sam", {"body": "tall",
                                            "skin": "#a4673f"}, b.send)

    # joiner learns the existing member
    assert b.sent[0] == {"type": m.ROOM_JOINED, "your_id": b_id,
                         "members": [{"id": a_id, "name": "Kain",
                                      "appearance": {"body": "round",
                                                     "skin": "#e8b48c"}}]}
    # existing member is told about the joiner
    assert a.sent[-1] == {"type": m.MEMBER_JOINED, "id": b_id,
                          "name": "Sam", "appearance": {"body": "tall",
                                                        "skin": "#a4673f"}}


async def test_join_unknown_code_raises_not_found():
    reg = Registry()
    with pytest.raises(JoinError) as err:
        await reg.join_room("NOPE-00", "Sam", {"body": "tall",
                                              "skin": "#a4673f"},
                            FakeConn().send)
    assert err.value.reason == ROOM_NOT_FOUND


async def test_relay_fans_out_to_others_only():
    reg = Registry()
    a, b = FakeConn(), FakeConn()
    code, a_id = await reg.create_room("Kain", {"body": "round",
                                               "skin": "#e8b48c"}, a.send)
    await reg.join_room(code, "Sam", {"body": "tall",
                                     "skin": "#a4673f"}, b.send)
    a.sent.clear(); b.sent.clear()

    raw = m.encode(m.STATE, id=a_id, x=0.3, y=0.9, facing=1, anim="walk")
    await reg.relay(code, a_id, raw)
    assert a.sent == []                 # sender does not get its own message
    assert b.sent == [m.decode(raw)]    # others do


async def test_leave_notifies_and_cleans_up():
    reg = Registry()
    a, b = FakeConn(), FakeConn()
    code, a_id = await reg.create_room("Kain", {"body": "round",
                                               "skin": "#e8b48c"}, a.send)
    b_id = await reg.join_room(code, "Sam", {"body": "tall",
                                            "skin": "#a4673f"}, b.send)
    a.sent.clear()

    await reg.leave(code, b_id)
    assert a.sent[-1] == {"type": m.MEMBER_LEFT, "id": b_id}

    await reg.leave(code, a_id)         # room now empty
    assert code not in reg.rooms


async def test_join_full_room_raises_full_and_sends_nothing():
    reg = Registry(max_members=2)
    a, b, c = FakeConn(), FakeConn(), FakeConn()
    code, _ = await reg.create_room("A", {}, a.send)
    await reg.join_room(code, "B", {}, b.send)
    sent_before = (len(a.sent), len(b.sent))

    with pytest.raises(JoinError) as err:
        await reg.join_room(code, "C", {}, c.send)

    assert err.value.reason == ROOM_FULL
    assert c.sent == []
    assert (len(a.sent), len(b.sent)) == sent_before
    assert len(reg.rooms[code]["members"]) == 2


async def test_default_room_cap_is_sixteen():
    reg = Registry()
    code, _ = await reg.create_room("host", {}, FakeConn().send)
    for i in range(15):
        await reg.join_room(code, f"p{i}", {}, FakeConn().send)
    with pytest.raises(JoinError):
        await reg.join_room(code, "one-too-many", {}, FakeConn().send)


async def test_names_are_cleaned_before_storing_and_forwarding():
    reg = Registry()
    a, b = FakeConn(), FakeConn()
    code, a_id = await reg.create_room("  " + "x" * 500, {}, a.send)
    b_id = await reg.join_room(code, 12345, {}, b.send)

    assert reg.rooms[code]["members"][a_id]["name"] == "x" * MAX_NAME
    assert a.sent[-1]["name"] == ""          # MEMBER_JOINED for the non-str name
    assert b.sent[0]["members"][0]["name"] == "x" * MAX_NAME
    assert reg.rooms[code]["members"][b_id]["name"] == ""


async def test_last_leave_logs_room_emptied(caplog):
    caplog.set_level("INFO", logger="relay")
    reg = Registry()
    code, mid = await reg.create_room("A", {}, FakeConn().send)
    await reg.leave(code, mid)
    assert f"room {code} emptied" in caplog.text
