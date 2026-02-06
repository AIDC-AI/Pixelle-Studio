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

from sqlalchemy import Column, String, DateTime, ForeignKey, create_engine, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from pathlib import Path
import os
import uuid

Base = declarative_base()

class MCPServer(Base):
    __tablename__ = "mcp_servers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False, index=True)
    transport = Column(String, nullable=False)  # 'streamable-http' | 'sse' | 'stdio'
    url = Column(String, nullable=True)  # for streamable-http/SSE
    command = Column(String, nullable=True)  # for stdio
    args = Column(String, nullable=True)  # JSON string array
    error = Column(String, nullable=True)
    uid = Column(Integer, ForeignKey('users.uid'), nullable=False, index=True)  # 关联用户
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="mcp_servers")


class User(Base):
    __tablename__ = "users"
    
    uid = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)  # hashed password
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    mcp_servers = relationship("MCPServer", back_populates="user", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Chat Persistence (Cursor-aligned session/turn/step trace)
# ---------------------------------------------------------------------------

class ChatSession(Base):
    """
    A long-lived conversation session. One session contains multiple turns.
    """
    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    uid = Column(Integer, nullable=True, index=True)  # User ID for multi-tenancy
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    turns = relationship("ChatTurn", back_populates="session", cascade="all, delete-orphan")


class ChatTurn(Base):
    """
    One user request -> agent multi-step loop -> final assistant response.
    """
    __tablename__ = "chat_turns"

    chat_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.session_id"), nullable=False, index=True)

    user_message = Column(Text, nullable=False)
    assistant_message = Column(Text, nullable=True)

    # "pending" | "running" | "success" | "error"
    status = Column(String, nullable=False, default="pending")
    error = Column(Text, nullable=True)

    # JSON strings (kept simple for sqlite, no JSON column dependency)
    file_urls_json = Column(Text, nullable=True)
    file_names_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = relationship("ChatSession", back_populates="turns")
    steps = relationship("ChatStep", back_populates="turn", cascade="all, delete-orphan")


class ChatStep(Base):
    """
    Trace events within a turn (Cursor-like): status/code/execution_result/skill_loaded/response.
    Append-only by (chat_id, step_index).
    """
    __tablename__ = "chat_steps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String, ForeignKey("chat_turns.chat_id"), nullable=False, index=True)

    step_index = Column(Integer, nullable=False)
    step_type = Column(String, nullable=False)  # e.g. "status" | "code" | "execution_result" | "response"

    content = Column(Text, nullable=True)
    data_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    turn = relationship("ChatTurn", back_populates="steps")


# Database setup
# Support DATABASE_URL from environment variable, default to ./app.db
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./app.db")

# For SQLite, ensure the database file's parent directory exists
if DATABASE_URL.startswith("sqlite:///"):
    # Extract path from sqlite:/// URL
    db_path_str = DATABASE_URL.replace("sqlite:///", "")
    # Handle both relative and absolute paths
    db_path = Path(db_path_str)
    
    # Ensure parent directory exists
    db_dir = db_path.parent
    if db_dir and str(db_dir) != ".":
        db_dir.mkdir(parents=True, exist_ok=True)
    
    # If the path is a directory (from Docker mount failure), remove it and create file
    if db_path.exists() and db_path.is_dir():
        import shutil
        shutil.rmtree(db_path)
    
    # Touch the file to ensure it exists (SQLite can create it, but we pre-create to avoid mount issues)
    if not db_path.exists():
        db_path.touch()
        print(f"[Database] Created new SQLite database file: {db_path.absolute()}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)
print(f"[Database] Initialized database at: {DATABASE_URL}")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
