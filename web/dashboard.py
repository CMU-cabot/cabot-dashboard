# このコードは、ダッシュボードをシミュレートし、サーバーからのメッセージを表示します。

import asyncio
import websockets

async def dashboard():
    uri = "ws://localhost:8000/ws/dashboard"
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            print(f"受信: {message}")

if __name__ == "__main__":
    asyncio.run(dashboard())