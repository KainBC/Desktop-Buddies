from shared import messages as m


def test_encode_roundtrips_through_decode():
    raw = m.encode(m.STATE, id="7", x=0.5, y=0.9, facing=-1, anim="walk")
    out = m.decode(raw)
    assert out == {"type": "state", "id": "7", "x": 0.5, "y": 0.9,
                   "facing": -1, "anim": "walk"}


def test_decode_rejects_malformed():
    assert m.decode("not json") is None
    assert m.decode("[1, 2, 3]") is None      # not an object
    assert m.decode('{"no": "type"}') is None  # missing type


def test_chat_roundtrips_through_decode():
    raw = m.encode(m.CHAT, id="7", text="hello world")
    assert m.decode(raw) == {"type": "chat", "id": "7", "text": "hello world"}


def test_constants_are_distinct_strings():
    values = [m.CREATE_ROOM, m.ROOM_CREATED, m.JOIN_ROOM, m.ROOM_JOINED,
              m.ERROR, m.MEMBER_JOINED, m.MEMBER_LEFT, m.STATE, m.CHAT]
    assert all(isinstance(v, str) for v in values)
    assert len(set(values)) == len(values)
