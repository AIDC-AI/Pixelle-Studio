# Copyright (C) 2026 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Pixelle-Studio Backend - Simplified with Single Agent Architecture.

This is a chat-based interface where a single agent handles all user requests,
using skill guidance when appropriate.
"""

from app.utils.prompt import get_full_message
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import json
import shutil
from pathlib import Path
from datetime import datetime

# Import the simplified agent
from app.agent import SkillAgent
# Import modules
from app.llm_adapter import generate_workflow_script
from app.execution.runner import run_script
from app.mcp_aggregator import MCPAggregator, MCPServerConfig
# from app.tool_search.selector import select_tools
# from app.tool_search.search_agent import SearchAgent

# Import skills loader for API endpoints
from app.skills.loader import get_skill_loader

# Import logger
from app.utils.logger import log

# Import network utilities
from app.utils.network import LOCAL_IP

# Import CRUD routes
from app.routes import mcp_servers, users, sessions, subagents

# DB models (sqlite persistence)
from app.database.models import SessionLocal, ChatSession, ChatTurn, ChatStep

app = FastAPI(title="Pixelle-Studio API", version="2.0.0")

# Include routers
app.include_router(mcp_servers.router)
app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(subagents.router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Static Files Service - Provide HTTP access to generated files for frontend
# ============================================================================
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files directory
# URL: http://localhost:8001/files/1/2026-02-04/example.pdf
# Maps to: backend/scripts/1/2026-02-04/example.pdf
app.mount(
    "/files",
    StaticFiles(directory=str(SCRIPTS_DIR)),
    name="files"
)
log.info(f"Static files service mounted at /files -> {SCRIPTS_DIR}")

# Storage directory for uploaded files
# STORAGE_DIR is now dynamic based on user_id, see upload_file
# STORAGE_DIR = Path(__file__).parent.parent / "scripts"
# STORAGE_DIR.mkdir(parents=True, exist_ok=True)


log.info(f"Local IP address: {LOCAL_IP} (EXTERNAL_IP env: {os.environ.get('EXTERNAL_IP', 'not set')})")

# NOTE:
# Previously we used an in-memory `chats` dict keyed by `chat_id` (one user request).
# This caused history loss across turns. We now persist session/turn/step into sqlite
# (see app.database.models). WebSocket still keys by `chat_id` (turn id), but each
# turn belongs to a long-lived `session_id`.

# Initialize skill loader
skill_loader = get_skill_loader()
skills_list = skill_loader.scan_skills()
log.info(f"Loaded {len(skills_list)} skills: {[s.name for s in skills_list]}")


class ChatRequest(BaseModel):
    message: str
    file_urls: Optional[List[str]] = None
    file_names: Optional[List[str]] = None  # Uploaded file names (e.g. 9120.xlsx)
    session_id: Optional[str] = None  # Optional: reuse same session (Cursor-like)
    user_id: Optional[int] = None  # User ID for multi-tenant isolation


class ChatResponse(BaseModel):
    chat_id: str
    session_id: str


class GenerateTitleRequest(BaseModel):
    message: str  # User's first message
    

class GenerateTitleResponse(BaseModel):
    title: str


@app.post("/api/generate-title", response_model=GenerateTitleResponse)
async def generate_title(request: GenerateTitleRequest):
    """Generate a concise title for a conversation based on user's first message."""
    from openai import AsyncOpenAI
    from app.llm_adapter import DEFAULT_MODEL
    
    try:
        client = AsyncOpenAI()
        
        response = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {
                    "role": "system", 
                    "content": """You are a conversation title generation assistant. Based on the user's message, generate a concise conversation title.
                    
                    Rules:
                    1. Title must be between 2-8 words, never exceed 8 words
                    2. Title should summarize the core content of the user's request
                    3. IMPORTANT: Generate the title in the SAME LANGUAGE as the user's message. If the user writes in Chinese, the title must be in Chinese. If the user writes in English, the title must be in English. If the user writes in Japanese, the title must be in Japanese. And so on for any other language.
                    4. Do not use punctuation
                    5. Only return the title text, do not reply with anything else

                    Examples:
                    - "帮我分析这个Excel表格的销售数据" -> "Excel销售数据分析"
                    - "Generate a PPT about artificial intelligence" -> "AI Presentation"
                    - "帮我写一个Python排序代码" -> "Python排序代码"
                    - "What's the weather today" -> "Weather Query"
                    - "帮我处理这个文件" -> "文件处理"
                    - "このファイルを分析してください" -> "ファイル分析"
                    """
                },
                {"role": "user", "content": request.message}
            ],
            temperature=0.3
        )
        
        title = response.choices[0].message.content.strip()
        # Remove possible quotes
        title = title.strip('"\'')
        
        # If title is too long, truncate to 50 chars
        if len(title) > 50:
            title = title[:50]
        
        # Log token usage
        usage = response.usage
        if usage:
            log.info(f"[TokenUsage][generate_title] model={DEFAULT_MODEL} prompt_tokens={usage.prompt_tokens} completion_tokens={usage.completion_tokens} total_tokens={usage.total_tokens}")
            
        log.info(f"Generated title: {title} for message: {request.message[:50]}...")
        return {"title": title}
        
    except Exception as e:
        log.error(f"Failed to generate title: {e}")
        # Fallback to simple truncation logic on failure
        fallback_title = request.message[:15] + "..." if len(request.message) > 15 else request.message
        return {"title": fallback_title}


@app.post("/api/chat", response_model=ChatResponse)
async def create_chat(request: ChatRequest):
    """Create a new chat session."""
    db = SessionLocal()
    try:
        # 1) Resolve session_id (create if missing)
        session_id = request.session_id
        if session_id:
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if not session:
                session = ChatSession(session_id=session_id, uid=request.user_id)
                db.add(session)
                db.commit()
            elif request.user_id and not session.uid:
                # Update existing session with uid if missing
                session.uid = request.user_id
                db.commit()
        else:
            session = ChatSession(uid=request.user_id)
            db.add(session)
            db.commit()
            db.refresh(session)
            session_id = session.session_id

        # 2) Create a new turn (chat_id) under this session
        chat_id = str(uuid.uuid4())[:8]
        turn = ChatTurn(
            chat_id=chat_id,
            session_id=session_id,
            user_message=request.message,
            status="pending",
            file_urls_json=json.dumps(request.file_urls or [], ensure_ascii=False),
            file_names_json=json.dumps(request.file_names or [], ensure_ascii=False),
        )
        db.add(turn)
        db.commit()

        log.info(f"Created turn {chat_id} (session {session_id[:8]}, user {request.user_id}): {request.message[:50]}...")
        return {"chat_id": chat_id, "session_id": session_id}
    finally:
        db.close()


@app.websocket("/ws/chat/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    """WebSocket endpoint for chat interaction."""
    await websocket.accept()
    log.info(f"WebSocket connected: {chat_id}")
    
    log.debug("Websocket accepted")

    try:
        # Load pending turn from DB and process
        db = SessionLocal()
        try:
            turn = db.query(ChatTurn).filter(ChatTurn.chat_id == chat_id).first()
            if not turn:
                await websocket.close(code=4004, reason=f"Chat not found: {chat_id}")
                return

            # Only process if pending/running (idempotent-ish)
            if turn.status in ("pending", "running"):
                turn.status = "running"
                turn.updated_at = datetime.utcnow()
                db.commit()

            user_message = turn.user_message
            file_urls = json.loads(turn.file_urls_json) if turn.file_urls_json else []
            file_names = json.loads(turn.file_names_json) if turn.file_names_json else []
            session_id = turn.session_id
            
            # Retrieve user_id from session
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            user_id = session.uid if session else None
            
        finally:
            db.close()

        await process_with_agent(websocket, chat_id, session_id, user_message, file_urls, file_names, user_id)
    
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
    session_id: str,
    user_message: str,
    file_urls: List[str],
    file_names: List[str] = None,
    user_id: int = None
):
    """
    Process a user message using the single agent.
    
    The agent handles everything:
    - Deciding whether to answer directly or execute code
    - Calling MCP tools for external services
    - Loading skills when needed
    - Executing code and evaluating results
    - Continuing until task is complete
    """
    try:
        # Build history from persisted completed turns in the same session
        db = SessionLocal()
        try:
            prior_turns = (
                db.query(ChatTurn)
                .filter(ChatTurn.session_id == session_id)
                .filter(ChatTurn.chat_id != chat_id)
                .order_by(ChatTurn.created_at.asc())
                .all()
            )
            history_messages = []
            for t in prior_turns:
                if t.user_message:
                    # Reconstruct the full message with file context (if any)
                    prior_file_urls = json.loads(t.file_urls_json) if t.file_urls_json else []
                    prior_file_names = json.loads(t.file_names_json) if t.file_names_json else []
                    full_prior_message = get_full_message(t.user_message, prior_file_urls, prior_file_names)
                    history_messages.append({"role": "user", "content": full_prior_message})

                assistant_text = t.assistant_message
                if not assistant_text:
                    # Try reconstruct from steps (best-effort)
                    last_resp = (
                        db.query(ChatStep)
                        .filter(ChatStep.chat_id == t.chat_id)
                        .filter(ChatStep.step_type == "response")
                        .order_by(ChatStep.step_index.desc())
                        .first()
                    )
                    if last_resp and last_resp.content:
                        assistant_text = last_resp.content

                # Extract generated files from execution_result steps
                generated_files = []
                exec_results = (
                    db.query(ChatStep)
                    .filter(ChatStep.chat_id == t.chat_id)
                    .filter(ChatStep.step_type == "execution_result")
                    .all()
                )
                for step in exec_results:
                    if step.data_json:
                        try:
                            step_data = json.loads(step.data_json)
                            output_files = step_data.get("output_files", [])
                            for f in output_files:
                                if isinstance(f, dict) and f.get("file_name"):
                                    generated_files.append(f["file_name"])
                                elif isinstance(f, str):
                                    generated_files.append(f)
                        except json.JSONDecodeError:
                            pass

                # Append generated files info to assistant message
                if assistant_text:
                    if generated_files:
                        assistant_text += "\n\n## Generated Files:\n"
                        for fname in generated_files:
                            assistant_text += f"- {fname}\n"
                    history_messages.append({"role": "assistant", "content": assistant_text})
            
            # Load first enabled MCP server for tool calls
            from app.database.models import MCPServer as DBMCPServer
            mcp_server_url = None
            mcp_server_type = "sse"
            
            mcp_server = db.query(DBMCPServer).first()  # Get first available server
            if mcp_server:
                mcp_server_url = mcp_server.url
                transport_mapping = {
                    'streamable-http': 'http',
                    'sse': 'sse',
                }
                mcp_server_type = transport_mapping.get(mcp_server.transport, 'sse')
                log.info(f"Using MCP server: {mcp_server.name} ({mcp_server_url})")
        finally:
            db.close()

        agent = SkillAgent(
            # max_turns uses config.agent_max_turns by default (env: AGENT_MAX_TURNS)
            history_messages=history_messages,
            mcp_server_url=mcp_server_url,
            mcp_server_type=mcp_server_type,
            user_id=user_id
        )
        
        step_index = 0
        final_response_text: Optional[str] = None
        async for event in agent.run(
            user_message=get_full_message(user_message or "", file_urls or [], file_names or []),
            session_id=chat_id[:8]
        ):
            # Forward all events to the frontend
            await websocket.send_json(event)

            # Persist step trace (Cursor-like)
            step_type = event.get("type", "unknown")
            content = event.get("content")
            
            # ✅ FIX: Skip response_delta early WITHOUT creating a DB session
            # (was creating and immediately closing a DB session for every delta - wasteful)
            if step_type == "response_delta":
                continue
            
            # Capture response text for final message (no DB needed)
            if step_type == "response" and isinstance(content, str) and content.strip():
                final_response_text = content
            
            # Only create DB session for events that need persistence
            try:
                db = SessionLocal()
                data_json = None
                
                # Events with structured data
                if step_type in ("execution_result", "final_result", "tool_call", "tool_result"):
                    data_json = json.dumps(event, ensure_ascii=False)
                    content = None
                
                step = ChatStep(
                    chat_id=chat_id,
                    step_index=step_index,
                    step_type=step_type,
                    content=content if isinstance(content, str) else None,
                    data_json=data_json
                )
                db.add(step)
                db.commit()
                step_index += 1
            except Exception as e:
                log.error(f"[{chat_id[:8]}] Error persisting step: {e}")
            finally:
                try:
                    db.close()
                except Exception:
                    pass
            
            # Log important events
            event_type = event.get("type")
            if event_type == "status":
                log.info(f"[{chat_id[:8]}] Status: {event.get('content', '')[:50]}")
            elif event_type == "code":
                log.info(f"[{chat_id[:8]}] Executing code #{event.get('execution_count', 0)}")
            elif event_type == "execution_result":
                log.info(f"[{chat_id[:8]}] Execution result: {event.get('status')}")
            elif event_type == "tool_call":
                log.info(f"[{chat_id[:8]}] Tool call: {event.get('name')}")
            elif event_type == "tool_result":
                log.info(f"[{chat_id[:8]}] Tool result: {event.get('name')}")
            elif event_type == "response_delta":
                pass  # Don't log deltas (too verbose)
            elif event_type == "response":
                log.info(f"[{chat_id[:8]}] Response: {str(event.get('content', ''))[:50]}...")
            elif event_type == "skill_loaded":
                log.info(f"[{chat_id[:8]}] Skill loaded: {event.get('skill_name')}")
            elif event_type == "final_result":
                log.info(f"[{chat_id[:8]}] Final: {event.get('status')}")

                # Persist final assistant message to the turn
                try:
                    db = SessionLocal()
                    turn = db.query(ChatTurn).filter(ChatTurn.chat_id == chat_id).first()
                    if turn:
                        final_status = event.get("status") or "error"
                        # Normalize to our turn status domain
                        if final_status not in ("success", "error", "incomplete"):
                            final_status = "error"
                        turn.status = final_status
                        # Prefer direct response if present
                        result_obj = event.get("result") or {}
                        if isinstance(result_obj, dict) and "answer" in result_obj:
                            turn.assistant_message = str(result_obj.get("answer"))
                        elif isinstance(result_obj, str):
                            turn.assistant_message = result_obj
                        else:
                            # fallback stringify
                            turn.assistant_message = json.dumps(result_obj, ensure_ascii=False)

                        # If final answer is empty, fallback to best-effort response text captured earlier
                        # Note: final_response_text should already be cleaned by agent.py
                        if (turn.assistant_message is None) or (isinstance(turn.assistant_message, str) and not turn.assistant_message.strip()):
                            if final_response_text:
                                # Double-check: remove any remaining <execute> blocks
                                import re
                                cleaned_fallback = re.sub(
                                    r'<execute\s+lang=["\']python["\']\s*>.*?</execute>',
                                    '', final_response_text, flags=re.DOTALL | re.IGNORECASE
                                )
                                cleaned_fallback = re.sub(r'\n{3,}', '\n\n', cleaned_fallback).strip()
                                turn.assistant_message = cleaned_fallback if cleaned_fallback else final_response_text
                        turn.updated_at = datetime.utcnow()
                        db.commit()
                finally:
                    try:
                        db.close()
                    except Exception:
                        pass
    
    except WebSocketDisconnect:
        log.info(f"Client disconnected during processing: {chat_id}")
    except Exception as e:
        log.error(f"Error processing message for {chat_id}: {e}", exc_info=True)
        try:
            # Send both error and final_result so frontend can close cleanly
            await websocket.send_json({"type": "error", "content": str(e)})
            await websocket.send_json({
                "type": "final_result",
                "status": "error",
                "result": {"error": str(e)},
                "error": str(e)
            })
        except:
            pass

# ============================================================================
# File Upload API
# ============================================================================

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), request: Request = None, user_id: Optional[int] = None):
    """Upload a file and return a URL for access."""
    try:
        # ✅ Use date subdirectory, consistent with write_file and exec
        from datetime import datetime
        script_root = Path(__file__).parent.parent / "scripts"
        target_subdir = str(user_id) if user_id is not None else "default"
        
        # Add date subdirectory
        date_str = datetime.now().strftime("%Y-%m-%d")
        storage_dir = script_root / target_subdir / date_str
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        file_id = str(uuid.uuid4())[:4]
        file_extension = Path(file.filename).suffix if file.filename else ""
        unique_filename = f"{file_id}{file_extension}"
        
        file_path = storage_dir / unique_filename

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        log.info(f"File uploaded: {file.filename} -> {unique_filename} (scope: {target_subdir}/{date_str})")
        
        port = request.url.port if request and request.url.port else 8001
        # ✅ URL path includes date subdirectory
        url_path = f"{target_subdir}/{date_str}/{unique_filename}"
        lan_url = f"http://{LOCAL_IP}:{port}/f/{url_path}"

        return {
            "success": True,
            "url": lan_url,
            "file_name": unique_filename,  # Saved filename
            "original_name": file.filename,  # Original filename
            "size": file_path.stat().st_size,
            "scope": f"{target_subdir}/{date_str}"
        }

    except Exception as e:
        log.error(f"File upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/f/{user_id}/{date}/{filename}")
async def get_user_file(user_id: int, date: str, filename: str):
    """Serve uploaded files for a specific user with date subdirectory."""
    script_root = Path(__file__).parent.parent / "scripts"
    file_path = script_root / str(user_id) / date / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


@app.get("/f/{user_id}/{filename}")
async def get_user_file_legacy(user_id: int, filename: str):
    """Serve uploaded files for a specific user (legacy, no date subdirectory)."""
    script_root = Path(__file__).parent.parent / "scripts"
    file_path = script_root / str(user_id) / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)


@app.get("/f/{filename}")
async def get_file(filename: str):
    """Serve uploaded files (legacy/default)."""
    # Default to 'default' directory
    script_root = Path(__file__).parent.parent / "scripts"
    file_path = script_root / "default" / filename

    # Fallback to root scripts dir for backward compatibility
    if not file_path.exists():
        file_path = script_root / filename
        
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

# ============================================================================
# Skills API
# ============================================================================

class CreateSkillRequest(BaseModel):
    name: str
    description: str
    content: str  # Full SKILL.md content

class UpdateSkillRequest(BaseModel):
    new_name: Optional[str] = None  # If provided, rename the skill
    description: str
    content: str  # Updated SKILL.md content

@app.get("/api/skills")
async def get_skills(user_id: Optional[int] = None):
    """Get all available skills metadata (merged view for user)."""
    try:
        # Convert user_id to string for file path
        user_id_str = str(user_id) if user_id is not None else None
        skills = skill_loader.scan_skills(user_id_str)
        return {
            "skills": [s.to_dict() for s in skills],
            "count": len(skills)
        }
    except Exception as e:
        log.error(f"Error getting skills: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills/{skill_name}")
async def get_skill_detail(skill_name: str, user_id: Optional[int] = None):
    """Get full content of a specific skill."""
    try:
        # Convert user_id to string for file path
        user_id_str = str(user_id) if user_id is not None else None
        content = skill_loader.read_skill(skill_name, user_id_str)
        if content is None:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
        
        meta = skill_loader.get_skill_meta(skill_name, user_id_str)
        files = skill_loader.list_skill_files(skill_name, user_id_str)
        
        return {
            "name": skill_name,
            "meta": meta.to_dict() if meta else None,
            "content": content,
            "files": files
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error getting skill detail for {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills")
async def create_skill(request: CreateSkillRequest, user_id: Optional[int] = None):
    """
    Create a new skill.
    If user_id provided, create in skills/<user_id>, else in skills/default.
    """
    try:
        # Determine target directory
        skills_root = Path(__file__).parent.parent / "skills"
        target_subdir = str(user_id) if user_id is not None else "default"
        skillset_dir = skills_root / target_subdir
        skillset_dir.mkdir(parents=True, exist_ok=True)
        
        skill_dir = skillset_dir / request.name
        
        # Check if skill already exists in this scope
        if skill_dir.exists():
            raise HTTPException(status_code=400, detail=f"Skill '{request.name}' already exists in {target_subdir}")
        
        # Create skill directory
        skill_dir.mkdir(parents=True)
        
        # Create SKILL.md file
        skill_md = skill_dir / "SKILL.md"
        # create content
#         skill_content = f"""---
# name: {request.name}
# description: {request.description}
# ---

# {request.content}
# """
        with open(skill_md, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        # Clear loader cache to reflect changes
        skill_loader.clear_cache()
        
        log.info(f"Created skill: {request.name} (scope: {target_subdir})")
        
        return {
            "success": True,
            "name": request.name,
            "path": str(skill_dir.relative_to(skills_root.parent)),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error creating skill {request.name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/skills/{skill_name}")
async def update_skill(skill_name: str, request: UpdateSkillRequest, user_id: Optional[int] = None):
    """
    Update an existing skill.
    Must provide user_id to update user-specific skills.
    """
    try:
        skills_root = Path(__file__).parent.parent / "skills"
        target_subdir = str(user_id) if user_id is not None else "default"
        skillset_dir = skills_root / target_subdir
        
        skill_dir = skillset_dir / skill_name
        
        if not skill_dir.exists() or not skill_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found in {target_subdir}")
        
        # Handle rename if new_name is provided
        if request.new_name and request.new_name != skill_name:
            new_skill_dir = skillset_dir / request.new_name
            
            # Check if new name already exists
            if new_skill_dir.exists():
                raise HTTPException(status_code=400, detail=f"Skill '{request.new_name}' already exists")
            
            # Rename directory
            skill_dir.rename(new_skill_dir)
            skill_dir = new_skill_dir
            log.info(f"Renamed skill from '{skill_name}' to '{request.new_name}' (scope: {target_subdir})")
        
        # Update SKILL.md content
        skill_md = skill_dir / "SKILL.md"
        with open(skill_md, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        skill_loader.clear_cache()
        
        final_name = request.new_name if request.new_name else skill_name
        log.info(f"Updated skill: {final_name} (scope: {target_subdir})")
        
        return {
            "success": True,
            "name": final_name,
            "path": str(skill_dir.relative_to(skills_root.parent)),
            "scope": target_subdir
        }
    
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating skill {skill_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/skills/{skill_name}")
async def delete_skill(skill_name: str, user_id: Optional[int] = None):
    """
    Delete a skill and all its files.
    """
    try:
        skills_root = Path(__file__).parent.parent / "skills"
        target_subdir = str(user_id) if user_id is not None else "default"
        skillset_dir = skills_root / target_subdir
        
        skill_dir = skillset_dir / skill_name
        
        if not skill_dir.exists() or not skill_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found in {target_subdir}")
        
        # Delete the entire skill directory
        shutil.rmtree(skill_dir)
        
        skill_loader.clear_cache()
        
        log.info(f"Deleted skill: {skill_name} (scope: {target_subdir})")
        
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
