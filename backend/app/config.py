"""配置管理 - 支持多模型和故障转移"""

import os
from typing import List, Dict, Any
import json
from pathlib import Path


class AgentConfig:
    """Agent 配置"""
    
    def __init__(self):
        # 模型配置
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # 模型 fallback 链
        self.model_fallbacks = self._load_model_fallbacks()
        
        # LLM 配置
        self.llm_timeout = float(os.getenv("LLM_TIMEOUT", "300"))
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "16384"))
        
        # 上下文管理配置
        self.context_compaction_enabled = os.getenv("CONTEXT_COMPACTION_ENABLED", "true").lower() == "true"
        self.context_keep_recent = int(os.getenv("CONTEXT_KEEP_RECENT", "10"))
        self.context_min_messages_before_compact = int(os.getenv("CONTEXT_MIN_MESSAGES_BEFORE_COMPACT", "15"))
        
        # Thinking Level 配置
        self.thinking_levels = ['high', 'medium', 'low', 'off']
        self.default_thinking_level = os.getenv("DEFAULT_THINKING_LEVEL", "medium")
        
        # 故障转移配置
        self.enable_auth_failover = os.getenv("ENABLE_AUTH_FAILOVER", "true").lower() == "true"
        self.enable_model_failover = os.getenv("ENABLE_MODEL_FAILOVER", "true").lower() == "true"
        self.enable_thinking_failover = os.getenv("ENABLE_THINKING_FAILOVER", "true").lower() == "true"
    
    def _load_model_fallbacks(self) -> List[str]:
        """加载模型 fallback 链"""
        # 尝试从配置文件加载
        config_file = Path(__file__).parent / "config" / "model_fallbacks.json"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    data = json.load(f)
                    return data.get("fallbacks", [])
            except Exception as e:
                print(f"[Config] Failed to load model fallbacks: {e}")
        
        # 默认 fallback 链
        default_fallbacks = {
            "gpt-4o": ["gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "gpt-4-turbo": ["gpt-4o", "gpt-3.5-turbo"],
            "gpt-4": ["gpt-4-turbo", "gpt-3.5-turbo"],
            "claude-3-5-sonnet": ["claude-3-sonnet", "claude-3-opus"],
        }
        
        return default_fallbacks.get(self.default_model, ["gpt-3.5-turbo"])
    
    def get_model_chain(self, primary_model: str = None) -> List[str]:
        """
        获取完整的模型链 (主模型 + fallback)。
        
        Args:
            primary_model: 主模型名称 (如果不提供,使用默认模型)
        
        Returns:
            模型列表 [主模型, fallback1, fallback2, ...]
        """
        model = primary_model or self.default_model
        
        # 如果不启用故障转移,只返回主模型
        if not self.enable_model_failover:
            return [model]
        
        # 返回主模型 + fallback
        fallbacks = self.model_fallbacks
        
        # 去重并保持顺序
        seen = set()
        chain = []
        for m in [model] + fallbacks:
            if m not in seen:
                seen.add(m)
                chain.append(m)
        
        return chain
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "default_model": self.default_model,
            "model_fallbacks": self.model_fallbacks,
            "llm_timeout": self.llm_timeout,
            "llm_max_tokens": self.llm_max_tokens,
            "context_compaction_enabled": self.context_compaction_enabled,
            "context_keep_recent": self.context_keep_recent,
            "context_min_messages_before_compact": self.context_min_messages_before_compact,
            "thinking_levels": self.thinking_levels,
            "default_thinking_level": self.default_thinking_level,
            "enable_auth_failover": self.enable_auth_failover,
            "enable_model_failover": self.enable_model_failover,
            "enable_thinking_failover": self.enable_thinking_failover,
        }


# 全局配置实例
_global_config = None


def get_config() -> AgentConfig:
    """获取全局配置实例"""
    global _global_config
    if _global_config is None:
        _global_config = AgentConfig()
    return _global_config


def reload_config():
    """重新加载配置"""
    global _global_config
    _global_config = AgentConfig()
    return _global_config

