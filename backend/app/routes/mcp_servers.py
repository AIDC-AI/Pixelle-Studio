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

router = APIRouter(prefix="/api/mcp-servers", tags=["MCP Servers"])


class ConnectionStatus(BaseModel):
    server_id: str
    server_name: str
    status: str  # 'connected', 'disconnected', 'error'
    message: str
    response_time: float  # 响应时间（毫秒）
    tools: List[dict] = []  # 添加 tools 字段


@router.get("", response_model=List[MCPServerResponse])
def get_all_servers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all MCP servers for current user (requires authentication)"""
    servers = db.query(MCPServer).filter(
        MCPServer.uid == current_user.uid
    ).order_by(MCPServer.created_at.desc()).all()
    return servers


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
    
    server = db.query(MCPServer).filter(
        MCPServer.id == server_id,
        MCPServer.uid == current_user.uid
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    start_time = time.time()
    
    try:
        # 映射 transport 类型
        transport_mapping = {
            'streamable-http': 'http',
            'sse': 'sse',
            'stdio': 'stdio'
        }
        
        server_type = transport_mapping.get(server.transport, server.transport)
        
        # 根据不同类型构建不同的 config
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
        
        # 构建 MCP 服务器配置
        mcp_server = {
            "id": server.id,
            "name": server.name,
            "type": server_type,
            "config": config_data,
            "enabled": True,
            "headers": None
        }
        
        config = AggregatorConfig(servers=[mcp_server])
        
        # 尝试连接并获取工具列表（带超时）
        aggregator = MCPAggregator()
        
        # 设置 5 秒超时
        try:
            tools = await asyncio.wait_for(aggregator.fetch_tools(config), timeout=5.0)
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            return ConnectionStatus(
                server_id=server.id,
                server_name=server.name,
                status="connected",
                message=f"Successfully connected. Found {len(tools)} tools.",
                response_time=round(response_time, 2),
                tools=tools  # 返回工具列表
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
