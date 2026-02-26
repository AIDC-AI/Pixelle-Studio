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

"""
Skill Agent - Native OpenAI API implementation with enhanced stability.

This agent uses direct OpenAI API calls (not Agents SDK) to:
1. Receive user input (text + optional files)
2. Stream LLM responses with tool calling support
3. Execute tools and continue the conversation loop
4. Support implicit code execution via <execute> blocks (Synthetic Tool Call)

Enhanced features:
- Three-layer failover (Auth, Model, Thinking Level)
- Automatic context management (Guard + Compaction)
- Improved error handling and retry logic
"""

import os
import json
import re
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator, Tuple

from openai import AsyncOpenAI
import httpx

from app.skills.loader import get_skill_loader
from app.tools import (
    AgentContext,
    TOOL_SCHEMAS,
    TOOL_HANDLERS,
)
from app.code_block_parser import process_code_blocks, has_code_blocks
from app.skills_manager import get_skills_summary
from app.prompt_builder import build_full_system_prompt
from app.utils.network import LOCAL_IP, SERVER_PORT
from app.auth.models import AuthStore
from app.config import get_config
from app.context import (
    evaluate_context_window_guard,
    should_compact_history,
    compact_history,
)
from app.utils.session_logger_simple import SessionLogger

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load configuration
config = get_config()

# LLM Configuration
DEFAULT_MODEL = config.default_model
LLM_TIMEOUT = config.llm_timeout
LLM_MAX_TOKENS = config.llm_max_tokens

logger.info(f"DEFAULT_MODEL: {DEFAULT_MODEL}")
logger.info(f"LLM_TIMEOUT: {LLM_TIMEOUT}s")
logger.info(f"LLM_MAX_TOKENS: {LLM_MAX_TOKENS}")


def _is_network_error(exc: Exception) -> bool:
    """
    Check if an exception is a transient network error that should trigger failover.
    
    These errors typically occur when the API gateway drops the connection during
    long streaming responses (e.g. httpx.ReadError, ConnectionError, etc.)
    """
    error_type = type(exc).__name__
    error_msg = str(exc).lower()
    
    # Check by exception type name
    network_error_types = [
        "ReadError",          # httpx.ReadError - connection dropped during streaming
        "WriteError",         # httpx.WriteError
        "ConnectError",       # httpx.ConnectError
        "RemoteProtocolError",# httpcore.RemoteProtocolError
        "ConnectionError",    # General connection error
        "ConnectionResetError",
        "BrokenPipeError",
    ]
    if error_type in network_error_types:
        return True
    
    # Check by error message patterns
    network_patterns = [
        "read error",
        "connection reset",
        "connection closed",
        "broken pipe",
        "peer closed",
        "network",
        "eof occurred",
        "remotedisconnected",
    ]
    return any(p in error_msg for p in network_patterns)


class SkillAgent:
    """
    Agent that handles user requests using native OpenAI API with enhanced stability.
    
    Enhanced features:
    - Three-layer failover (Auth/Model/Thinking)
    - Automatic context management
    - Improved error handling
    """
    
    def __init__(
        self, 
        max_turns: int = None, 
        history_messages: Optional[List[Dict[str, str]]] = None,
        mcp_server_url: Optional[str] = None,
        mcp_server_type: str = "sse",
        user_id: Optional[int] = None,
        auth_store: Optional[AuthStore] = None,
        user_llm_config: Optional[Dict[str, str]] = None,
        user_context_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the agent.
        
        Args:
            max_turns: Maximum number of conversation turns (safety limit)
            history_messages: Previous conversation history
            mcp_server_url: URL of the MCP server for tool calls
            mcp_server_type: Type of MCP server ("sse" or "http")
            user_id: User ID for isolation and personalization
            auth_store: Authentication store for failover (optional)
            user_llm_config: User-specific LLM config dict with keys: api_key, base_url, model_name
            user_context_config: User-specific context / advanced settings
        """
        # User-specific LLM configuration (REQUIRED – no env-var fallback)
        self.user_llm_config = user_llm_config or {}
        self.user_context_config = user_context_config or {}
        
        # Authentication config – only used when user provides their own key
        self.auth_store = auth_store or AuthStore()
        self.current_auth_profile = None
        
        # Client will be lazily initialized
        self.client = None
        
        # Model config - user config takes priority
        self.model = self.user_llm_config.get("model_name") or DEFAULT_MODEL
        
        # Model fallbacks - user override or system default
        user_fallbacks_str = self.user_context_config.get("model_fallbacks")
        if user_fallbacks_str:
            user_fallback_list = [m.strip() for m in user_fallbacks_str.split(",") if m.strip()]
            seen = set()
            chain = []
            for m in [self.model] + user_fallback_list:
                if m not in seen:
                    seen.add(m)
                    chain.append(m)
            self.model_fallbacks = chain
        else:
            self.model_fallbacks = config.get_model_chain(self.model)
        
        # Agent config - user override or explicit param or system default
        if max_turns is not None:
            self.max_turns = max_turns
        elif "agent_max_turns" in self.user_context_config:
            self.max_turns = self.user_context_config["agent_max_turns"]
        else:
            self.max_turns = config.agent_max_turns
        self.history_messages = history_messages or []
        self.mcp_server_url = mcp_server_url
        self.mcp_server_type = mcp_server_type
        self.user_id = str(user_id) if user_id is not None else None
        
        self.skill_loader = get_skill_loader()
        
        # Script storage
        script_subdir = self.user_id if self.user_id else "default"
        self.script_dir = Path(__file__).parent.parent / "scripts" / script_subdir
        self.script_dir.mkdir(parents=True, exist_ok=True)
        
        self.backend_root = Path(__file__).parent.parent
        
        # Context management state
        self.compaction_attempted = False
        
        # Session logger (lazy initialization)
        self.session_logger: Optional[SessionLogger] = None
    
    async def _init_client_with_failover(self) -> AsyncOpenAI:
        """
        Initialize LLM client.
        
        ONLY user-configured API keys are used.  Environment variables are
        intentionally ignored so that credentials are never leaked through
        shell configuration.  If no user key is present the caller
        (process_with_agent) should already have blocked the request.
        """
        # Get proxy config (proxy settings are infrastructure, not credentials)
        http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        
        # Build httpx client config
        httpx_config = {}
        if http_proxy or https_proxy:
            httpx_config["proxies"] = {
                "http://": http_proxy,
                "https://": https_proxy or http_proxy,
            }
            logger.info(f"[Agent] Using proxy: {https_proxy or http_proxy}")
        
        # --- User-specific LLM configuration (REQUIRED) ---
        user_api_key = self.user_llm_config.get("api_key")
        user_base_url = self.user_llm_config.get("base_url")
        
        if not user_api_key:
            raise RuntimeError(
                "No API key configured. Please go to Settings and add your API Key."
            )
        
        logger.info(f"[Agent] Using user-specific LLM config (model={self.model})")
        client_kwargs = {
            "api_key": user_api_key,
            "timeout": LLM_TIMEOUT,
        }
        if user_base_url:
            client_kwargs["base_url"] = user_base_url
        if httpx_config:
            client_kwargs["http_client"] = httpx.AsyncClient(**httpx_config)
        return AsyncOpenAI(**client_kwargs)
    
    async def _call_llm_with_failover(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        thinking_level: str = "medium"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Call LLM with model and thinking level failover.
        
        Yields:
            Stream chunks from LLM
        """
        # Get model chain
        if config.enable_model_failover:
            model_chain = self.model_fallbacks
        else:
            model_chain = [self.model]
        
        # Thinking Level chain
        if config.enable_thinking_failover:
            thinking_idx = config.thinking_levels.index(thinking_level) if thinking_level in config.thinking_levels else 1
            thinking_chain = config.thinking_levels[thinking_idx:]
        else:
            thinking_chain = [thinking_level]
        
        last_error = None
        
        # Try each model
        for model_name in model_chain:
            logger.info(f"[Agent] Trying model: {model_name}")
            
            # Try each thinking level
            for think_level in thinking_chain:
                try:
                    logger.info(f"[Agent] Trying thinking level: {think_level}")
                    
                    # Build request params
                    request_params = {
                        "model": model_name,
                        "messages": messages,
                        "stream": True,
                        "stream_options": {"include_usage": True},  # Track token usage in streaming mode
                    }
                    
                    # Add tools (if any)
                    if tools:
                        request_params["tools"] = tools
                    
                    # Claude models require max_tokens
                    if "claude" in model_name.lower():
                        request_params["max_tokens"] = LLM_MAX_TOKENS
                    
                    # Call API
                    response_stream = await self.client.chat.completions.create(**request_params)
                    
                    # Success, mark auth profile as successful
                    if self.current_auth_profile:
                        self.auth_store.mark_success(self.current_auth_profile.id)
                    
                    # Return stream, capture usage from last chunk
                    async for chunk in response_stream:
                        # Check for usage info (comes in the last chunk with stream_options)
                        if hasattr(chunk, 'usage') and chunk.usage is not None:
                            yield {
                                "type": "usage",
                                "model": model_name,
                                "prompt_tokens": chunk.usage.prompt_tokens or 0,
                                "completion_tokens": chunk.usage.completion_tokens or 0,
                                "total_tokens": chunk.usage.total_tokens or 0,
                            }
                        yield {"type": "chunk", "chunk": chunk}
                    
                    # Successfully completed
                    return
                
                except Exception as e:
                    error_msg = str(e).lower()
                    error_type = type(e).__name__
                    logger.error(f"[Agent] LLM call failed (model={model_name}, thinking={think_level}, error_type={error_type}): {e}")
                    
                    # Mark auth failure
                    if self.current_auth_profile:
                        if "401" in error_msg or "unauthorized" in error_msg:
                            self.auth_store.mark_failure(self.current_auth_profile.id, "auth_error")
                        elif "429" in error_msg or "rate_limit" in error_msg:
                            self.auth_store.mark_failure(self.current_auth_profile.id, "rate_limit")
                    
                    # Classify error and decide whether to continue
                    if "context" in error_msg and ("window" in error_msg or "too long" in error_msg):
                        # Context overflow - skip thinking levels, try next model
                        logger.warning(f"[Agent] Context overflow, trying next model...")
                        last_error = e
                        break  # Break out of thinking level loop
                    
                    elif "thinking" in error_msg or "extended_thinking" in error_msg or "unsupported" in error_msg:
                        # Thinking level not supported - try next level
                        logger.warning(f"[Agent] Thinking level {think_level} not supported, trying lower level...")
                        last_error = e
                        continue  # Continue thinking level loop
                    
                    elif "timeout" in error_msg:
                        # Timeout - try next model
                        logger.warning(f"[Agent] Timeout, trying next model...")
                        last_error = e
                        break  # Break out of thinking level loop
                    
                    elif "overloaded" in error_msg or "503" in error_msg:
                        # Server overloaded - try next model
                        logger.warning(f"[Agent] Server overloaded, trying next model...")
                        last_error = e
                        break  # Break out of thinking level loop
                    
                    elif "expecting value" in error_msg or "json" in error_msg.lower():
                        # JSON parse error - possibly empty response or HTML error page from API
                        logger.warning(f"[Agent] JSON parse error (possibly empty response or HTML error page), trying next model...")
                        last_error = e
                        break  # Break out of thinking level loop, try next model
                    
                    elif error_type == "APIError" and not error_msg:
                        # Empty error message APIError - possibly network issue
                        logger.warning(f"[Agent] Empty APIError (possibly network issue), trying next model...")
                        last_error = e
                        break  # Break out of thinking level loop
                    
                    elif _is_network_error(e):
                        # Network error (ReadError, connection reset, etc.) - try next model
                        logger.warning(f"[Agent] Network error ({error_type}), trying next model...")
                        last_error = e
                        break  # Break out of thinking level loop
                    
                    else:
                        # Other errors - raise directly
                        raise e
        
        # All models and thinking levels failed
        raise RuntimeError(f"All models and thinking levels failed. Last error: {last_error}")
    
    # Old <execute> block handler has been removed
    # Now using code block parser (code_block_parser.py) to handle ```language:filename format
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt using the modular Prompt Builder."""
        # Get skills summary (new format)
        skills_summary = get_skills_summary(user_id=self.user_id)
        
        # Build prompt using the new modular builder
        return build_full_system_prompt(
            skills_summary=skills_summary,
            available_tools=set(TOOL_HANDLERS.keys()),
            model=self.model,
            mcp_server_url=self.mcp_server_url,
            workspace_dir=str(self.backend_root)
        )
    
    def _create_context(self, session_id: str) -> AgentContext:
        """Create the context object passed to all tools."""
        # ✅ Don't pass script_dir and backend_root, let AgentContext calculate them
        # This ensures the latest date subdirectory is used
        return AgentContext(
            user_id=self.user_id,
            session_id=session_id,
            mcp_server_url=self.mcp_server_url,
            mcp_server_type=self.mcp_server_type,
        )
    
    async def _execute_tool(self, tool_call: Dict, context: AgentContext) -> str:
        """Execute a tool and return the result."""
        name = tool_call["function"]["name"]
        args_str = tool_call["function"]["arguments"]
        
        try:
            args = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError as e:
            logger.error(f"[Tool] Failed to parse arguments: {args_str}, error: {e}")
            return json.dumps({"status": "error", "error": f"Invalid JSON arguments: {e}"})
        
        logger.info(f"[Tool] Executing: {name} with args: {args}")
        
        # Handle regular tools
        handler = TOOL_HANDLERS.get(name)
        if handler:
            try:
                # All handlers take context as first argument
                if name == "list_mcp_tools":
                    result = await handler(context)
                else:
                    result = await handler(context, **args)
                return result
            except Exception as e:
                logger.error(f"[Tool] Error executing {name}: {e}")
                return json.dumps({"status": "error", "error": str(e)})
        
        return json.dumps({"status": "error", "error": f"Unknown tool: {name}"})
    
    def _parse_tool_json(self, result_text: str) -> Optional[Dict[str, Any]]:
        """Parse tool result JSON."""
        if not result_text:
            return None
        
        result_str = str(result_text).strip()
        if result_str.startswith("{"):
            try:
                return json.loads(result_str)
            except:
                pass
        return None

    async def run(
        self,
        user_message: str,
        session_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run the agent loop for a user request with enhanced stability.
        
        This implements:
        1. Build messages with history + current user message
        2. Context Window Guard + Auto-Compaction
        3. Call OpenAI API with streaming (with failover)
        4. Process tool calls (both explicit and Synthetic)
        5. Continue loop until no more tool calls
        6. Session logging for full traceability
        """
        session_id = session_id or str(uuid.uuid4())[:8]
        
        logger.info(f"[Agent] Starting session {session_id}")
        
        # === Initialize Session Logger ===
        self.session_logger = SessionLogger(session_id, self.user_id)
        self.session_logger.log_session_start(
            model=self.model,
            mcp_server_url=self.mcp_server_url
        )
        
        turn_count = 0  # Initialize turn_count
        
        try:
            # Initialize client (with failover)
            if self.client is None:
                self.client = await self._init_client_with_failover()
        
            # Build initial user message with file context
            full_user_message = user_message
            
            yield {"type": "status", "content": "Processing your request..."}
            
            # Create context
            context = self._create_context(session_id)
            
            # Build messages
            system_prompt = self._build_system_prompt()
            messages: List[Dict[str, Any]] = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add history
            for msg in self.history_messages:
                if msg["role"] in ["user", "assistant", "tool"]:
                    messages.append(msg)
            
            # Add current user message
            messages.append({"role": "user", "content": full_user_message})
            
            # === Log user message ===
            self.session_logger.log_message("user", full_user_message, turn=0)
        
            # === Context Window Guard ===
            # Resolve per-user context settings with system defaults
            _compaction_enabled = self.user_context_config.get("context_compaction_enabled", config.context_compaction_enabled)
            _keep_recent = self.user_context_config.get("context_keep_recent", config.context_keep_recent)
            
            if _compaction_enabled:
                should_block, warning, stats = evaluate_context_window_guard(
                    model=self.model,
                    messages=messages,
                    system_prompt=system_prompt
                )
            
                if warning:
                    logger.warning(f"[Agent] {warning}")
                    yield {"type": "status", "content": f"⚠️ {warning}"}
                
                if should_block and not self.compaction_attempted:
                    logger.info("[Agent] Context window too small, triggering auto-compaction...")
                    yield {"type": "status", "content": "Compacting conversation history..."}
                    
                    # Execute compaction (skip system and current user messages)
                    history_to_compact = messages[1:-1]  # Exclude system and last user message
                    
                    if len(history_to_compact) > _keep_recent:
                        compacted_history = await compact_history(
                            history_to_compact,
                            keep_recent=_keep_recent,
                            client=self.client
                        )
                        
                        # Rebuild message list
                        messages = [
                            {"role": "system", "content": system_prompt},
                            *compacted_history,
                            {"role": "user", "content": full_user_message}
                        ]
                        
                        # === Log context compaction ===
                        self.session_logger.log_context_compaction(
                            messages_before=len(history_to_compact),
                            messages_after=len(compacted_history)
                        )
                        
                        self.compaction_attempted = True
                        logger.info(f"[Agent] Compaction complete: {len(history_to_compact)} -> {len(compacted_history)} messages")
                        yield {"type": "status", "content": "✅ History compacted successfully"}
            
            # Agent loop
            MAX_TURNS = self.max_turns
            
            TURN_WARNING_THRESHOLD = max(MAX_TURNS - 5, int(MAX_TURNS * 0.8))
            
            while turn_count < MAX_TURNS:
                turn_count += 1
                logger.info(f"[Agent] Turn #{turn_count}/{MAX_TURNS}")
                
                # Warn when approaching turn limit
                if turn_count == TURN_WARNING_THRESHOLD:
                    logger.warning(f"[Agent] Approaching turn limit: {turn_count}/{MAX_TURNS}")
                    yield {
                        "type": "status",
                        "content": f"⚠️ Approaching turn limit ({turn_count}/{MAX_TURNS}). Please wrap up the current task."
                    }
                
                # === Log status ===
                self.session_logger.log_status(f"Turn {turn_count} started", turn=turn_count)
                
                # Clear pending code queue for this turn
                # Old pending_code_queue removed (no longer needed)
                context.last_response_text = ""
                
                try:
                    # === Call LLM with failover ===
                    final_content = ""
                    tool_calls_accumulator: Dict[int, Dict] = {}
                    turn_usage = None  # Track token usage for this turn
                
                    # Resolve thinking level: user override > system default
                    _thinking_level = self.user_context_config.get("default_thinking_level", config.default_thinking_level)
                    
                    async for event in self._call_llm_with_failover(
                        messages=messages,
                        tools=TOOL_SCHEMAS if TOOL_SCHEMAS else None,
                        thinking_level=_thinking_level
                    ):
                        # Capture usage event
                        if event["type"] == "usage":
                            turn_usage = event
                            continue
                        
                        if event["type"] != "chunk":
                            continue
                        
                        chunk = event["chunk"]
                        
                        if not chunk.choices:
                            continue
                        
                        delta = chunk.choices[0].delta
                        
                        # Text content
                        if delta.content:
                            final_content += delta.content
                            
                            # Check for new <execute> blocks
                            # Old execute block extraction logic removed
                            # Now using code block parser for ```language:filename format
                            pass
                            
                            yield {
                                "type": "response_delta",
                                "content": delta.content,
                                "accumulated": final_content
                            }
                        
                        # Tool calls (chunked)
                        if delta.tool_calls:
                            for tc_chunk in delta.tool_calls:
                                idx = tc_chunk.index
                                if idx not in tool_calls_accumulator:
                                    tool_calls_accumulator[idx] = {"id": "", "name": "", "arguments": ""}
                                
                                if tc_chunk.id:
                                    tool_calls_accumulator[idx]["id"] += tc_chunk.id
                                if tc_chunk.function and tc_chunk.function.name:
                                    tool_calls_accumulator[idx]["name"] += tc_chunk.function.name
                                if tc_chunk.function and tc_chunk.function.arguments:
                                    tool_calls_accumulator[idx]["arguments"] += tc_chunk.function.arguments
                    
                    # === Log LLM token usage ===
                    if turn_usage:
                        self.session_logger.log_llm_usage(
                            model=turn_usage["model"],
                            prompt_tokens=turn_usage["prompt_tokens"],
                            completion_tokens=turn_usage["completion_tokens"],
                            total_tokens=turn_usage["total_tokens"],
                            call_type="agent_chat",
                            turn=turn_count
                        )
                    
                    # Convert accumulated tool calls to list
                    tool_calls_list = []
                    for idx in sorted(tool_calls_accumulator.keys()):
                        tc = tool_calls_accumulator[idx]
                        tool_calls_list.append({
                            "id": tc["id"],
                            "type": "function",
                            "function": {"name": tc["name"], "arguments": tc["arguments"]}
                        })
                        logger.info(f"[Stream] Tool call: {tc['name']}")
                    
                    context.last_response_text = final_content
                    
                    # === Log assistant message ===
                    if final_content:
                        self.session_logger.log_message("assistant", final_content, turn=turn_count)
                    
                except Exception as e:
                    logger.error(f"[Agent] API Error: {e}", exc_info=True)
                    
                    # === Log error ===
                    self.session_logger.log_error(str(e), error_type=type(e).__name__, turn=turn_count)
                    
                    yield {"type": "error", "content": str(e)}
                    yield {"type": "final_result", "status": "error", "result": {"error": str(e)}}
                    return
            
                # === New mechanism: detect code blocks and auto-create files ===
                if has_code_blocks(final_content) and not tool_calls_list:
                    logger.info(f"[Agent] Detected code blocks in response, auto-creating files...")
                    yield {"type": "status", "content": "Detected code blocks, creating files..."}
                    
                    # Auto-create files
                    summary = await process_code_blocks(
                        final_content,
                        context,
                        TOOL_HANDLERS["write_file"]
                    )
                    
                    if summary:
                        # Add creation summary to response
                        final_content_with_summary = final_content + "\n\n" + summary
                        
                        # Add assistant message
                        messages.append({
                            "role": "assistant",
                            "content": final_content_with_summary
                        })
                        
                        # Yield the summary
                        yield {
                            "type": "status",
                            "content": summary
                        }
                        
                        logger.info(f"[Agent] Files created from code blocks: {summary}")
                    else:
                        # No summary, just add the original message
                        messages.append({
                            "role": "assistant",
                            "content": final_content
                        })
                    
                    # Continue the loop (let LLM continue the conversation)
                    continue
            
                # === Handle explicit tool calls ===
                if tool_calls_list:
                    # Add assistant message with tool_calls
                    assistant_msg = {
                        "role": "assistant",
                        "content": final_content or None,  # Can be empty if only tool calls
                        "tool_calls": tool_calls_list
                    }
                    messages.append(assistant_msg)
                    
                    # Execute each tool
                    for tc in tool_calls_list:
                        tool_name = tc["function"]["name"]
                        
                        # === Log tool call ===
                        try:
                            args = json.loads(tc["function"]["arguments"])
                        except:
                            args = {}
                        
                        self.session_logger.log_tool_call(
                            tool=tool_name,
                            args=args,
                            call_id=tc["id"],
                            turn=turn_count
                        )
                        
                        yield {
                            "type": "tool_call",
                            "name": tool_name,
                            "arguments": tc["function"]["arguments"],
                            "call_id": tc["id"]
                        }
                        
                        # Execute tool
                        import time
                        start_time = time.time()
                        result = await self._execute_tool(tc, context)
                        duration_ms = (time.time() - start_time) * 1000
                        
                        # === Log tool result ===
                        tool_data = self._parse_tool_json(result)
                        self.session_logger.log_tool_result(
                            tool=tool_name,
                            call_id=tc["id"],
                            status=tool_data.get("status", "success") if tool_data else "unknown",
                            result=result,
                            duration_ms=duration_ms
                        )
                        
                        # First send generic tool_result
                        yield {
                            "type": "tool_result",
                            "name": tool_name,
                            "result": result,
                            "call_id": tc["id"]
                        }
                        
                        # Parse tool result, send structured display event
                        tool_data = self._parse_tool_json(result)
                        if tool_data:
                            status = tool_data.get("status")
                            
                            # write_file: display file creation info
                            if tool_name == "write_file" and status == "success":
                                # ✅ Check notify_frontend field
                                notify_frontend = tool_data.get("notify_frontend", True)  # Default True for backward compatibility
                                
                                # ✅ Fallback: filter intermediate script files
                                file_path = tool_data.get("path", "")
                                actual_filename = tool_data.get("actual_filename", "")
                                
                                # Check if it's an intermediate script file
                                is_script_file = any(actual_filename.endswith(ext) for ext in ['.py', '.sh', '.js', '.ts'])
                                
                                # Only notify frontend when notify_frontend=True and not a script file
                                if notify_frontend and not is_script_file:
                                    relative_path = tool_data.get("relative_path", file_path)
                                    file_size = tool_data.get("size", 0)
                                    lines = tool_data.get("lines", 0)
                                    
                                    # ✅ Handle rename case
                                    was_renamed = tool_data.get("renamed", False)
                                    
                                    if was_renamed:
                                        original_name = tool_data.get("original_name", "")
                                        message = f"✅ File created (renamed): {original_name} -> {actual_filename} ({lines} lines, {file_size} bytes)"
                                    else:
                                        message = f"✅ File created: {relative_path} ({lines} lines, {file_size} bytes)"
                                    
                                    yield {
                                        "type": "file_created",
                                        "path": file_path,  # Absolute path
                                        "relative_path": relative_path,  # Relative path (more friendly)
                                        "actual_filename": actual_filename,  # Actual filename
                                        "renamed": was_renamed,  # Whether it was renamed
                                        "size": file_size,
                                        "lines": lines,
                                        "message": message
                                    }
                                else:
                                    # Log but don't notify frontend
                                    logger.debug(f"[agent] Skipping file notification: {actual_filename} (notify_frontend={notify_frontend}, is_script={is_script_file})")
                            
                            # exec/shell_exec: display execution result and detect files
                            # ✅ Process created_files for BOTH success AND error status
                            # (files may be created before a script error occurs)
                            elif tool_name in ["exec", "shell_exec"]:
                                if status == "success":
                                    stdout = tool_data.get("stdout", "") or tool_data.get("output", "")
                                    stderr = tool_data.get("stderr", "")
                                    if stdout or stderr:
                                        yield {
                                            "type": "execution_result",
                                            "tool": tool_name,
                                            "stdout": stdout,
                                            "stderr": stderr,
                                            "status": status
                                        }
                                
                                # ✅ Detect newly created files regardless of status
                                # Files may be created/modified even when exec returns an error
                                created_files = tool_data.get("created_files", [])
                                for file_info in created_files:
                                    file_name = file_info.get("name", "")
                                    
                                    # ✅ Fallback: filter intermediate script files
                                    is_script_file = any(file_name.endswith(ext) for ext in ['.py', '.sh', '.js', '.ts'])
                                    
                                    if not is_script_file:
                                        yield {
                                            "type": "file_created",
                                            "path": file_info.get("path", ""),
                                            "relative_path": file_name,
                                            "actual_filename": file_name,
                                            "renamed": False,
                                            "size": file_info.get("size", 0),
                                            "lines": file_info.get("lines", 0),
                                            "message": f"✅ File created: {file_name} ({file_info.get('size', 0)} bytes)"
                                        }
                                    else:
                                        logger.debug(f"[agent] Skipping script file notification: {file_name}")
                            
                            # read_file: display file content (if not too large)
                            elif tool_name == "read_file" and status == "success":
                                content = tool_data.get("content", "")
                                if len(content) < 10000:  # Display directly if < 10KB
                                    yield {
                                        "type": "file_content",
                                        "path": tool_data.get("path", ""),
                                        "content": content,
                                        "size": len(content)
                                    }
                            
                            # Legacy compatibility logic (to be gradually removed)
                            tool_type = tool_data.get("__tool__")
                            if tool_type == "execute_code":
                                yield {
                                    "type": "execution_result",
                                    "status": tool_data.get("status"),
                                    "stdout": tool_data.get("stdout", ""),
                                    "stderr": tool_data.get("stderr", ""),
                                    "result": tool_data.get("result"),
                                    "output_files": tool_data.get("output_files", [])
                                }
                            elif tool_type == "load_skill":
                                if tool_data.get("status") == "success":
                                    yield {
                                        "type": "skill_loaded",
                                        "skill_name": tool_data.get("skill_name")
                                    }
                    
                    # Add tool result to messages
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result
                    }
                    messages.append(tool_msg)
                    
                    # Send turn complete event to help frontend distinguish conversation turns
                    yield {
                        "type": "turn_complete",
                        "turn": turn_count,
                        "tool_calls_count": len(tool_calls_list)
                    }
                    
                    # Continue loop to let LLM process results
                    continue
                
                # No tool calls, no code blocks - we're done
                logger.info(f"[Agent] No more actions, finishing turn {turn_count}")
                break
            
            # Check if we exited due to turn limit
            if turn_count >= MAX_TURNS:
                logger.warning(f"[Agent] Turn limit reached: {turn_count}/{MAX_TURNS}")
                yield {
                    "type": "status",
                    "content": f"⚠️ Turn limit reached ({MAX_TURNS}). The task may be incomplete. You can continue by sending a follow-up message."
                }
            
            # Final response
            clean_answer = context.last_response_text  # No need to clean anymore
            
            # === Log session end ===
            self.session_logger.log_session_end(
                status="success" if turn_count < MAX_TURNS else "turn_limit",
                total_turns=turn_count
            )
            
            yield {
                "type": "final_result",
                "status": "success",
                "result": {"answer": clean_answer}
            }
        
        except Exception as e:
            # === Log error and end ===
            if hasattr(self, 'session_logger') and self.session_logger:
                self.session_logger.log_error(str(e), error_type=type(e).__name__)
                self.session_logger.log_session_end(
                    status="error",
                    total_turns=turn_count
                )
            raise
        
        finally:
            # === Close logger ===
            if hasattr(self, 'session_logger') and self.session_logger:
                self.session_logger.close()


async def run_agent(
    user_message: str,
    session_id: str = None,
    user_id: int = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function to run the agent.
    """
    agent = SkillAgent(user_id=user_id)
    async for event in agent.run(
        user_message=user_message,
        session_id=session_id
    ):
        yield event
