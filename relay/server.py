import asyncio
import logging
import os

import websockets
from websockets.exceptions import ConnectionClosed

from relay.room import JoinError, Registry
from shared import messages as m

log = logging.getLogger("relay.server")

# Every real message is a few hundred bytes; the library default (1 MiB)
# only helps someone trying to fill the relay's memory.
MAX_FRAME = 64 * 1024


def make_handler(registry: Registry):
    async def handler(websocket):
        code: str | None = None
        member_id: str | None = None

        async def send(raw: str) -> None:
            await websocket.send(raw)

        log.info("connection opened")
        try:
            async for raw in websocket:
                msg = m.decode(raw)
                if msg is None:
                    continue
                mtype = msg.get("type")

                if mtype == m.CREATE_ROOM and member_id is None:
                    code, member_id = await registry.create_room(
                        msg.get("name", ""), msg.get("appearance", {}), send)
                    log.info("room %s created by member %s", code, member_id)

                elif mtype == m.JOIN_ROOM and member_id is None:
                    requested = str(msg.get("code", ""))[:16]
                    try:
                        mid = await registry.join_room(
                            msg.get("code", ""), msg.get("name", ""),
                            msg.get("appearance", {}), send)
                    except JoinError as err:
                        log.info("join refused for room %s: %s",
                                 requested, err.reason)
                        await send(m.encode(m.ERROR, reason=err.reason))
                    else:
                        code, member_id = msg["code"], mid
                        log.info("member %s joined room %s", member_id, code)

                elif mtype in (m.STATE, m.CHAT, m.POKE) and member_id is not None:
                    await registry.relay(code, member_id, raw)
        except ConnectionClosed:
            pass   # a peer that vanished without a handshake is normal
        finally:
            if code is not None and member_id is not None:
                await registry.leave(code, member_id)
            log.info("connection closed (member %s, room %s)", member_id, code)

    return handler


async def start_server(host: str, port: int,
                       registry: Registry | None = None):
    """Start listening and return the server. Tests use this directly so
    they exercise the same limits production runs with."""
    if registry is None:
        registry = Registry()
    return await websockets.serve(make_handler(registry), host, port,
                                  max_size=MAX_FRAME)


async def serve(host: str, port: int) -> None:
    server = await start_server(host, port)
    log.info("Desktop Buddies relay listening on ws://%s:%s", host, port)
    await server.wait_closed()


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    host = os.environ.get("BUDDIES_HOST", "0.0.0.0")
    port = int(os.environ.get("BUDDIES_PORT", "8765"))
    asyncio.run(serve(host, port))
