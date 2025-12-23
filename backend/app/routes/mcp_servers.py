from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database.models import MCPServer, User, get_db
from app.database.schemas import MCPServerCreate, MCPServerUpdate, MCPServerResponse
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/mcp-servers", tags=["MCP Servers"])


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
