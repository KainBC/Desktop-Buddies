import asyncio
import pytest
import websockets

from relay.room import Registry
from relay.server import make_handler
from shared import messages as m


async def _recv(ws):
    return m.decode(await asyncio.wait_for(ws.recv(), timeout=2))


@pytest.fixture
async def server():
    registry = Registry()
    async with websockets.serve(make_handler(registry), "localhost", 0) as srv:
        port = srv.sockets[0].getsockname()[1]
        yield port


async def test_create_join_and_relay(server):
    port = server
    url = f"ws://localhost:{port}"
    async with websockets.connect(url) as host, websockets.connect(url) as guest:
        await host.send(m.encode(m.CREATE_ROOM, name="Kain", character="cat"))
        created = await _recv(host)
        assert created["type"] == m.ROOM_CREATED
        code = created["code"]

        await guest.send(m.encode(m.JOIN_ROOM, code=code, name="Sam", character="dog"))
        joined = await _recv(guest)
        assert joined["type"] == m.ROOM_JOINED
        assert await _recv(host) == {"type": m.MEMBER_JOINED, "id": joined["your_id"],
                                     "name": "Sam", "character": "dog"}

        raw = m.encode(m.STATE, id=created["your_id"], x=0.4, y=0.9,
                       facing=1, anim="walk")
        await host.send(raw)
        assert await _recv(guest) == m.decode(raw)


async def test_unknown_code_errors(server):
    url = f"ws://localhost:{server}"
    async with websockets.connect(url) as guest:
        await guest.send(m.encode(m.JOIN_ROOM, code="NOPE-00", name="x", character="cat"))
        assert (await _recv(guest))["type"] == m.ERROR


async def test_disconnect_sends_member_left(server):
    url = f"ws://localhost:{server}"
    async with websockets.connect(url) as host:
        await host.send(m.encode(m.CREATE_ROOM, name="Kain", character="cat"))
        code = (await _recv(host))["code"]
        guest = await websockets.connect(url)
        await guest.send(m.encode(m.JOIN_ROOM, code=code, name="Sam", character="dog"))
        left_id = (await _recv(guest))["your_id"]
        await _recv(host)  # member_joined
        await guest.close()
        assert await _recv(host) == {"type": m.MEMBER_LEFT, "id": left_id}
