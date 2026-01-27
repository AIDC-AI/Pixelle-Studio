#!/usr/bin/env python3
"""
Test script for WebSocket chat endpoint.
1. POST /api/chat to create a chat turn
2. Connect to /ws/chat/{chat_id} and receive streaming response

Usage:
    python test_ws_chat.py [test_name]
    
    test_name: basic, file, session (default: basic)
"""

import asyncio
import httpx
import websockets
import json
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# Configuration
# =============================================================================

BASE_URL = "http://localhost:8001"
WS_BASE_URL = "ws://localhost:8001"
DEFAULT_USER_ID = 1
WS_TIMEOUT = 60.0


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ChatRequest:
    """Chat request parameters."""
    message: str
    user_id: int = DEFAULT_USER_ID
    session_id: Optional[str] = None
    file_urls: Optional[list[str]] = None
    file_names: Optional[list[str]] = None


@dataclass
class ChatResponse:
    """Chat creation response."""
    chat_id: str
    session_id: str


# =============================================================================
# Reusable Helper Functions
# =============================================================================

async def create_chat(request: ChatRequest) -> Optional[ChatResponse]:
    """
    Create a chat turn via POST /api/chat.
    
    Args:
        request: ChatRequest with message and optional parameters
        
    Returns:
        ChatResponse with chat_id and session_id, or None on failure
    """
    payload = {
        "message": request.message,
        "user_id": request.user_id,
    }
    
    if request.session_id:
        payload["session_id"] = request.session_id
    if request.file_urls:
        payload["file_urls"] = request.file_urls
    if request.file_names:
        payload["file_names"] = request.file_names
    
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/api/chat", json=payload)
        
        if response.status_code != 200:
            print(f"ERROR: Failed to create chat: {response.status_code}")
            print(f"Response: {response.text}")
            return None
        
        data = response.json()
        return ChatResponse(
            chat_id=data["chat_id"],
            session_id=data["session_id"]
        )


def handle_ws_message(data: dict) -> bool:
    """
    Handle a single WebSocket message.
    
    Args:
        data: Parsed JSON message from WebSocket
        
    Returns:
        True if should continue receiving, False if done
    """
    msg_type = data.get("type", "unknown")
    
    if msg_type == "response_delta":
        # Streaming text - print without newline
        print(data.get("content", ""), end="", flush=True)
        return True
        
    elif msg_type == "final_result":
        # Agent completed
        result = data.get("result", {})
        print(f"\n\n[FINAL_RESULT] Status: {data.get('status')}")
        if isinstance(result, dict) and result.get("answer"):
            print(f"Answer: {result.get('answer')}")
        elif isinstance(result, dict) and result.get("error"):
            print(f"Error: {result.get('error')}")
        return False
        
    elif msg_type == "final":
        print(f"\n\n[FINAL] Status: {data.get('status')}")
        if data.get("response"):
            print(f"Response: {data.get('response')[:200]}...")
        return False
        
    elif msg_type == "error":
        print(f"\n[ERROR] {data.get('content')}")
        return False
        
    elif msg_type == "tool_call":
        print(f"\n[TOOL CALL] {data.get('tool_name')}: {str(data.get('arguments', ''))[:100]}...")
        return True
        
    elif msg_type == "tool_result":
        result = str(data.get('result', ''))[:200]
        print(f"[TOOL RESULT] {result}...")
        return True
        
    elif msg_type == "code_execution":
        print(f"\n[CODE] Executing code...")
        return True
        
    elif msg_type == "code_result":
        print(f"[CODE RESULT] Success: {data.get('success')}")
        return True
        
    else:
        print(f"\n[{msg_type.upper()}] {str(data)[:100]}")
        return True


async def listen_ws_stream(chat_id: str) -> None:
    """
    Connect to WebSocket and listen for streaming response.
    
    Args:
        chat_id: The chat ID to connect to
    """
    ws_url = f"{WS_BASE_URL}/ws/chat/{chat_id}"
    print(f"WebSocket URL: {ws_url}\n")
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("Connected! Receiving messages...\n")
            print("-" * 50)
            
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=WS_TIMEOUT)
                    data = json.loads(msg)
                    
                    if not handle_ws_message(data):
                        break
                        
                except asyncio.TimeoutError:
                    print(f"\n[TIMEOUT] No message received for {WS_TIMEOUT} seconds")
                    break
                except websockets.exceptions.ConnectionClosed as e:
                    print(f"\n[CLOSED] Connection closed: {e}")
                    break
                    
            print("-" * 50)
            
    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()


async def run_chat_test(request: ChatRequest, test_name: str) -> Optional[str]:
    """
    Run a complete chat test: create chat and listen to stream.
    
    Args:
        request: ChatRequest with message and optional parameters
        test_name: Name of the test for logging
        
    Returns:
        session_id if successful, None otherwise
    """
    print(f"\n{'='*60}")
    print(f"  Test: {test_name}")
    print(f"  Message: {request.message[:50]}{'...' if len(request.message) > 50 else ''}")
    if request.file_names:
        print(f"  Files: {request.file_names}")
    if request.session_id:
        print(f"  Session: {request.session_id}")
    print(f"{'='*60}\n")
    
    # Step 1: Create chat
    print("Step 1: Creating chat turn...")
    chat_response = await create_chat(request)
    
    if not chat_response:
        print("Failed to create chat. Test aborted.")
        return None
    
    print(f"Created chat_id: {chat_response.chat_id}, session_id: {chat_response.session_id}\n")
    
    # Step 2: Listen to WebSocket stream
    print("Step 2: Connecting to WebSocket...")
    await listen_ws_stream(chat_response.chat_id)
    
    print(f"\nTest '{test_name}' completed!")
    return chat_response.session_id


# =============================================================================
# Test Cases
# =============================================================================

async def test_basic():
    """
    Test Case 1: Basic chat - simple greeting message.
    
    Tests basic chat functionality without files or session context.
    """
    request = ChatRequest(message="hi, 请简单介绍一下你自己")
    await run_chat_test(request, "Basic Chat")


async def test_html():
    request = ChatRequest(message="生成一个贪吃蛇的html")
    await run_chat_test(request, "Chat with HTML")

async def test_xlsx_total_price():
    """
    Test Case 2: Chat with file - Excel processing.
    
    Tests file upload and processing capability.
    Requires a valid file URL accessible by the server.
    """
    # Note: Update these URLs to match your actual test files
    request = ChatRequest(
        message="给当前的excel文档，先 单价这列 * 销量这列 = 总价这列，再总价求和获得总营收",
        file_urls=["http://30.150.44.149:8001/f/1/7654.xlsx"],
        file_names=["7654.xlsx"]
    )
    await run_chat_test(request, "Chat with File")


async def test_csv_top_10_salary():
    """
    Test Case 3: Chat with file - CSV processing.
    
    Tests file upload and processing capability.
    Requires a valid file URL accessible by the server.
    """
    request = ChatRequest(
        message="找出薪资水平处于所属岗位前10%的员工名单,输入的薪资文件表包含列如下:[员工ID,姓名,部门,岗位,职级,月薪,年终奖,入职日期]",
        file_urls=["http://30.150.44.149:8001/f/1/764d.csv"],
        file_names=["764d.csv"]
    )
    await run_chat_test(request, "Chat with CSV")

async def test_ppt():
    request = ChatRequest(
        message="我想生成一份ppt,用来做技术分享,以Claude skills的背景、原理、应用场景、具体案例、总结和展望的大纲来生成。简短的做3页ppt",
    )
    await run_chat_test(request, "Chat with PPT")

async def test_multi_turn_session():
    """
    Test Case 3: Multi-turn session - conversation continuity.
    
    Tests that the agent can maintain context across multiple turns
    in the same session.
    """
    # Turn 1: Start conversation
    request1 = ChatRequest(message="我叫小明，请记住我的名字")
    session_id = await run_chat_test(request1, "Session Turn 1")
    
    if not session_id:
        print("Turn 1 failed, cannot continue session test")
        return
    
    # Small delay between turns
    await asyncio.sleep(1)
    
    # Turn 2: Continue with context
    request2 = ChatRequest(
        message="请问我叫什么名字？",
        session_id=session_id
    )
    await run_chat_test(request2, "Session Turn 2")


# =============================================================================
# Main Entry Point
# =============================================================================

TEST_CASES = {
    "basic": test_basic,
    "html": test_html,
    "file": test_xlsx_total_price,
    "csv": test_csv_top_10_salary,
    "ppt": test_ppt,
    "session": test_multi_turn_session,
    "all": None,  # Special case to run all tests
}


async def run_all_tests():
    """Run all test cases sequentially."""
    print("\n" + "="*60)
    print("  Running ALL Test Cases")
    print("="*60)
    
    await test_basic()
    print("\n" + "-"*60 + "\n")
    
    await test_html()
    print("\n" + "-"*60 + "\n")
    
    await test_xlsx_total_price()
    print("\n" + "-"*60 + "\n")
    
    await test_csv_top_10_salary()
    print("\n" + "-"*60 + "\n")
    
    await test_ppt()
    print("\n" + "-"*60 + "\n")
    
    await test_multi_turn_session()
    
    print("\n" + "="*60)
    print("  All Tests Completed!")
    print("="*60 + "\n")


def print_usage():
    """Print usage information."""
    print("""
Usage: python test_ws_chat.py [test_name]

Available tests:
  basic   - Simple greeting message (default)
  html    - Chat with HTML generation
  file    - Chat with Excel file processing
  session - Multi-turn conversation with session context
  all     - Run all tests sequentially

Examples:
  python test_ws_chat.py
  python test_ws_chat.py basic
  python test_ws_chat.py html
  python test_ws_chat.py file
  python test_ws_chat.py session
  python test_ws_chat.py all
""")


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        
        if test_name in ("-h", "--help", "help"):
            print_usage()
            sys.exit(0)
            
        if test_name not in TEST_CASES:
            print(f"Unknown test: {test_name}")
            print_usage()
            sys.exit(1)
    else:
        test_name = "basic"
    
    # Run the selected test
    if test_name == "all":
        asyncio.run(run_all_tests())
    else:
        asyncio.run(TEST_CASES[test_name]())
