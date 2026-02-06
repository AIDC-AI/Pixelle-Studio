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

class MCPServerWithStatus(BaseModel):
    # 基本信息
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
    
    # 状态信息
    status: str  # 'connected', 'disconnected', 'error', 'checking'
    message: str
    response_time: float
    tools: List[dict] = []


class ConnectionStatus(BaseModel):
    server_id: str
    server_name: str
    status: str  # 'connected', 'disconnected', 'error'
    message: str
    response_time: float  # 响应时间（毫秒）
    tools: List[dict] = []  # 添加 tools 字段


async def _check_single_server_status(server: MCPServer) -> dict:
    """检查单个服务器的状态和工具"""
    import time
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
            return {
                "status": "error",
                "message": f"Unsupported transport type: {server.transport}",
                "response_time": 0,
                "tools": []
            }
        
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
        aggregator = MCPAggregator()
        
        # 设置 3 秒超时（列表页面需要快速响应）
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
    check_status: bool = True  # 查询参数：是否检查状态
):
    """Get all MCP servers for current user with status and tools"""
    servers = db.query(MCPServer).filter(
        MCPServer.uid == current_user.uid
    ).order_by(MCPServer.created_at.desc()).all()
    
    if not check_status:
        # 如果不需要检查状态，只返回基本信息
        return [
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
                tools=[]
            )
            for s in servers
        ]
    print(f"123123123")
    # 并发检查所有服务器的状态
    status_tasks = [_check_single_server_status(server) for server in servers]
    status_results = await asyncio.gather(*status_tasks, return_exceptions=True)
    
    # 组合结果
    result = []
    for server, status_data in zip(servers, status_results):
        # 如果检查失败，使用默认值
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
                tools=status_data["tools"]
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
