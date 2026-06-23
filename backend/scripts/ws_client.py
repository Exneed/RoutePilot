import asyncio
import websockets

async def main():
    uri = 'ws://localhost:8000/ws/trip/demo_trip'
    async with websockets.connect(uri) as ws:
        await ws.send('ready')
        while True:
            msg = await ws.recv()
            print('recv:', msg)

if __name__ == '__main__':
    asyncio.run(main())
