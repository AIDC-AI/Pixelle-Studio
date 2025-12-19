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
# from app.tool_search.selector import select_tools
# from app.tool_search.search_agent import SearchAgent

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


async def process_and_execute(websocket: WebSocket, chat_id: str, user_message: str):
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
        #TODO: Tool selector rely on embedding model,close it for now,open it when the framework is ready
        #selected_tools = await select_tools(user_message, all_tools)
        selected_tools = all_tools
        chats[chat_id]["tools"] = selected_tools

        # Check if workflow is needed
        workflow_check = await check_if_workflow_needed(user_message, selected_tools, file_urls)
        log.info(f"Workflow check result: {workflow_check}")

        if not workflow_check.get("needs_workflow", True):
            # === Direct answer path ===
            log.info("Direct answer mode - no workflow needed")
            await websocket.send_json({"type": "status", "content": f"💡 Reasoning: {workflow_check.get('reasoning', 'Simple query')}"})

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
        await websocket.send_json({"type": "status", "content": f"🔧 {workflow_check.get('reasoning', 'Complex workflow detected - generating script...')}"})

        # === Stage 1: Execute with self-evaluation ===
        execution_context = await orchestrator.execute_with_self_evaluation(websocket=websocket,
                                                                            chat_id=chat_id,
                                                                            user_message=user_message,
                                                                            selected_tools=selected_tools,
                                                                            file_urls=file_urls)

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
        #TODO: SearchAgent rely on embedding model,close it for now,open it when the framework is ready
        #await SearchAgent.instance.embedding_tools(config,tools)
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
