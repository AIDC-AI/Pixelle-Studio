from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# MCPServer Schemas
class MCPServerBase(BaseModel):
    name: str
    transport: str  # 'streamable-http' | 'sse' | 'stdio'
    url: Optional[str] = None
    command: Optional[str] = None
    args: Optional[str] = None  # JSON string
    error: Optional[str] = None


class MCPServerCreate(MCPServerBase):
    pass  # uid will be set from current_user in the route


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    transport: Optional[str] = None
    url: Optional[str] = None
    command: Optional[str] = None
    args: Optional[str] = None
    error: Optional[str] = None


class MCPServerResponse(MCPServerBase):
    id: str
    uid: str  # 用户 ID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    uid: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class LoginResponse(BaseModel):
    message: str
    user: UserResponse
    token: Token
