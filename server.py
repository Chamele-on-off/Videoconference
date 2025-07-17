import asyncio
import ssl
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('websockets')

connections = set()

async def handler(websocket, path):
    connections.add(websocket)
    logger.info(f"New connection: {websocket.remote_address}")
    
    try:
        async for message in websocket:
            logger.info(f"Received: {message[:50]}...")
            for conn in connections:
                if conn != websocket:
                    await conn.send(message)
    except Exception as e:
        logger.error(f"Error: {e}")
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
        ssl=ssl_context,
        ping_timeout=None
    ):
        logger.info("Server started at wss://0.0.0.0:8765")
        await asyncio.Future()

asyncio.run(main())