from sqlalchemy import Column, String, DateTime, ForeignKey, create_engine, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
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
    uid = Column(String, ForeignKey('users.uid'), nullable=False, index=True)  # 关联用户
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="mcp_servers")


class User(Base):
    __tablename__ = "users"
    
    uid = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
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
DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
