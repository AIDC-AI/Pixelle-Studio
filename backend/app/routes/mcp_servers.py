from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database.models import MCPServer, User, get_db
from app.database.schemas import MCPServerCreate, MCPServerUpdate, MCPServerResponse
from app.utils.auth import get_current_user
from app.mcp_aggregator import MCPAggregator, MCPServerConfig as AggregatorConfig
from pydantic import BaseModel
from app.utils.logger import log
import asyncio
import json

router = APIRouter(prefix="/api/mcp-servers", tags=["MCP Servers"])

class MCPServerWithStatus(BaseModel):
    # Basic info
    id: str
    name: str
    transport: str
    url: str | None
    command: str | None
    args: str | None
    error: str | None
    uid: int
    created_at: str
    updated_at: str
    
    # Status info
    status: str  # 'connected', 'disconnected', 'error', 'checking'
    message: str
    response_time: float
    tools: List[dict] = []
    
    # Built-in flag
    is_builtin: bool = False


class ConnectionStatus(BaseModel):
    server_id: str
    server_name: str
    status: str  # 'connected', 'disconnected', 'error'
    message: str
    response_time: float  # Response time (milliseconds)
    tools: List[dict] = []  # Add tools field


async def _check_single_server_status(server: MCPServer) -> dict:
    """Check single server status and tools"""
    import time
    start_time = time.time()
    
    try:
        # Map transport types
        transport_mapping = {
            'streamable-http': 'http',
            'sse': 'sse',
            'stdio': 'stdio'
        }
        
        server_type = transport_mapping.get(server.transport, server.transport)
        
        # Build different configs based on type
        if server_type == 'sse':
            config_data = {"url": server.url}
        elif server_type == 'http':
            config_data = {"endpoint": server.url}
        elif server_type == 'stdio':
            config_data = {
                "command": server.command,
                "args": server.args.split(',') if server.args else []
            }
        else:
            return {
                "status": "error",
                "message": f"Unsupported transport type: {server.transport}",
                "response_time": 0,
                "tools": []
            }
        
        # Parse headers from JSON string
        parsed_headers = None
        if hasattr(server, 'headers') and server.headers:
            try:
                parsed_headers = json.loads(server.headers)
            except (json.JSONDecodeError, TypeError):
                parsed_headers = None
        
        # Build MCP server config
        mcp_server = {
            "id": server.id,
            "name": server.name,
            "type": server_type,
            "config": config_data,
            "enabled": True,
            "headers": parsed_headers
        }
        
        config = AggregatorConfig(servers=[mcp_server])
        aggregator = MCPAggregator()
        
        # Set 3 second timeout (list page needs fast response)
        try:
            tools = await asyncio.wait_for(aggregator.fetch_tools(config), timeout=3.0)
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "connected",
                "message": f"Found {len(tools)} tools",
                "response_time": round(response_time, 2),
                "tools": tools
            }
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return {
                "status": "error",
                "message": "Connection timeout (3s)",
                "response_time": round(response_time, 2),
                "tools": []
            }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            "status": "disconnected",
            "message": f"Connection failed: {str(e)}",
            "response_time": round(response_time, 2),
            "tools": []
        }


async def _check_builtin_server_status(server_config: dict) -> dict:
    """Check status of a built-in default MCP server."""
    import time
    start_time = time.time()
    
    try:
        server_type = server_config.get("type", "http")
        url = server_config["url"]
        
        # Build config for aggregator
        if server_type == 'sse':
            config_data = {"url": url}
        elif server_type == 'http':
            config_data = {"endpoint": url}
        else:
            config_data = {"url": url}
        
        # Parse headers from server config (built-in servers may have headers too)
        parsed_headers = server_config.get("headers", None)
        
        mcp_server = {
            "id": f"builtin_{server_config['name']}",
            "name": server_config["name"],
            "type": server_type,
            "config": config_data,
            "enabled": True,
            "headers": parsed_headers
        }
        
        config = AggregatorConfig(servers=[mcp_server])
        aggregator = MCPAggregator()
        
        try:
            tools = await asyncio.wait_for(aggregator.fetch_tools(config), timeout=3.0)
            response_time = (time.time() - start_time) * 1000
            return {
                "status": "connected",
                "message": f"Found {len(tools)} tools",
                "response_time": round(response_time, 2),
                "tools": tools
            }
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return {
                "status": "error",
                "message": "Connection timeout (3s)",
                "response_time": round(response_time, 2),
                "tools": []
            }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            "status": "disconnected",
            "message": f"Connection failed: {str(e)}",
            "response_time": round(response_time, 2),
            "tools": []
        }


@router.get("", response_model=List[MCPServerWithStatus])
async def get_all_servers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    check_status: bool = True  # Query parameter: whether to check status
):
    """Get all MCP servers for current user with status and tools.
    
    Includes both:
    - Built-in default servers (from mcp_client.DEFAULT_MCP_SERVERS)
    - User-configured servers (from database)
    """
    from app.mcp_client import DEFAULT_MCP_SERVERS
    from datetime import datetime
    
    servers = db.query(MCPServer).filter(
        MCPServer.uid == current_user.uid
    ).order_by(MCPServer.created_at.desc()).all()
    
    # Collect user-configured server URLs to avoid duplicates
    user_server_urls = {s.url for s in servers if s.url}
    
    if not check_status:
        # Return basic info without status checks
        result = []
        
        # Add built-in servers first (skip if user already configured same URL)
        for ds in DEFAULT_MCP_SERVERS:
            if ds["url"] not in user_server_urls:
                result.append(
                    MCPServerWithStatus(
                        id=f"builtin_{ds['name']}",
                        name=ds.get("description", ds["name"]),
                        transport="streamable-http",
                        url=ds["url"],
                        command=None,
                        args=None,
                        error=None,
                        uid=current_user.uid,
                        created_at=datetime.utcnow().isoformat(),
                        updated_at=datetime.utcnow().isoformat(),
                        status="unknown",
                        message="Status check disabled",
                        response_time=0,
                        tools=[],
                        is_builtin=True
                    )
                )
        
        # Add user servers
        for s in servers:
            result.append(
                MCPServerWithStatus(
                    id=s.id,
                    name=s.name,
                    transport=s.transport,
                    url=s.url,
                    command=s.command,
                    args=s.args,
                    error=s.error,
                    uid=s.uid,
                    created_at=s.created_at.isoformat(),
                    updated_at=s.updated_at.isoformat(),
                    status="unknown",
                    message="Status check disabled",
                    response_time=0,
                    tools=[],
                    is_builtin=False
                )
            )
        return result

    # === With status check ===
    
    # 1. Check built-in servers (skip if user already configured same URL)
    builtin_to_check = [ds for ds in DEFAULT_MCP_SERVERS if ds["url"] not in user_server_urls]
    
    # 2. Build all status check tasks concurrently
    builtin_tasks = [_check_builtin_server_status(ds) for ds in builtin_to_check]
    user_tasks = [_check_single_server_status(server) for server in servers]
    
    all_results = await asyncio.gather(*(builtin_tasks + user_tasks), return_exceptions=True)
    
    builtin_results = all_results[:len(builtin_tasks)]
    user_results = all_results[len(builtin_tasks):]
    
    # 3. Combine results
    result = []
    
    # Built-in servers first
    for ds, status_data in zip(builtin_to_check, builtin_results):
        if isinstance(status_data, Exception):
            status_data = {
                "status": "error",
                "message": str(status_data),
                "response_time": 0,
                "tools": []
            }
        
        result.append(
            MCPServerWithStatus(
                id=f"builtin_{ds['name']}",
                name=ds.get("description", ds["name"]),
                transport="streamable-http",
                url=ds["url"],
                command=None,
                args=None,
                error=None,
                uid=current_user.uid,
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat(),
                status=status_data["status"],
                message=status_data["message"],
                response_time=status_data["response_time"],
                tools=status_data["tools"],
                is_builtin=True
            )
        )
    
    # User servers
    for server, status_data in zip(servers, user_results):
        if isinstance(status_data, Exception):
            status_data = {
                "status": "error",
                "message": str(status_data),
                "response_time": 0,
                "tools": []
            }
        
        result.append(
            MCPServerWithStatus(
                id=server.id,
                name=server.name,
                transport=server.transport,
                url=server.url,
                command=server.command,
                args=server.args,
                error=server.error,
                uid=server.uid,
                created_at=server.created_at.isoformat(),
                updated_at=server.updated_at.isoformat(),
                status=status_data["status"],
                message=status_data["message"],
                response_time=status_data["response_time"],
                tools=status_data["tools"],
                is_builtin=False
            )
        )
    
    return result


@router.get("/{server_id}", response_model=MCPServerResponse)
def get_server(
    server_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific MCP server (requires authentication and ownership)"""
    server = db.query(MCPServer).filter(
        MCPServer.id == server_id,
        MCPServer.uid == current_user.uid
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.get("/{server_id}/status", response_model=ConnectionStatus)
async def check_server_status(
    server_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check connection status of a specific MCP server and return tools"""
    import time
    
    # Handle built-in servers
    if server_id.startswith("builtin_"):
        from app.mcp_client import DEFAULT_MCP_SERVERS
        builtin_name = server_id[len("builtin_"):]
        builtin_config = next((s for s in DEFAULT_MCP_SERVERS if s["name"] == builtin_name), None)
        if builtin_config:
            status_data = await _check_builtin_server_status(builtin_config)
            return ConnectionStatus(
                server_id=server_id,
                server_name=builtin_config.get("description", builtin_config["name"]),
                status=status_data["status"],
                message=status_data["message"],
                response_time=status_data["response_time"],
                tools=status_data["tools"]
            )
        raise HTTPException(status_code=404, detail="Built-in server not found")
    
    server = db.query(MCPServer).filter(
        MCPServer.id == server_id,
        MCPServer.uid == current_user.uid
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    start_time = time.time()
    
    try:
        # Map transport types
        transport_mapping = {
            'streamable-http': 'http',
            'sse': 'sse',
            'stdio': 'stdio'
        }
        
        server_type = transport_mapping.get(server.transport, server.transport)
        
        # Build different configs based on type
        if server_type == 'sse':
            config_data = {"url": server.url}
        elif server_type == 'http':
            config_data = {"endpoint": server.url}
        elif server_type == 'stdio':
            config_data = {
                "command": server.command,
                "args": server.args.split(',') if server.args else []
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported transport type: {server.transport}")
        
        # Parse headers from JSON string
        parsed_headers = None
        if hasattr(server, 'headers') and server.headers:
            try:
                parsed_headers = json.loads(server.headers)
            except (json.JSONDecodeError, TypeError):
                parsed_headers = None
        
        # Build MCP server config
        mcp_server = {
            "id": server.id,
            "name": server.name,
            "type": server_type,
            "config": config_data,
            "enabled": True,
            "headers": parsed_headers
        }
        
        config = AggregatorConfig(servers=[mcp_server])
        
        # Try to connect and fetch tool list (with timeout)
        aggregator = MCPAggregator()
        
        # Set 5 second timeout
        try:
            tools = await asyncio.wait_for(aggregator.fetch_tools(config), timeout=5.0)
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            return ConnectionStatus(
                server_id=server.id,
                server_name=server.name,
                status="connected",
                message=f"Successfully connected. Found {len(tools)} tools.",
                response_time=round(response_time, 2),
                tools=tools  # Return tool list
            )
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return ConnectionStatus(
                server_id=server.id,
                server_name=server.name,
                status="error",
                message="Connection timeout (5s)",
                response_time=round(response_time, 2),
                tools=[]
            )
            
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return ConnectionStatus(
            server_id=server.id,
            server_name=server.name,
            status="disconnected",
            message=f"Connection failed: {str(e)}",
            response_time=round(response_time, 2),
            tools=[]
        )


@router.post("", response_model=MCPServerResponse, status_code=201)
def create_server(
    server: MCPServerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new MCP server (requires authentication)"""
    # Check if server with same name exists for this user
    existing = db.query(MCPServer).filter(
        MCPServer.name == server.name,
        MCPServer.uid == current_user.uid
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Server with this name already exists")
    
    # Validate transport type
    valid_transports = ['streamable-http', 'sse', 'stdio']
    if server.transport not in valid_transports:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid transport. Must be one of: {', '.join(valid_transports)}"
        )
    
    # Create server with current user's uid
    db_server = MCPServer(**server.model_dump(), uid=current_user.uid)
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    return db_server


@router.put("/{server_id}", response_model=MCPServerResponse)
def update_server(
    server_id: str,
    server: MCPServerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an MCP server (requires authentication and ownership)"""
    db_server = db.query(MCPServer).filter(
        MCPServer.id == server_id,
        MCPServer.uid == current_user.uid
    ).first()
    if not db_server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Check name uniqueness if updating name (within user's servers)
    if server.name and server.name != db_server.name:
        existing = db.query(MCPServer).filter(
            MCPServer.name == server.name,
            MCPServer.uid == current_user.uid
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Server with this name already exists")
    
    # Validate transport type if updating
    if server.transport:
        valid_transports = ['streamable-http', 'sse', 'stdio']
        if server.transport not in valid_transports:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transport. Must be one of: {', '.join(valid_transports)}"
            )
    
    # Update fields
    update_data = server.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_server, field, value)
    
    db.commit()
    db.refresh(db_server)
    return db_server


@router.delete("/{server_id}")
def delete_server(
    server_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an MCP server (requires authentication and ownership)"""
    db_server = db.query(MCPServer).filter(
        MCPServer.id == server_id,
        MCPServer.uid == current_user.uid
    ).first()
    if not db_server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    db.delete(db_server)
    db.commit()
    return {"message": "Server deleted successfully"}
