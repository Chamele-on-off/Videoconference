import asyncio
import websockets
import json

connections = {}

async def handler(websocket, path):
    room_id = path.strip('/')
    if room_id not in connections:
        connections[room_id] = set()
    
    connections[room_id].add(websocket)
    print(f"New connection in room {room_id}")

    try:
        async for message in websocket:
            data = json.loads(message)
            for client in connections[room_id]:
                if client != websocket:
                    await client.send(message)
    finally:
        connections[room_id].remove(websocket)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()  # Бесконечный цикл

asyncio.run(main())
