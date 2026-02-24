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

"""Authentication configuration models - supports multiple auth configs with automatic failover"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import json


@dataclass
class AuthProfile:
    """Authentication profile"""
    id: str
    provider: str  # "openai", "anthropic", "google", etc.
    api_key: str
    base_url: Optional[str] = None
    
    # Failure tracking
    failure_count: int = 0
    last_failed_at: Optional[datetime] = None
    is_enabled: bool = True


@dataclass
class AuthStore:
    """Authentication configuration storage"""
    profiles: List[AuthProfile] = field(default_factory=list)
    
    def get_candidates(self, provider: str) -> List[AuthProfile]:
        """Get candidate profiles for specified provider (enabled + not in cooldown)"""
        candidates = [
            p for p in self.profiles
            if p.provider == provider and p.is_enabled
        ]
        
        # Filter by cooldown period
        candidates = [
            p for p in candidates
            if not self.is_in_cooldown(p)
        ]
        
        # Sort by failure count (fewer failures first)
        candidates.sort(key=lambda p: p.failure_count)
        
        return candidates
    
    def is_in_cooldown(self, profile: AuthProfile) -> bool:
        """Check if in cooldown period (exponential backoff)"""
        if not profile.last_failed_at:
            return False
        
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, 60s (max)
        cooldown_ms = min(
            1000 * (2 ** profile.failure_count),
            60_000
        )
        
        elapsed = (datetime.now() - profile.last_failed_at).total_seconds() * 1000
        return elapsed < cooldown_ms
    
    def mark_failure(self, profile_id: str, reason: str):
        """Record failure"""
        for p in self.profiles:
            if p.id == profile_id:
                p.failure_count += 1
                p.last_failed_at = datetime.now()
                print(f"[AuthStore] Profile {profile_id} failed ({p.failure_count} times): {reason}")
                break
    
    def mark_success(self, profile_id: str):
        """Record success (reset failure count)"""
        for p in self.profiles:
            if p.id == profile_id:
                p.failure_count = 0
                p.last_failed_at = None
                break
    
    def add_profile(self, profile: AuthProfile):
        """Add authentication profile"""
        # Check if already exists
        existing = [p for p in self.profiles if p.id == profile.id]
        if existing:
            # Replace
            self.profiles = [p for p in self.profiles if p.id != profile.id]
        
        self.profiles.append(profile)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "profiles": [
                {
                    "id": p.id,
                    "provider": p.provider,
                    "api_key": p.api_key,
                    "base_url": p.base_url,
                    "failure_count": p.failure_count,
                    "last_failed_at": p.last_failed_at.isoformat() if p.last_failed_at else None,
                    "is_enabled": p.is_enabled
                }
                for p in self.profiles
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AuthStore":
        """Create from dictionary"""
        store = cls()
        for p_data in data.get("profiles", []):
            profile = AuthProfile(
                id=p_data["id"],
                provider=p_data["provider"],
                api_key=p_data["api_key"],
                base_url=p_data.get("base_url"),
                failure_count=p_data.get("failure_count", 0),
                last_failed_at=datetime.fromisoformat(p_data["last_failed_at"]) if p_data.get("last_failed_at") else None,
                is_enabled=p_data.get("is_enabled", True)
            )
            store.profiles.append(profile)
        return store
    
    @classmethod
    def from_env(cls) -> "AuthStore":
        """Create default configuration from environment variables"""
        import os
        store = cls()
        
        # Primary API Key (from environment variables)
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        
        if api_key:
            store.add_profile(AuthProfile(
                id="openai-primary",
                provider="openai",
                api_key=api_key,
                base_url=base_url
            ))
        
        # Backup API Key (if configured)
        backup_key = os.getenv("OPENAI_API_KEY_BACKUP")
        if backup_key:
            store.add_profile(AuthProfile(
                id="openai-backup",
                provider="openai",
                api_key=backup_key,
                base_url=base_url
            ))
        
        return store

