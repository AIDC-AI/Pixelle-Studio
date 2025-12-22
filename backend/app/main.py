"""
MCP Workflow Backend - Simplified with Single Agent Architecture.

This is a chat-based interface where a single agent handles all user requests,
using skill guidance when appropriate.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json
import shutil
import socket
from pathlib import Path

# Import the simplified agent
from app.agent import SkillAgent

# Import skills loader for API endpoints
from app.skills.loader import get_skill_loader

# Import logger
from app.utils.logger import log

app = FastAPI(title="MCP Workflow API", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage directory for uploaded files
STORAGE_DIR = Path(__file__).parent / "storage" / "files"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


LOCAL_IP = get_local_ip()
log.info(f"Local IP address: {LOCAL_IP}")

# In-memory chat storage
chats = {}

# Initialize skill loader
skill_loader = get_skill_loader()
skills_list = skill_loader.scan_skills()
log.info(f"Loaded {len(skills_list)} skills: {[s.name for s in skills_list]}")


class ChatRequest(BaseModel):
    message: str
    file_urls: Optional[List[str]] = None


class ChatResponse(BaseModel):
    chat_id: str


@app.post("/api/chat", response_model=ChatResponse)
async def create_chat(request: ChatRequest):
    """Create a new chat session."""
    chat_id = str(uuid.uuid4())
    chats[chat_id] = {
        "messages": [{
            "role": "user",
            "content": request.message
        }],
        "file_urls": request.file_urls or [],
        "status": "created"
    }
    log.info(f"Created chat {chat_id}: {request.message[:50]}...")
    return {"chat_id": chat_id}


@app.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    """WebSocket endpoint for chat interaction."""
    await websocket.accept()
    log.info(f"WebSocket connected: {chat_id}")
    
    if chat_id not in chats:
        await websocket.close(code=4004, reason="Chat not found")
        return
    
    try:
        chat = chats[chat_id]
        
        # Process initial message if chat was just created
        if chat["status"] == "created":
            chat["status"] = "active"
            user_message = chat["messages"][0]["content"]
            file_urls = chat.get("file_urls", [])
            
            await process_with_agent(websocket, chat_id, user_message, file_urls)
        
        # Listen for follow-up messages
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                user_message = data.get("content", "")
                file_urls = data.get("file_urls", [])
                
                if user_message:
                    chat["messages"].append({
                        "role": "user",
                        "content": user_message
                    })
                    await process_with_agent(websocket, chat_id, user_message, file_urls)
    
    except WebSocketDisconnect:
        log.info(f"WebSocket disconnected: {chat_id}")
    except Exception as e:
        log.error(f"WebSocket error for {chat_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass


async def process_with_agent(
    websocket: WebSocket,
    chat_id: str,
    user_message: str,
    file_urls: List[str]
):
    """
    Process a user message using the single agent.
    
    The agent handles everything:
    - Deciding whether to answer directly or execute code
    - Loading skills when needed
    - Executing code and evaluating results
    - Continuing until task is complete
    """
    try:
        agent = SkillAgent(max_tool_calls=10)
        
        async for event in agent.run(
            user_message=user_message,
            file_urls=file_urls,
            session_id=chat_id[:8]
        ):
            # Forward all events to the frontend
            await websocket.send_json(event)
            
            # Log important events
            event_type = event.get("type")
            if event_type == "status":
                log.info(f"[{chat_id[:8]}] Status: {event.get('content', '')[:50]}")
            elif event_type == "code":
                log.info(f"[{chat_id[:8]}] Executing code #{event.get('execution_count', 0)}")
            elif event_type == "execution_result":
                log.info(f"[{chat_id[:8]}] Execution result: {event.get('status')}")
            elif event_type == "final_result":
                log.info(f"[{chat_id[:8]}] Final: {event.get('status')}")
    
    except WebSocketDisconnect:
        log.info(f"Client disconnected during processing: {chat_id}")
    except Exception as e:
        log.error(f"Error processing message for {chat_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass


# ============================================================================
# Skills API
# ============================================================================

@app.get("/api/skills")
async def get_skills():
    """Get all available skills metadata."""
    return {
        "skills": [s.to_dict() for s in skills_list],
        "count": len(skills_list)
    }


@app.get("/api/skills/{skill_name}")
async def get_skill_detail(skill_name: str):
    """Get full content of a specific skill."""
    content = skill_loader.read_skill(skill_name)
    if content is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    
    meta = skill_loader.get_skill_meta(skill_name)
    files = skill_loader.list_skill_files(skill_name)
    
    return {
        "name": skill_name,
        "meta": meta.to_dict() if meta else None,
        "content": content,
        "files": files
    }


# ============================================================================
# File Upload API
# ============================================================================

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), request: Request = None):
    """Upload a file and return a URL for access."""
    try:
        file_id = str(uuid.uuid4())[:4]
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{file_id}{file_extension}"
        
        file_path = STORAGE_DIR / unique_filename
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        log.info(f"File uploaded: {file.filename} -> {unique_filename}")
        
        port = request.url.port if request and request.url.port else 8001
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
    """Serve uploaded files."""
    file_path = STORAGE_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "architecture": "single_agent",
        "skills_loaded": len(skills_list)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
