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

import bcrypt
import base64
import hashlib
from jose import JWTError, jwt
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from typing import Optional
import os

# JWT settings
_DEFAULT_JWT_SECRET = "pixelle-jwt-secret-key-for-development-only-2024"
SECRET_KEY = os.environ.get("JWT_SECRET", _DEFAULT_JWT_SECRET)  # Production should use environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 

# Encryption key for sensitive data (API keys etc.)
# Derived from JWT_SECRET to avoid requiring a separate env var
_ENCRYPTION_SECRET = os.environ.get("ENCRYPTION_SECRET", SECRET_KEY)
_FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256(_ENCRYPTION_SECRET.encode()).digest())
_fernet = Fernet(_FERNET_KEY)

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


# ============================================================================
# Symmetric encryption for sensitive data (API keys)
# ============================================================================

def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string using Fernet symmetric encryption.
    Returns a base64-encoded ciphertext string safe for DB storage."""
    if not plaintext:
        return ""
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted string back to plaintext."""
    if not ciphertext:
        return ""
    return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def mask_api_key(api_key: str) -> str:
    """Mask an API key for safe display: show only first 4 and last 4 chars.
    e.g. 'sk-abc123...xyz9' """
    if not api_key:
        return ""
    if len(api_key) <= 12:
        return api_key[:2] + "*" * (len(api_key) - 4) + api_key[-2:]
    return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
