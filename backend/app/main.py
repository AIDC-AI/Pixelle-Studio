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

# Import self-evaluation modules
from app.context.context_manager import ContextManager
from app.orchestrator.execution_orchestrator import ExecutionOrchestrator, ExecutionConfig

# Import logger
from app.utils.logger import log

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

# Initialize Context Manager and Orchestrator (NEW)
context_manager = ContextManager()
execution_config = ExecutionConfig(
    max_iterations=3,
    enable_error_evaluation=True,
    enable_result_validation=True
)
orchestrator = ExecutionOrchestrator(
    context_manager=context_manager,
    config=execution_config
)

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
        "messages": [{
            "role": "user",
            "content": request.message
        }],
        "mcp_config": request.mcp_config,  # Store config
        "status": "created"
    }
    return {"chat_id": chat_id}


async def process_and_execute(websocket: WebSocket, chat_id: str,
                              user_message: str):
    """
    Process a user message: select tools, generate script, and execute it.
    Now uses ExecutionOrchestrator for self-evaluation loop.
    """
    try:
        log.info(f"Processing message for {chat_id}: {user_message}")
        
        # === Stage 1: Analyze and select tools ===
        await websocket.send_json({"type": "status", "content": "Analyzing request and selecting tools..."})
        
        log.debug("Sent analyzing status")
        
        # Fetch tools using the stored config
        chat_config = chats[chat_id].get("mcp_config")
        config_to_use = chat_config or mcp_config_cache or MCPServerConfig(servers=[])
        
        all_tools = await mcp_aggregator.fetch_tools(config_to_use)
        selected_tools = select_tools(user_message, all_tools)
        chats[chat_id]["tools"] = selected_tools
        
        # === Stage 2: Execute with self-evaluation (NEW) ===
        execution_context = await orchestrator.execute_with_self_evaluation(
            websocket=websocket,
            chat_id=chat_id,
            user_message=user_message,
            selected_tools=selected_tools
        )
        
        # === Stage 3: Send final result ===
        if execution_context.status == "success":
            latest_iter = execution_context.get_latest_iteration()
            await websocket.send_json({
                "type": "final_result",
                "status": "success",
                "total_iterations": len(execution_context.iterations),
                "result": latest_iter.execution_result if latest_iter else None
            })
        else:
            await websocket.send_json({
                "type": "final_result",
                "status": "failed",
                "total_iterations": len(execution_context.iterations),
                "error": "Maximum iterations reached or unrecoverable error"
            })

    except WebSocketDisconnect:
        # Client went away; stop processing quietly
        log.info(f"WebSocket disconnected while processing chat {chat_id}")
        return
    except Exception as e:
        log.error(f"Error processing message for chat {chat_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            # If the socket is already closed, just exit
            pass


@app.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    log.info(f"New websocket connection: {chat_id}")
    await websocket.accept()
    log.debug("Websocket accepted")
    
    log.debug(f"Current chats: {list(chats.keys())}")
    
    if chat_id not in chats:
        log.warning(f"Chat not found: {chat_id}")
        await websocket.close(code=4004, reason="Chat not found")
        return

    try:
        # Process initial message if it exists and hasn't been processed
        status = chats[chat_id].get("status")
        log.debug(f"Chat status: {status}")
            
        if status == "created":
            log.info("Processing initial message")
            initial_message = chats[chat_id]["messages"][0]["content"]
            chats[chat_id]["status"] = "active"
            await process_and_execute(websocket, chat_id, initial_message)

        # Loop for subsequent messages
        while True:
            log.debug("Waiting for next message")
            data = await websocket.receive_json()
            log.debug(f"Received message: {data}")
            
            if data.get("type") == "message":
                user_message = data.get("content")
                if user_message:
                    # Add to history
                    chats[chat_id]["messages"].append({
                        "role": "user",
                        "content": user_message
                    })
                    # Process
                    await process_and_execute(websocket, chat_id, user_message)

    except WebSocketDisconnect:
        log.info(f"[WebSocket] Client disconnected: {chat_id}")
    except Exception as e:
        import traceback
        log.error(f"[WebSocket] Error in chat {chat_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            # If we can't send, client already disconnected
            log.error(f"[WebSocket] Failed to send error, client disconnected: {e}")


@app.post("/api/tools")
async def get_tools(config: Optional[MCPServerConfig] = None):
    """
    Fetch tools from all configured servers + default tools.
    """
    if config:
        log.info(f"Fetching tools with config: {len(config.servers)} servers")
        return await mcp_aggregator.fetch_tools(config)

    # Return default tools if no config
    return mcp_aggregator._get_default_tools()


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "self_evaluation": "enabled",
        "max_iterations": execution_config.max_iterations
    }
