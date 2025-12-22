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
# Import modules
from app.llm_adapter import generate_workflow_script, check_if_workflow_needed
from app.execution.runner import run_script
from app.mcp_aggregator import MCPAggregator, MCPServerConfig
# from app.tool_search.selector import select_tools
# from app.tool_search.search_agent import SearchAgent

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
# STORAGE_DIR = Path(__file__).parent.parent / "storage" / "files"
STORAGE_DIR = Path(__file__).parent.parent / "scripts"
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
    
    log.debug("Websocket accepted")

    log.debug(f"Current chats: {list(chats.keys())}")

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
@app.get("/api/skills")
async def get_skills():
    """
    Get all skills from the skillset folder.
    Returns a list of skill names (folder names).
    """
    try:
        skillset_dir = Path(__file__).parent.parent / "skillset"
        
        if not skillset_dir.exists():
            return {"skills": []}
        
        # Get all subdirectories in skillset folder
        skills = []
        for item in skillset_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if SKILL.md exists
                skill_md = item / "SKILL.md"
                skill_info = {
                    "name": item.name,
                    "path": str(item.relative_to(skillset_dir.parent)),
                    "has_description": skill_md.exists()
                }
                
                # Parse SKILL.md front matter if exists
                if skill_md.exists():
                    try:
                        with open(skill_md, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # Parse YAML front matter
                            if content.startswith('---'):
                                parts = content.split('---', 2)
                                if len(parts) >= 3:
                                    front_matter = parts[1].strip()
                                    # Simple parsing for description field
                                    for line in front_matter.split('\n'):
                                        if line.strip().startswith('description:'):
                                            # Extract description value (handle quotes)
                                            desc = line.split('description:', 1)[1].strip()
                                            # Remove surrounding quotes if present
                                            if desc.startswith('"') and desc.endswith('"'):
                                                desc = desc[1:-1]
                                            elif desc.startswith("'") and desc.endswith("'"):
                                                desc = desc[1:-1]
                                            skill_info["description"] = desc
                                            break
                    except Exception as e:
                        log.warning(f"Failed to read SKILL.md for {item.name}: {e}")
                        skill_info["description"] = ""
                
                skills.append(skill_info)
        
        return {"skills": skills}
    
    except Exception as e:
        log.error(f"Error getting skills: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills/{skill_name}")
async def get_skill_detail(skill_name: str):
    """
    Get detailed content of a specific skill.
    Returns the full SKILL.md content and metadata.
    """
    try:
        skillset_dir = Path(__file__).parent.parent / "skillset"
        skill_dir = skillset_dir / skill_name
        
        if not skill_dir.exists() or not skill_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
        
        skill_md = skill_dir / "SKILL.md"
        
        if not skill_md.exists():
            raise HTTPException(status_code=404, detail=f"SKILL.md not found for '{skill_name}'")
        
        # Read full content
        with open(skill_md, 'r', encoding='utf-8') as f:
            full_content = f.read()
        
        # Parse front matter and body
        metadata = {}
        body = full_content
        
        if full_content.startswith('---'):
            parts = full_content.split('---', 2)
            if len(parts) >= 3:
                front_matter = parts[1].strip()
                body = parts[2].strip()
                
                # Parse front matter fields
                for line in front_matter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        metadata[key] = value
        
        # Get list of files in skill directory
        files = []
        for file in skill_dir.iterdir():
            if file.is_file():
                files.append({
                    "name": file.name,
                    "size": file.stat().st_size,
                    "path": str(file.relative_to(skillset_dir.parent))
                })
        
        return {
            "name": skill_name,
            "metadata": metadata,
            "content": body,
            "full_content": full_content,
            "files": files
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting skill detail for {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class CreateSkillRequest(BaseModel):
    name: str
    content: str  # Full SKILL.md content


class UpdateSkillRequest(BaseModel):
    new_name: Optional[str] = None  # If provided, rename the skill
    content: str  # Updated SKILL.md content


@app.post("/api/skills")
async def create_skill(request: CreateSkillRequest):
    """
    Create a new skill.
    """
    try:
        skillset_dir = Path(__file__).parent.parent / "skillset"
        skillset_dir.mkdir(parents=True, exist_ok=True)
        
        skill_dir = skillset_dir / request.name
        
        # Check if skill already exists
        if skill_dir.exists():
            raise HTTPException(status_code=400, detail=f"Skill '{request.name}' already exists")
        
        # Create skill directory
        skill_dir.mkdir(parents=True)
        
        # Create SKILL.md file
        skill_md = skill_dir / "SKILL.md"
        with open(skill_md, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        log.info(f"Created skill: {request.name}")
        
        return {
            "success": True,
            "name": request.name,
            "path": str(skill_dir.relative_to(skillset_dir.parent))
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating skill {request.name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/skills/{skill_name}")
async def update_skill(skill_name: str, request: UpdateSkillRequest):
    """
    Update an existing skill.
    Can rename the skill and/or update its content.
    """
    try:
        skillset_dir = Path(__file__).parent.parent / "skillset"
        skill_dir = skillset_dir / skill_name
        
        if not skill_dir.exists() or not skill_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
        
        # Handle rename if new_name is provided
        if request.new_name and request.new_name != skill_name:
            new_skill_dir = skillset_dir / request.new_name
            
            # Check if new name already exists
            if new_skill_dir.exists():
                raise HTTPException(status_code=400, detail=f"Skill '{request.new_name}' already exists")
            
            # Rename directory
            skill_dir.rename(new_skill_dir)
            skill_dir = new_skill_dir
            log.info(f"Renamed skill from '{skill_name}' to '{request.new_name}'")
        
        # Update SKILL.md content
        skill_md = skill_dir / "SKILL.md"
        with open(skill_md, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        final_name = request.new_name if request.new_name else skill_name
        log.info(f"Updated skill: {final_name}")
        
        return {
            "success": True,
            "name": final_name,
            "path": str(skill_dir.relative_to(skillset_dir.parent))
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating skill {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/skills/{skill_name}")
async def delete_skill(skill_name: str):
    """
    Delete a skill and all its files.
    """
    try:
        skillset_dir = Path(__file__).parent.parent / "skillset"
        skill_dir = skillset_dir / skill_name
        
        if not skill_dir.exists() or not skill_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
        
        # Delete the entire skill directory
        shutil.rmtree(skill_dir)
        
        log.info(f"Deleted skill: {skill_name}")
        
        return {
            "success": True,
            "message": f"Skill '{skill_name}' deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deleting skill {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
