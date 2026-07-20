import asyncio
import os

import websockets

from relay.room import Registry
from shared import messages as m


def make_handler(registry: Registry):
    async def handler(websocket):
        code: str | None = None
        member_id: str | None = None

        async def send(raw: str) -> None:
            await websocket.send(raw)

        try:
            async for raw in websocket:
                msg = m.decode(raw)
                if msg is None:
                    continue
                mtype = msg.get("type")

                if mtype == m.CREATE_ROOM and member_id is None:
                    code, member_id = await registry.create_room(
                        msg.get("name", ""), msg.get("character", ""), send)

                elif mtype == m.JOIN_ROOM and member_id is None:
                    mid = await registry.join_room(
                        msg.get("code", ""), msg.get("name", ""),
                        msg.get("character", ""), send)
                    if mid is None:
                        await send(m.encode(m.ERROR, reason="Room not found"))
                    else:
                        code, member_id = msg["code"], mid

                elif mtype in (m.STATE, m.CHAT) and member_id is not None:
                    await registry.relay(code, member_id, raw)
        finally:
            if code is not None and member_id is not None:
                await registry.leave(code, member_id)

    return handler


async def serve(host: str, port: int) -> None:
    registry = Registry()
    async with websockets.serve(make_handler(registry), host, port):
        print(f"Desktop Buddies relay listening on ws://{host}:{port}")
        await asyncio.Future()  # run forever


def main() -> None:
    host = os.environ.get("BUDDIES_HOST", "0.0.0.0")
    port = int(os.environ.get("BUDDIES_PORT", "8765"))
    asyncio.run(serve(host, port))
