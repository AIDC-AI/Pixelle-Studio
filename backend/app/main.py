from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import asyncio
import json
import os

# Import modules
from app.llm_adapter import generate_workflow_script
from app.execution.runner import run_script
from app.mcp_aggregator import MCPAggregator, MCPServerConfig
from app.tool_search.selector import select_tools

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
chats = {}
scripts = {}

# Initialize MCP Config - in production this would come from a config file or database
# For now, we load from the frontend's saved config
mcp_config_cache = None

# Initialize Aggregator
mcp_aggregator = MCPAggregator()

class ChatRequest(BaseModel):
    message: str
    mcp_config: Optional[MCPServerConfig] = None  # Frontend sends this

class ChatResponse(BaseModel):
    chat_id: str

@app.post("/api/chat", response_model=ChatResponse)
async def create_chat(request: ChatRequest):
    print(f"Creating chat with request: {request}")
    global mcp_config_cache
    
    # Update cache if provided
    if request.mcp_config:
        mcp_config_cache = request.mcp_config
    
    # Store mcp_config in the chat session for later use
    # We don't fetch tools here anymore, we do it in the WebSocket connection
    
    chat_id = str(uuid.uuid4())
    chats[chat_id] = {
        "messages": [{"role": "user", "content": request.message}],
        "mcp_config": request.mcp_config,  # Store config
        "status": "created"
    }
    return {"chat_id": chat_id}

async def process_and_execute(websocket: WebSocket, chat_id: str, user_message: str):
    """
    Process a user message: select tools, generate script, and execute it.
    """
    try:
        with open("/tmp/debug_absolute.log", "a") as f:
            f.write(f"Processing message for {chat_id}: {user_message}\n")
        # 1. Notify start
        await websocket.send_json({"type": "status", "content": "Analyzing request..."})
        await websocket.send_json({"type": "status", "content": "Analyzing request..."})
        with open("/tmp/debug_absolute.log", "a") as f:
            f.write("Sent analyzing status\n")
        
        # Fetch tools using the stored config
        chat_config = chats[chat_id].get("mcp_config")
        # Use global cache if chat specific config is missing (fallback)
        config_to_use = chat_config or mcp_config_cache or MCPServerConfig(servers=[])
        
        all_tools = await mcp_aggregator.fetch_tools(config_to_use)
        
        # Select tools
        selected_tools = select_tools(user_message, all_tools)
        chats[chat_id]["tools"] = selected_tools # Store for reference
        
        # 2. Generate Script
        script_content = await generate_workflow_script(user_message, selected_tools)
        
        # Save script to file
        # Use a directory outside of 'backend' to prevent uvicorn auto-reload
        script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../scripts"))
        os.makedirs(script_dir, exist_ok=True)
        script_path = os.path.join(script_dir, f"{chat_id}_{uuid.uuid4().hex[:8]}.py") # Unique script per turn
        
        with open(script_path, "w") as f:
            f.write(script_content)
            
        # Store latest script
        scripts[chat_id] = script_path
        
        await websocket.send_json({"type": "script", "content": script_content})
        
        # 3. Execute Script
        await websocket.send_json({"type": "status", "content": "Executing workflow..."})
        
        # Run script and stream logs
        async for log in run_script(script_path, cwd=os.path.dirname(script_path)):
            await websocket.send_json(log)
            
        await websocket.send_json({"type": "status", "content": "Turn complete"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        await websocket.send_json({"type": "error", "content": str(e)})

@app.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    with open("/tmp/debug_absolute.log", "a") as f:
        f.write(f"New websocket connection: {chat_id}\n")
    await websocket.accept()
    with open("/tmp/debug_absolute.log", "a") as f:
        f.write("Websocket accepted\n")
    
    with open("/tmp/debug_absolute.log", "a") as f:
        f.write(f"Current chats: {list(chats.keys())}\n")
    
    if chat_id not in chats:
        with open("/tmp/debug_absolute.log", "a") as f:
            f.write(f"Chat not found: {chat_id}\n")
        await websocket.close(code=4004, reason="Chat not found")
        return

    try:
        # Process initial message if it exists and hasn't been processed
        status = chats[chat_id].get("status")
        with open("/tmp/debug_absolute.log", "a") as f:
            f.write(f"Chat status: {status}\n")
            
        if status == "created":
            with open("/tmp/debug_absolute.log", "a") as f:
                f.write("Processing initial message\n")
            initial_message = chats[chat_id]["messages"][0]["content"]
            chats[chat_id]["status"] = "active"
            await process_and_execute(websocket, chat_id, initial_message)
        
        # Loop for subsequent messages
        while True:
            print("Waiting for next message")
            data = await websocket.receive_json()
            print(f"Received message: {data}")
            
            if data.get("type") == "message":
                user_message = data.get("content")
                if user_message:
                    # Add to history
                    chats[chat_id]["messages"].append({"role": "user", "content": user_message})
                    # Process
                    await process_and_execute(websocket, chat_id, user_message)
            
    except WebSocketDisconnect:
        print(f"Client disconnected: {chat_id}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        await websocket.send_json({"type": "error", "content": str(e)})

@app.post("/api/tools")
async def get_tools(config: Optional[MCPServerConfig] = None):
    """
    Fetch tools from all configured servers + default tools.
    """
    if config:
        print(f"Fetching tools with config: {len(config.servers)} servers")
        return await mcp_aggregator.fetch_tools(config)
    
    # Return default tools if no config
    return mcp_aggregator._get_default_tools()
