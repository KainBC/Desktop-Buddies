import asyncio
import pytest
import websockets
from websockets.exceptions import ConnectionClosedError

from relay.room import Registry, ROOM_FULL, ROOM_NOT_FOUND
from relay.server import MAX_FRAME, make_handler, start_server
from shared import messages as m


async def _recv(ws):
    return m.decode(await asyncio.wait_for(ws.recv(), timeout=2))


@pytest.fixture
async def server():
    srv = await start_server("localhost", 0)
    port = srv.sockets[0].getsockname()[1]
    yield port
    srv.close()
    await srv.wait_closed()


@pytest.fixture
async def tiny_server():
    srv = await start_server("localhost", 0, Registry(max_members=1))
    yield srv.sockets[0].getsockname()[1]
    srv.close()
    await srv.wait_closed()


async def test_create_join_and_relay(server):
    port = server
    url = f"ws://localhost:{port}"
    async with websockets.connect(url) as host, websockets.connect(url) as guest:
        await host.send(m.encode(m.CREATE_ROOM, name="Kain", appearance={"body": "round", "skin": "#e8b48c"}))
        created = await _recv(host)
        assert created["type"] == m.ROOM_CREATED
        code = created["code"]

        await guest.send(m.encode(m.JOIN_ROOM, code=code, name="Sam", appearance={"body": "tall", "skin": "#a4673f"}))
        joined = await _recv(guest)
        assert joined["type"] == m.ROOM_JOINED
        assert await _recv(host) == {"type": m.MEMBER_JOINED, "id": joined["your_id"],
                                     "name": "Sam", "appearance": {"body": "tall",
                                                                   "skin": "#a4673f"}}

        raw = m.encode(m.STATE, id=created["your_id"], x=0.4, y=0.9,
                       facing=1, anim="walk")
        await host.send(raw)
        assert await _recv(guest) == m.decode(raw)


async def test_unknown_code_errors(server):
    url = f"ws://localhost:{server}"
    async with websockets.connect(url) as guest:
        await guest.send(m.encode(m.JOIN_ROOM, code="NOPE-00", name="x", appearance={"body": "round", "skin": "#e8b48c"}))
        reply = await _recv(guest)
        assert reply == {"type": m.ERROR, "reason": ROOM_NOT_FOUND}


async def test_disconnect_sends_member_left(server):
    url = f"ws://localhost:{server}"
    async with websockets.connect(url) as host:
        await host.send(m.encode(m.CREATE_ROOM, name="Kain", appearance={"body": "round", "skin": "#e8b48c"}))
        code = (await _recv(host))["code"]
        guest = await websockets.connect(url)
        await guest.send(m.encode(m.JOIN_ROOM, code=code, name="Sam", appearance={"body": "tall", "skin": "#a4673f"}))
        left_id = (await _recv(guest))["your_id"]
        await _recv(host)  # member_joined
        await guest.close()
        assert await _recv(host) == {"type": m.MEMBER_LEFT, "id": left_id}


async def test_relay_forwards_chat(server):
    url = f"ws://localhost:{server}"
    async with websockets.connect(url) as host, websockets.connect(url) as guest:
        await host.send(m.encode(m.CREATE_ROOM, name="Kain", appearance={"body": "round", "skin": "#e8b48c"}))
        created = await _recv(host)
        host_id = created["your_id"]
        await guest.send(m.encode(m.JOIN_ROOM, code=created["code"],
                                  name="Sam", appearance={"body": "tall", "skin": "#a4673f"}))
        await _recv(guest)   # room_joined
        await _recv(host)    # member_joined

        raw = m.encode(m.CHAT, id=host_id, text="hi there")
        await host.send(raw)
        assert await _recv(guest) == m.decode(raw)


async def test_relay_forwards_poke(server):
    url = f"ws://localhost:{server}"
    async with websockets.connect(url) as host, websockets.connect(url) as guest:
        await host.send(m.encode(m.CREATE_ROOM, name="Kain", appearance={"body": "round", "skin": "#e8b48c"}))
        created = await _recv(host)
        await guest.send(m.encode(m.JOIN_ROOM, code=created["code"],
                                  name="Sam", appearance={"body": "tall", "skin": "#a4673f"}))
        guest_id = (await _recv(guest))["your_id"]
        await _recv(host)    # member_joined

        raw = m.encode(m.POKE, id=created["your_id"], target_id=guest_id)
        await host.send(raw)
        assert await _recv(guest) == m.decode(raw)


async def test_abrupt_disconnect_cleans_up_without_raising():
    """A client that vanishes without a close handshake is normal, not a crash.

    The handler must swallow ConnectionClosed so websockets does not log it as
    'connection handler failed', while still leaving the room."""
    registry = Registry()
    handler = make_handler(registry)

    class VanishingSocket:
        """Delivers one create_room, then dies mid-stream."""

        def __init__(self):
            self.sent = []

        async def send(self, raw):
            self.sent.append(raw)

        async def __aiter__(self):
            yield m.encode(m.CREATE_ROOM, name="Kain", appearance={"body": "round", "skin": "#e8b48c"})
            raise ConnectionClosedError(None, None)

    ws = VanishingSocket()
    await handler(ws)                       # must not raise
    assert registry.rooms == {}             # room torn down on the way out


async def test_full_room_gets_room_is_full(tiny_server):
    url = f"ws://localhost:{tiny_server}"
    async with websockets.connect(url) as host, websockets.connect(url) as guest:
        await host.send(m.encode(m.CREATE_ROOM, name="A", appearance={}))
        code = (await _recv(host))["code"]
        await guest.send(m.encode(m.JOIN_ROOM, code=code, name="B",
                                  appearance={}))
        assert await _recv(guest) == {"type": m.ERROR, "reason": ROOM_FULL}


async def test_oversized_frame_closes_connection(server):
    async with websockets.connect(f"ws://localhost:{server}",
                                  max_size=None) as ws:
        await ws.send("x" * (MAX_FRAME + 1))
        with pytest.raises(ConnectionClosedError):
            await asyncio.wait_for(ws.recv(), timeout=2)
        assert ws.close_code == 1009       # "message too big"


async def test_logs_codes_but_never_names_or_chat(server, caplog):
    caplog.set_level("INFO", logger="relay")
    url = f"ws://localhost:{server}"
    async with websockets.connect(url) as host, websockets.connect(url) as guest:
        await host.send(m.encode(m.CREATE_ROOM, name="SecretName",
                                 appearance={}))
        created = await _recv(host)
        await guest.send(m.encode(m.JOIN_ROOM, code=created["code"],
                                  name="OtherSecret", appearance={}))
        await _recv(guest)
        await _recv(host)
        await host.send(m.encode(m.CHAT, id=created["your_id"],
                                 text="private words"))
        await _recv(guest)

    await asyncio.sleep(0.1)     # let the handlers' finally-blocks log
    assert created["code"] in caplog.text
    for secret in ("SecretName", "OtherSecret", "private words"):
        assert secret not in caplog.text
