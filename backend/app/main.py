from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import asyncio
import json
import os
import shutil
import socket
from pathlib import Path

# Import modules
from app.llm_adapter import generate_workflow_script, check_if_workflow_needed
from app.execution.runner import run_script
from app.mcp_aggregator import MCPAggregator, MCPServerConfig
from app.tool_search.selector import select_tools
from app.tool_search.search_agent import SearchAgent

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

# Create storage directory if it doesn't exist
STORAGE_DIR = Path(__file__).parent / "storage" / "files"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Get local IP address
def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
log.info(f"Local IP address: {LOCAL_IP}")

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
    file_urls: Optional[List[str]] = None  # File URLs uploaded by user


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
        "file_urls": request.file_urls or [],  # Store file URLs
        "status": "created"
    }
    return {"chat_id": chat_id}


async def process_and_execute(websocket: WebSocket, chat_id: str,
                              user_message: str):
    """
    Process a user message: first check if workflow is needed, then execute accordingly.
    If workflow not needed, directly return answer. Otherwise use ExecutionOrchestrator.
    """
    try:
        log.info(f"Processing message for {chat_id}: {user_message}")
        
        # Get file URLs from chat context
        file_urls = chats[chat_id].get("file_urls", [])
        
        # === Stage 0: Check if workflow is needed ===
        await websocket.send_json({"type": "status", "content": "Analyzing request..."})
        
        # Fetch tools using the stored config
        chat_config = chats[chat_id].get("mcp_config")
        config_to_use = chat_config or mcp_config_cache or MCPServerConfig(servers=[])
        
        all_tools = await mcp_aggregator.fetch_tools(config_to_use)
        selected_tools = await select_tools(user_message, all_tools)
        chats[chat_id]["tools"] = selected_tools
        
        # Check if workflow is needed
        workflow_check = await check_if_workflow_needed(user_message, selected_tools, file_urls)
        log.info(f"Workflow check result: {workflow_check}")
        
        if not workflow_check.get("needs_workflow", True):
            # === Direct answer path ===
            log.info("Direct answer mode - no workflow needed")
            await websocket.send_json({
                "type": "status",
                "content": f"💡 Reasoning: {workflow_check.get('reasoning', 'Simple query')}"
            })
            
            direct_answer = workflow_check.get("direct_answer", "I understand your question.")
            await websocket.send_json({
                "type": "final_result",
                "status": "success",
                "total_iterations": 0,
                "result": {
                    "answer": direct_answer,
                    "file_urls": file_urls,
                    "reasoning": workflow_check.get("reasoning", "")
                }
            })
            return
        
        # === Workflow execution path ===
        log.info("Workflow mode - generating and executing script")
        await websocket.send_json({
            "type": "status",
            "content": f"🔧 {workflow_check.get('reasoning', 'Complex workflow detected - generating script...')}"
        })
        
        # === Stage 1: Execute with self-evaluation ===
        execution_context = await orchestrator.execute_with_self_evaluation(
            websocket=websocket,
            chat_id=chat_id,
            user_message=user_message,
            selected_tools=selected_tools,
            file_urls=file_urls
        )
        
        # === Stage 2: Send final result ===
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
        tools = await mcp_aggregator.fetch_tools_by_server(config)
        #for debug, save the tools to a file
        # if not os.path.exists("./logs"):
        #     os.makedirs("./logs", exist_ok=True)
        # with open("./logs/config_tools.json", "w") as f:
        #     json.dump(tools, f, indent=4, ensure_ascii=False)
        await SearchAgent.instance.embedding_tools(config,tools)
        return [tool for server_tools in tools for tool in server_tools]
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


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), request: Request = None):
    """
    Upload a file and return a short URL for LAN access.
    """
    try:
        # Generate a unique short filename
        file_id = str(uuid.uuid4())[:4]  # Short ID for URL (4 chars)
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{file_id}{file_extension}"
        
        # Save file to storage
        file_path = STORAGE_DIR / unique_filename
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        log.info(f"File uploaded: {file.filename} -> {unique_filename}")
        
        # Get port from request
        port = request.url.port if request and request.url.port else 8001
        
        # Return short URL with LAN IP
        lan_url = f"http://{LOCAL_IP}:{port}/f/{unique_filename}"
        
        return {
            "success": True,
            "url": lan_url,
            "filename": file.filename,
            "size": file_path.stat().st_size
        }
    
    except Exception as e:
        log.error(f"File upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/f/{filename}")
async def get_file(filename: str):
    """
    Serve uploaded files with a short URL.
    """
    file_path = STORAGE_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)