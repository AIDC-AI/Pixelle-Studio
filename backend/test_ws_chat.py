#!/usr/bin/env python3
"""
Test script for WebSocket chat endpoint.
1. POST /api/chat to create a chat turn
2. Connect to /ws/chat/{chat_id} and receive streaming response
"""

import asyncio
import httpx
import websockets
import json

BASE_URL = "http://localhost:8001"
WS_BASE_URL = "ws://localhost:8001"


async def test_chat(message: str = "hi"):
    """Test the chat endpoint with a simple message."""
    print(f"=== Testing chat with message: '{message}' ===\n")
    
    # Step 1: Create chat via POST /api/chat
    print("Step 1: Creating chat turn...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": message,
                "user_id": 1,  # Test user
            }
        )
        
        if response.status_code != 200:
            print(f"ERROR: Failed to create chat: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        data = response.json()
        chat_id = data["chat_id"]
        session_id = data["session_id"]
        print(f"Created chat_id: {chat_id}, session_id: {session_id}\n")
    
    # Step 2: Connect to WebSocket
    print("Step 2: Connecting to WebSocket...")
    ws_url = f"{WS_BASE_URL}/ws/chat/{chat_id}"
    print(f"WebSocket URL: {ws_url}\n")
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("Connected! Receiving messages...\n")
            print("-" * 50)
            
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=60.0)
                    data = json.loads(msg)
                    
                    msg_type = data.get("type", "unknown")
                    
                    if msg_type == "response_delta":
                        # Streaming text - print without newline
                        print(data.get("content", ""), end="", flush=True)
                    elif msg_type == "final_result":
                        # Agent completed
                        result = data.get("result", {})
                        print(f"\n\n[FINAL_RESULT] Status: {data.get('status')}")
                        if isinstance(result, dict) and result.get("answer"):
                            print(f"Answer: {result.get('answer')}")
                        elif isinstance(result, dict) and result.get("error"):
                            print(f"Error: {result.get('error')}")
                        break
                    elif msg_type == "final":
                        print(f"\n\n[FINAL] Status: {data.get('status')}")
                        if data.get("response"):
                            print(f"Response: {data.get('response')[:200]}...")
                        break
                    elif msg_type == "error":
                        print(f"\n[ERROR] {data.get('content')}")
                        break
                    elif msg_type == "tool_call":
                        print(f"\n[TOOL CALL] {data.get('tool_name')}: {str(data.get('arguments', ''))[:100]}...")
                    elif msg_type == "tool_result":
                        result = str(data.get('result', ''))[:200]
                        print(f"[TOOL RESULT] {result}...")
                    elif msg_type == "code_execution":
                        print(f"\n[CODE] Executing code...")
                    elif msg_type == "code_result":
                        print(f"[CODE RESULT] Success: {data.get('success')}")
                    else:
                        print(f"\n[{msg_type.upper()}] {str(data)[:100]}")
                        
                except asyncio.TimeoutError:
                    print("\n[TIMEOUT] No message received for 60 seconds")
                    break
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"\n[CLOSED] Connection closed: {e}")
                    break
                    
            print("-" * 50)
            print("\nTest completed!")
            
    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    message = sys.argv[1] if len(sys.argv) > 1 else "hi"
    asyncio.run(test_chat(message))
