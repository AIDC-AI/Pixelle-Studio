import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os

# JWT settings
_DEFAULT_JWT_SECRET = "pixelle-jwt-secret-key-for-development-only-2024"
SECRET_KEY = os.environ.get("JWT_SECRET", _DEFAULT_JWT_SECRET)  # 生产环境应该使用环境变量
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 7 

def _truncate_password(password: str) -> bytes:
    """Truncate password to 72 bytes for bcrypt compatibility"""
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Truncate at byte level
        password_bytes = password_bytes[:72]
    return password_bytes

def hash_password(password: str) -> str:
    """Hash a password using bcrypt (has a 72 byte limit)"""
    password_bytes = _truncate_password(password)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash (has a 72 byte limit)"""
    password_bytes = _truncate_password(plain_password)
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
