import asyncio
import ssl
import websockets
from pathlib import Path

connections = set()

async def handler(websocket, path):
    connections.add(websocket)
    try:
        async for message in websocket:
            for conn in connections:
                if conn != websocket:
                    await conn.send(message)
    finally:
        connections.remove(websocket)

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(
    certfile='ssl/cert.pem',
    keyfile='ssl/key.pem'
)

async def main():
    async with websockets.serve(
        handler,
        host="0.0.0.0",
        port=8765,
        ssl=ssl_context
    ):
        await asyncio.Future()  # Бесконечный цикл

asyncio.run(main())