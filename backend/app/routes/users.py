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
from app.database.models import User, get_db
from app.database.schemas import (
    UserCreate, UserUpdate, UserResponse, UserLogin, LoginResponse, Token,
    LLMSettingsUpdate, LLMSettingsResponse, LLMTestRequest, LLMTestResponse
)
from app.utils.security import (
    hash_password, verify_password, create_access_token,
    encrypt_value, decrypt_value, mask_api_key
)
from app.utils.auth import get_current_user
from app.config import get_config
from datetime import timedelta
import os
import re
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


def validate_password(password: str):
    """Validate password strength"""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")


@router.get("", response_model=List[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all users (requires authentication)"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info"""
    return current_user


@router.get("/{uid}", response_model=UserResponse)
def get_user(
    uid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific user (requires authentication)"""
    user = db.query(User).filter(User.uid == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("", response_model=UserResponse, status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user (public endpoint)"""
    # Validate password
    validate_password(user.password)
    
    # Check if username exists
    existing_username = db.query(User).filter(User.username == user.username).first()
    if existing_username:
        raise HTTPException(status_code=409, detail="User with this username already exists")
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == user.email).first()
    if existing_email:
        raise HTTPException(status_code=409, detail="User with this email already exists")
    
    # Hash password
    hashed_password = hash_password(user.password)
    
    # Create user
    db_user = User(
        username=user.username,
        email=user.email,
        password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.put("/{uid}", response_model=UserResponse)
def update_user(
    uid: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a user (requires authentication, can only update own profile)"""
    # Check if user is updating their own profile
    if current_user.uid != uid:
        raise HTTPException(status_code=403, detail="You can only update your own profile")
    
    db_user = db.query(User).filter(User.uid == uid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check username uniqueness if updating
    if user.username and user.username != db_user.username:
        existing = db.query(User).filter(User.username == user.username).first()
        if existing:
            raise HTTPException(status_code=409, detail="User with this username already exists")
    
    # Check email uniqueness if updating
    if user.email and user.email != db_user.email:
        existing = db.query(User).filter(User.email == user.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="User with this email already exists")
    
    # Validate and hash password if updating
    if user.password:
        validate_password(user.password)
        user.password = hash_password(user.password)
    
    # Update fields
    update_data = user.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{uid}")
def delete_user(
    uid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a user (requires authentication, can only delete own account)"""
    # Check if user is deleting their own account
    if current_user.uid != uid:
        raise HTTPException(status_code=403, detail="You can only delete your own account")
    
    db_user = db.query(User).filter(User.uid == uid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}


# ============================================================================
# User LLM Settings Endpoints
# ============================================================================

def _build_llm_settings_response(db_user: User) -> LLMSettingsResponse:
    """Build a LLMSettingsResponse from a User model, applying system defaults for unset fields."""
    cfg = get_config()
    
    api_key_set = bool(db_user.llm_api_key_encrypted)
    api_key_masked = None
    if api_key_set:
        try:
            plain_key = decrypt_value(db_user.llm_api_key_encrypted)
            api_key_masked = mask_api_key(plain_key)
        except Exception:
            api_key_masked = "****"

    # Resolve advanced settings with system defaults from config / .env
    compaction_enabled = cfg.context_compaction_enabled
    if db_user.context_compaction_enabled is not None:
        compaction_enabled = db_user.context_compaction_enabled.lower() == "true"

    return LLMSettingsResponse(
        api_key_set=api_key_set,
        api_key_masked=api_key_masked,
        base_url=db_user.llm_base_url,
        model_name=db_user.llm_model_name,
        context_compaction_enabled=compaction_enabled,
        context_keep_recent=db_user.context_keep_recent if db_user.context_keep_recent is not None else cfg.context_keep_recent,
        context_min_messages=db_user.context_min_messages if db_user.context_min_messages is not None else cfg.context_min_messages_before_compact,
        default_thinking_level=db_user.default_thinking_level if db_user.default_thinking_level else cfg.default_thinking_level,
        agent_max_turns=db_user.agent_max_turns if db_user.agent_max_turns is not None else cfg.agent_max_turns,
        model_fallbacks=db_user.model_fallbacks,
    )


@router.get("/me/llm-settings", response_model=LLMSettingsResponse)
def get_llm_settings(
    current_user: User = Depends(get_current_user)
):
    """Get current user's LLM configuration (API key is masked for security)."""
    return _build_llm_settings_response(current_user)


@router.put("/me/llm-settings", response_model=LLMSettingsResponse)
def update_llm_settings(
    settings: LLMSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update current user's LLM configuration. API key is encrypted before storage."""
    db_user = db.query(User).filter(User.uid == current_user.uid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update API key (encrypt before storage)
    if settings.api_key is not None:
        if settings.api_key.strip():
            db_user.llm_api_key_encrypted = encrypt_value(settings.api_key.strip())
        else:
            # Empty string means clear the API key
            db_user.llm_api_key_encrypted = None
    
    # Update base URL
    if settings.base_url is not None:
        db_user.llm_base_url = settings.base_url.strip() if settings.base_url.strip() else None
    
    # Update model name
    if settings.model_name is not None:
        db_user.llm_model_name = settings.model_name.strip() if settings.model_name.strip() else None

    # Update advanced / context management settings
    if settings.context_compaction_enabled is not None:
        db_user.context_compaction_enabled = str(settings.context_compaction_enabled).lower()

    if settings.context_keep_recent is not None:
        db_user.context_keep_recent = max(1, settings.context_keep_recent)

    if settings.context_min_messages is not None:
        db_user.context_min_messages = max(1, settings.context_min_messages)

    if settings.default_thinking_level is not None:
        level = settings.default_thinking_level.strip().lower()
        if level in ("high", "medium", "low", "off"):
            db_user.default_thinking_level = level

    if settings.agent_max_turns is not None:
        db_user.agent_max_turns = max(1, min(200, settings.agent_max_turns))

    if settings.model_fallbacks is not None:
        db_user.model_fallbacks = settings.model_fallbacks.strip() if settings.model_fallbacks.strip() else None
    
    db.commit()
    db.refresh(db_user)
    
    return _build_llm_settings_response(db_user)


@router.delete("/me/llm-settings")
def delete_llm_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear all LLM settings for the current user."""
    db_user = db.query(User).filter(User.uid == current_user.uid).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.llm_api_key_encrypted = None
    db_user.llm_base_url = None
    db_user.llm_model_name = None
    db_user.context_compaction_enabled = None
    db_user.context_keep_recent = None
    db_user.context_min_messages = None
    db_user.default_thinking_level = None
    db_user.agent_max_turns = None
    db_user.model_fallbacks = None
    
    db.commit()
    
    return {"message": "LLM settings cleared successfully"}


@router.post("/me/llm-settings/test", response_model=LLMTestResponse)
async def test_llm_connection(
    request: LLMTestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Test LLM API connectivity with user-provided credentials.
    Sends a minimal request to verify the API key / base URL / model work.
    """
    from openai import AsyncOpenAI
    import httpx as _httpx

    api_key = request.api_key.strip()
    base_url = request.base_url.strip() if request.base_url else None
    model = request.model_name.strip() if request.model_name else "gpt-4o"

    if not api_key:
        return LLMTestResponse(success=False, message="API Key is required")

    try:
        client_kwargs = {"api_key": api_key, "timeout": 30}
        if base_url:
            client_kwargs["base_url"] = base_url

        # Check proxy settings
        http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        if http_proxy or https_proxy:
            client_kwargs["http_client"] = _httpx.AsyncClient(
                proxies={"http://": http_proxy, "https://": https_proxy or http_proxy}
            )

        client = AsyncOpenAI(**client_kwargs)

        start = time.time()
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        latency_ms = int((time.time() - start) * 1000)

        # Validate we got a response
        if response.choices and response.choices[0].message:
            return LLMTestResponse(
                success=True,
                message="Connection successful!",
                model_used=model,
                latency_ms=latency_ms
            )
        else:
            return LLMTestResponse(success=False, message="Received empty response from API")

    except Exception as e:
        error_msg = str(e)
        # Provide user-friendly error messages
        if "401" in error_msg or "Unauthorized" in error_msg or "invalid_api_key" in error_msg:
            friendly = "Authentication failed. Please check your API Key."
        elif "404" in error_msg:
            friendly = f"Model '{model}' not found. Please check the model name and base URL."
        elif "429" in error_msg:
            friendly = "Rate limit exceeded. The API key is valid but hitting rate limits."
        elif "timeout" in error_msg.lower():
            friendly = "Connection timed out. Please check the Base URL."
        elif "connect" in error_msg.lower():
            friendly = "Connection failed. Please check the Base URL is reachable."
        else:
            friendly = f"Connection failed: {error_msg[:200]}"
        
        logger.warning(f"LLM test failed for user {current_user.uid}: {error_msg[:200]}")
        return LLMTestResponse(success=False, message=friendly)


@router.post("/login", response_model=LoginResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """User login (public endpoint)"""
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.uid)},  # Convert uid to string for JWT
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "message": "Login successful",
        "user": UserResponse.model_validate(user),
        "token": {
            "access_token": access_token,
            "token_type": "bearer"
        }
    }
