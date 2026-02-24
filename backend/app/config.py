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

"""Configuration management - supports multi-model and failover"""

import os
from typing import List, Dict, Any
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env file (must be called before reading environment variables)
load_dotenv()


class AgentConfig:
    """Agent configuration"""
    
    def __init__(self):
        # Model configuration
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        # Model fallback chain
        self.model_fallbacks = self._load_model_fallbacks()
        
        # LLM configuration
        self.llm_timeout = float(os.getenv("LLM_TIMEOUT", "300"))
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "16384"))
        
        # Context management configuration
        self.context_compaction_enabled = os.getenv("CONTEXT_COMPACTION_ENABLED", "true").lower() == "true"
        self.context_keep_recent = int(os.getenv("CONTEXT_KEEP_RECENT", "10"))
        self.context_min_messages_before_compact = int(os.getenv("CONTEXT_MIN_MESSAGES_BEFORE_COMPACT", "15"))
        
        # Thinking Level configuration
        self.thinking_levels = ['high', 'medium', 'low', 'off']
        self.default_thinking_level = os.getenv("DEFAULT_THINKING_LEVEL", "medium")
        
        # Failover configuration
        self.enable_auth_failover = os.getenv("ENABLE_AUTH_FAILOVER", "true").lower() == "true"
        self.enable_model_failover = os.getenv("ENABLE_MODEL_FAILOVER", "true").lower() == "true"
        self.enable_thinking_failover = os.getenv("ENABLE_THINKING_FAILOVER", "true").lower() == "true"
    
    def _load_model_fallbacks(self) -> List[str]:
        """
        Load model fallback chain.
        
        Priority:
        1. Environment variable MODEL_FALLBACKS (comma-separated)
        2. Config file app/config/model_fallbacks.json
        3. Code defaults
        """
        # 1. Try loading from environment variable (highest priority)
        env_fallbacks = os.getenv("MODEL_FALLBACKS")
        if env_fallbacks:
            # Support comma-separated model list
            models = [m.strip() for m in env_fallbacks.split(",") if m.strip()]
            if models:
                print(f"[Config] Using model fallbacks from environment: {models}")
                return models
        
        # 2. Try loading from config file
        config_file = Path(__file__).parent / "config" / "model_fallbacks.json"
        if config_file.exists():
            try:
                with open(config_file, "r") as f:
                    data = json.load(f)
                    fallbacks = data.get("fallbacks", [])
                    if fallbacks:
                        print(f"[Config] Using model fallbacks from config file: {fallbacks}")
                        return fallbacks
            except Exception as e:
                print(f"[Config] Failed to load model fallbacks from file: {e}")
        
        # 3. Use code defaults (fallback)
        default_fallbacks = {
            "gpt-4o": ["gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "gpt-4-turbo": ["gpt-4o", "gpt-3.5-turbo"],
            "gpt-4": ["gpt-4-turbo", "gpt-3.5-turbo"],
            "claude-3-5-sonnet": ["claude-3-sonnet", "claude-3-opus"],
        }
        
        fallbacks = default_fallbacks.get(self.default_model, ["gpt-3.5-turbo"])
        print(f"[Config] Using default model fallbacks for {self.default_model}: {fallbacks}")
        return fallbacks
    
    def get_model_chain(self, primary_model: str = None) -> List[str]:
        """
        Get the complete model chain (primary model + fallbacks).
        
        Args:
            primary_model: Primary model name (if not provided, uses default model)
        
        Returns:
            Model list [primary_model, fallback1, fallback2, ...]
        """
        model = primary_model or self.default_model
        
        # If failover is not enabled, return only the primary model
        if not self.enable_model_failover:
            return [model]
        
        # Return primary model + fallbacks
        fallbacks = self.model_fallbacks
        
        # Deduplicate while preserving order
        seen = set()
        chain = []
        for m in [model] + fallbacks:
            if m not in seen:
                seen.add(m)
                chain.append(m)
        
        return chain
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
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


# Global configuration instance
_global_config = None


def get_config() -> AgentConfig:
    """Get global configuration instance"""
    global _global_config
    if _global_config is None:
        _global_config = AgentConfig()
    return _global_config


def reload_config():
    """Reload configuration"""
    global _global_config
    _global_config = AgentConfig()
    return _global_config

