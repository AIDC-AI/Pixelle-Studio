"""认证配置模型 - 支持多个认证配置并自动故障转移"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import json


@dataclass
class AuthProfile:
    """认证配置"""
    id: str
    provider: str  # "openai", "anthropic", "google", etc.
    api_key: str
    base_url: Optional[str] = None
    
    # 故障跟踪
    failure_count: int = 0
    last_failed_at: Optional[datetime] = None
    is_enabled: bool = True


@dataclass
class AuthStore:
    """认证配置存储"""
    profiles: List[AuthProfile] = field(default_factory=list)
    
    def get_candidates(self, provider: str) -> List[AuthProfile]:
        """获取指定 provider 的候选配置 (已启用 + 不在冷却期)"""
        candidates = [
            p for p in self.profiles
            if p.provider == provider and p.is_enabled
        ]
        
        # 过滤冷却期
        candidates = [
            p for p in candidates
            if not self.is_in_cooldown(p)
        ]
        
        # 按失败次数排序 (失败少的优先)
        candidates.sort(key=lambda p: p.failure_count)
        
        return candidates
    
    def is_in_cooldown(self, profile: AuthProfile) -> bool:
        """检查是否在冷却期 (指数退避)"""
        if not profile.last_failed_at:
            return False
        
        # 指数退避: 1s, 2s, 4s, 8s, 16s, 32s, 60s (最多)
        cooldown_ms = min(
            1000 * (2 ** profile.failure_count),
            60_000
        )
        
        elapsed = (datetime.now() - profile.last_failed_at).total_seconds() * 1000
        return elapsed < cooldown_ms
    
    def mark_failure(self, profile_id: str, reason: str):
        """记录失败"""
        for p in self.profiles:
            if p.id == profile_id:
                p.failure_count += 1
                p.last_failed_at = datetime.now()
                print(f"[AuthStore] Profile {profile_id} failed ({p.failure_count} times): {reason}")
                break
    
    def mark_success(self, profile_id: str):
        """记录成功 (重置失败计数)"""
        for p in self.profiles:
            if p.id == profile_id:
                p.failure_count = 0
                p.last_failed_at = None
                break
    
    def add_profile(self, profile: AuthProfile):
        """添加认证配置"""
        # 检查是否已存在
        existing = [p for p in self.profiles if p.id == profile.id]
        if existing:
            # 替换
            self.profiles = [p for p in self.profiles if p.id != profile.id]
        
        self.profiles.append(profile)
    
    def to_dict(self) -> dict:
        """转换为字典"""
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
        """从字典创建"""
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
        """从环境变量创建默认配置"""
        import os
        store = cls()
        
        # 主 API Key (从环境变量)
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        
        if api_key:
            store.add_profile(AuthProfile(
                id="openai-primary",
                provider="openai",
                api_key=api_key,
                base_url=base_url
            ))
        
        # 备用 API Key (如果配置了)
        backup_key = os.getenv("OPENAI_API_KEY_BACKUP")
        if backup_key:
            store.add_profile(AuthProfile(
                id="openai-backup",
                provider="openai",
                api_key=backup_key,
                base_url=base_url
            ))
        
        return store

