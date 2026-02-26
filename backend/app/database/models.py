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
    headers = Column(Text, nullable=True)  # JSON string for custom headers (e.g. Authorization)
    command = Column(String, nullable=True)  # for stdio
    args = Column(String, nullable=True)  # JSON string array
    error = Column(String, nullable=True)
    uid = Column(Integer, ForeignKey('users.uid'), nullable=False, index=True)  # Associate with user
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="mcp_servers")


class User(Base):
    __tablename__ = "users"
    
    uid = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)  # hashed password
    
    # User-specific LLM configuration (encrypted API key)
    llm_api_key_encrypted = Column(Text, nullable=True)   # Fernet-encrypted API key
    llm_base_url = Column(String, nullable=True)           # Custom OpenAI-compatible base URL
    llm_model_name = Column(String, nullable=True)         # Custom model name (e.g. gpt-4o, claude-3.5-sonnet)
    
    # Advanced / context management settings (per-user overrides, NULL = use system default)
    context_compaction_enabled = Column(String, nullable=True)   # "true" / "false"
    context_keep_recent = Column(Integer, nullable=True)         # e.g. 10
    context_min_messages = Column(Integer, nullable=True)        # e.g. 15
    default_thinking_level = Column(String, nullable=True)       # high/medium/low/off
    agent_max_turns = Column(Integer, nullable=True)             # e.g. 50
    model_fallbacks = Column(String, nullable=True)              # comma-separated model names
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
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
    title = Column(String, nullable=True)  # Session title (synced from frontend)
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

# Migrate: add missing columns to existing tables (SQLite doesn't auto-add columns)
def _migrate_add_column(engine, table_name: str, column_name: str, column_type: str, default: str = "NULL"):
    """Add a column to an existing table if it doesn't exist (SQLite migration helper)."""
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    if column_name not in columns:
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default}"))
            conn.commit()
        print(f"[Database] Migrated: added column '{column_name}' to table '{table_name}'")

try:
    _migrate_add_column(engine, "mcp_servers", "headers", "TEXT", "NULL")
    _migrate_add_column(engine, "chat_sessions", "title", "VARCHAR", "NULL")
    # User LLM configuration columns
    _migrate_add_column(engine, "users", "llm_api_key_encrypted", "TEXT", "NULL")
    _migrate_add_column(engine, "users", "llm_base_url", "VARCHAR", "NULL")
    _migrate_add_column(engine, "users", "llm_model_name", "VARCHAR", "NULL")
    # Advanced / context management columns
    _migrate_add_column(engine, "users", "context_compaction_enabled", "VARCHAR", "NULL")
    _migrate_add_column(engine, "users", "context_keep_recent", "INTEGER", "NULL")
    _migrate_add_column(engine, "users", "context_min_messages", "INTEGER", "NULL")
    _migrate_add_column(engine, "users", "default_thinking_level", "VARCHAR", "NULL")
    _migrate_add_column(engine, "users", "agent_max_turns", "INTEGER", "NULL")
    _migrate_add_column(engine, "users", "model_fallbacks", "VARCHAR", "NULL")
except Exception as e:
    print(f"[Database] Migration check (non-critical): {e}")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
