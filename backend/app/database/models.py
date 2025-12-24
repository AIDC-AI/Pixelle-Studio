from sqlalchemy import Column, String, DateTime, ForeignKey, create_engine
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
