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

from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# MCPServer Schemas
class MCPServerBase(BaseModel):
    name: str
    transport: str  # 'streamable-http' | 'sse' | 'stdio'
    url: Optional[str] = None
    headers: Optional[str] = None  # JSON string for custom headers (e.g. {"Authorization": "Bearer ..."})
    command: Optional[str] = None
    args: Optional[str] = None  # JSON string
    error: Optional[str] = None


class MCPServerCreate(MCPServerBase):
    pass  # uid will be set from current_user in the route


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    transport: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[str] = None
    command: Optional[str] = None
    args: Optional[str] = None
    error: Optional[str] = None


class MCPServerResponse(MCPServerBase):
    id: str
    uid: int  # User ID
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
    uid: int
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


# ============================================================================
# User LLM Settings Schemas
# ============================================================================

class LLMSettingsUpdate(BaseModel):
    """Request to save user's custom LLM configuration."""
    api_key: Optional[str] = None       # Plaintext API key (encrypted before storage)
    base_url: Optional[str] = None      # Custom OpenAI-compatible base URL
    model_name: Optional[str] = None    # Custom model name
    # Advanced / context management settings
    context_compaction_enabled: Optional[bool] = None
    context_keep_recent: Optional[int] = None
    context_min_messages: Optional[int] = None
    default_thinking_level: Optional[str] = None   # high / medium / low / off
    agent_max_turns: Optional[int] = None
    model_fallbacks: Optional[str] = None           # comma-separated


class LLMSettingsResponse(BaseModel):
    """Response with user's LLM configuration (API key masked for security)."""
    api_key_set: bool = False             # Whether an API key is configured
    api_key_masked: Optional[str] = None  # Masked API key for display (e.g. sk-ab****xyz9)
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    # Advanced settings (with system defaults as fallback)
    context_compaction_enabled: bool = True
    context_keep_recent: int = 10
    context_min_messages: int = 15
    default_thinking_level: str = "medium"
    agent_max_turns: int = 50
    model_fallbacks: Optional[str] = None


class LLMTestRequest(BaseModel):
    """Request to test LLM connectivity."""
    api_key: str
    base_url: Optional[str] = None
    model_name: Optional[str] = None


class LLMTestResponse(BaseModel):
    """Response from LLM connectivity test."""
    success: bool
    message: str
    model_used: Optional[str] = None
    latency_ms: Optional[int] = None
