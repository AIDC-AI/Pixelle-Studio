import asyncio
import aiohttp
import sys
import json

async def test_chat():
    async with aiohttp.ClientSession() as session:
        # 1. Create Chat
        print("Creating chat...")
        async with session.post('http://localhost:8003/api/chat', json={
            "message": "List files in current directory",
            "mcp_config": {
                "servers": []
            }
        }) as resp:
            if resp.status != 200:
                print(f"Error creating chat: {await resp.text()}")
                return
            data = await resp.json()
            chat_id = data['chat_id']
            print(f"Chat created with ID: {chat_id}")

        # 2. Connect to WebSocket
        ws_url = f"ws://localhost:8003/wa/chat/{chat_id}"
        print(f"Connecting to WebSocket: {ws_url}")
        
        async with session.ws_connect(ws_url) as ws:
            print("Connected!")
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    print(f"Received: {data.get('type')} - {data.get('content')}")
                    if data.get('type') == 'error':
                        break
                    # In a real scenario we might wait for 'finish' or similar, 
                    # but here we just want to see some progress
                    if "Turn complete" in str(data.get('content')):
                        print("First turn complete. Sending second message...")
                        await ws.send_json({"type": "message", "content": "List files in parent directory"})
                        
                    if "Executing workflow" in str(data.get('content')):
                         print("Execution started...") 
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print('ws connection closed with exception %s',
                          ws.exception())
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    print("WebSocket closed")
                    break

if __name__ == "__main__":
    try:
        asyncio.run(test_chat())
    except KeyboardInterrupt:
        pass
