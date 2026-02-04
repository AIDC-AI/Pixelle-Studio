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
        max_turns: int = 20, 
        history_messages: Optional[List[Dict[str, str]]] = None,
        mcp_server_url: Optional[str] = None,
        mcp_server_type: str = "sse",
        user_id: Optional[int] = None,
        auth_store: Optional[AuthStore] = None
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
        """
        # 认证配置
        self.auth_store = auth_store or AuthStore.from_env()
        self.current_auth_profile = None
        
        # 客户端将延迟初始化
        self.client = None
        
        # 模型配置
        self.model = DEFAULT_MODEL
        self.model_fallbacks = config.get_model_chain(DEFAULT_MODEL)
        
        # Agent 配置
        self.max_turns = max_turns
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
        
        # 上下文管理状态
        self.compaction_attempted = False
        
        # Session logger (延迟初始化)
        self.session_logger: Optional[SessionLogger] = None
    
    async def _init_client_with_failover(self) -> AsyncOpenAI:
        """使用故障转移初始化 LLM 客户端"""
        # 获取代理配置
        http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
        
        # 构建 httpx 客户端配置
        httpx_config = {}
        if http_proxy or https_proxy:
            httpx_config["proxies"] = {
                "http://": http_proxy,
                "https://": https_proxy or http_proxy,
            }
            logger.info(f"[Agent] Using proxy: {https_proxy or http_proxy}")
        
        if not config.enable_auth_failover:
            # 不启用故障转移,直接使用默认配置
            logger.info("[Agent] Auth failover disabled, using default config")
            return AsyncOpenAI(timeout=LLM_TIMEOUT, http_client=httpx.AsyncClient(**httpx_config) if httpx_config else None)
        
        candidates = self.auth_store.get_candidates("openai")
        
        if not candidates:
            logger.warning("[Agent] No auth profiles available, using default")
            return AsyncOpenAI(timeout=LLM_TIMEOUT)
        
        last_error = None
        
        for profile in candidates:
            try:
                # 尝试使用当前配置
                client = AsyncOpenAI(
                    api_key=profile.api_key,
                    base_url=profile.base_url,
                    timeout=LLM_TIMEOUT,
                    http_client=httpx.AsyncClient(**httpx_config) if httpx_config else None
                )
                
                # 简单测试 (不实际调用 API,只是初始化)
                logger.info(f"[Agent] Using auth profile: {profile.id}")
                self.current_auth_profile = profile
                self.auth_store.mark_success(profile.id)
                return client
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # 分类错误
                if "401" in error_msg or "unauthorized" in error_msg:
                    reason = "auth_error"
                elif "429" in error_msg or "rate_limit" in error_msg:
                    reason = "rate_limit"
                elif "402" in error_msg or "quota" in error_msg:
                    reason = "billing_error"
                else:
                    reason = "unknown"
                
                # 记录失败
                self.auth_store.mark_failure(profile.id, reason)
                logger.warning(f"[Agent] Auth profile {profile.id} failed: {reason}")
                last_error = e
                
                # 继续尝试下一个
                continue
        
        # 所有配置都失败,使用默认配置
        logger.error(f"[Agent] All auth profiles failed: {last_error}")
        return AsyncOpenAI(timeout=LLM_TIMEOUT, http_client=httpx.AsyncClient(**httpx_config) if httpx_config else None)
    
    async def _call_llm_with_failover(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        thinking_level: str = "medium"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        调用 LLM (带模型和 Thinking Level 故障转移)。
        
        Yields:
            Stream chunks from LLM
        """
        # 获取模型链
        if config.enable_model_failover:
            model_chain = self.model_fallbacks
        else:
            model_chain = [self.model]
        
        # Thinking Level 链
        if config.enable_thinking_failover:
            thinking_idx = config.thinking_levels.index(thinking_level) if thinking_level in config.thinking_levels else 1
            thinking_chain = config.thinking_levels[thinking_idx:]
        else:
            thinking_chain = [thinking_level]
        
        last_error = None
        
        # 尝试每个模型
        for model_name in model_chain:
            logger.info(f"[Agent] Trying model: {model_name}")
            
            # 尝试每个 Thinking Level
            for think_level in thinking_chain:
                try:
                    logger.info(f"[Agent] Trying thinking level: {think_level}")
                    
                    # 构建请求参数
                    request_params = {
                        "model": model_name,
                        "messages": messages,
                        "stream": True,
                    }
                    
                    # 添加工具 (如果有)
                    if tools:
                        request_params["tools"] = tools
                    
                    # Claude 模型需要 max_tokens
                    if "claude" in model_name.lower():
                        request_params["max_tokens"] = LLM_MAX_TOKENS
                    
                    # 调用 API
                    response_stream = await self.client.chat.completions.create(**request_params)
                    
                    # 成功,标记认证配置成功
                    if self.current_auth_profile:
                        self.auth_store.mark_success(self.current_auth_profile.id)
                    
                    # 返回流
                    async for chunk in response_stream:
                        yield {"type": "chunk", "chunk": chunk}
                    
                    # 成功完成
                    return
                
                except Exception as e:
                    error_msg = str(e).lower()
                    error_type = type(e).__name__
                    logger.error(f"[Agent] LLM call failed (model={model_name}, thinking={think_level}, error_type={error_type}): {e}")
                    
                    # 标记认证失败
                    if self.current_auth_profile:
                        if "401" in error_msg or "unauthorized" in error_msg:
                            self.auth_store.mark_failure(self.current_auth_profile.id, "auth_error")
                        elif "429" in error_msg or "rate_limit" in error_msg:
                            self.auth_store.mark_failure(self.current_auth_profile.id, "rate_limit")
                    
                    # 分类错误并决定是否继续
                    if "context" in error_msg and ("window" in error_msg or "too long" in error_msg):
                        # 上下文溢出 - 不尝试其他 thinking level,直接尝试下一个模型
                        logger.warning(f"[Agent] Context overflow, trying next model...")
                        last_error = e
                        break  # 跳出 thinking level 循环
                    
                    elif "thinking" in error_msg or "extended_thinking" in error_msg or "unsupported" in error_msg:
                        # Thinking level 不支持 - 尝试下一个 level
                        logger.warning(f"[Agent] Thinking level {think_level} not supported, trying lower level...")
                        last_error = e
                        continue  # 继续 thinking level 循环
                    
                    elif "timeout" in error_msg:
                        # 超时 - 尝试下一个模型
                        logger.warning(f"[Agent] Timeout, trying next model...")
                        last_error = e
                        break  # 跳出 thinking level 循环
                    
                    elif "overloaded" in error_msg or "503" in error_msg:
                        # 服务器过载 - 尝试下一个模型
                        logger.warning(f"[Agent] Server overloaded, trying next model...")
                        last_error = e
                        break  # 跳出 thinking level 循环
                    
                    elif "expecting value" in error_msg or "json" in error_msg.lower():
                        # JSON 解析错误 - 可能是 API 返回了空响应或 HTML 错误页面
                        logger.warning(f"[Agent] JSON parse error (possibly empty response or HTML error page), trying next model...")
                        last_error = e
                        break  # 跳出 thinking level 循环，尝试下一个模型
                    
                    elif error_type == "APIError" and not error_msg:
                        # 空错误消息的 APIError - 可能是网络问题
                        logger.warning(f"[Agent] Empty APIError (possibly network issue), trying next model...")
                        last_error = e
                        break  # 跳出 thinking level 循环
                    
                    else:
                        # 其他错误 - 直接抛出
                        raise e
        
        # 所有模型和 thinking level 都失败
        raise RuntimeError(f"All models and thinking levels failed. Last error: {last_error}")
    
    # 旧的 <execute> 块处理函数已移除
    # 现在使用代码块解析器（code_block_parser.py）处理 ```language:filename 格式
    
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
        # ✅ 不传递 script_dir 和 backend_root，让 AgentContext 自己计算
        # 这样可以确保使用最新的日期子目录
        return AgentContext(
            user_id=self.user_id,
            session_id=session_id,
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
        
        # === 初始化 Session Logger ===
        self.session_logger = SessionLogger(session_id, self.user_id)
        self.session_logger.log_session_start(
            model=self.model,
            mcp_server_url=self.mcp_server_url
        )
        
        turn_count = 0  # 初始化 turn_count
        
        try:
            # 初始化客户端 (带故障转移)
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
            
            # === 记录用户消息 ===
            self.session_logger.log_message("user", full_user_message, turn=0)
        
            # === Context Window Guard ===
            if config.context_compaction_enabled:
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
                    
                    # 执行压缩 (跳过 system 和当前 user 消息)
                    history_to_compact = messages[1:-1]  # 排除 system 和最后的 user 消息
                    
                    if len(history_to_compact) > config.context_keep_recent:
                        compacted_history = await compact_history(
                            history_to_compact,
                            keep_recent=config.context_keep_recent,
                            client=self.client
                        )
                        
                        # 重建消息列表
                        messages = [
                            {"role": "system", "content": system_prompt},
                            *compacted_history,
                            {"role": "user", "content": full_user_message}
                        ]
                        
                        # === 记录上下文压缩 ===
                        self.session_logger.log_context_compaction(
                            messages_before=len(history_to_compact),
                            messages_after=len(compacted_history)
                        )
                        
                        self.compaction_attempted = True
                        logger.info(f"[Agent] Compaction complete: {len(history_to_compact)} -> {len(compacted_history)} messages")
                        yield {"type": "status", "content": "✅ History compacted successfully"}
            
            # Agent loop
            MAX_TURNS = self.max_turns
            
            while turn_count < MAX_TURNS:
                turn_count += 1
                logger.info(f"[Agent] Turn #{turn_count}")
                
                # === 记录状态 ===
                self.session_logger.log_status(f"Turn {turn_count} started", turn=turn_count)
                
                # Clear pending code queue for this turn
                # 旧的 pending_code_queue 已移除（不再需要）
                context.last_response_text = ""
                
                try:
                    # === Call LLM with failover ===
                    final_content = ""
                    tool_calls_accumulator: Dict[int, Dict] = {}
                
                    async for event in self._call_llm_with_failover(
                        messages=messages,
                        tools=TOOL_SCHEMAS if TOOL_SCHEMAS else None
                    ):
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
                            # 旧的 execute block 提取逻辑已移除
                            # 现在使用代码块解析器处理 ```language:filename 格式
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
                    
                    # === 记录 assistant 消息 ===
                    if final_content:
                        self.session_logger.log_message("assistant", final_content, turn=turn_count)
                    
                except Exception as e:
                    logger.error(f"[Agent] API Error: {e}", exc_info=True)
                    
                    # === 记录错误 ===
                    self.session_logger.log_error(str(e), error_type=type(e).__name__, turn=turn_count)
                    
                    yield {"type": "error", "content": str(e)}
                    yield {"type": "final_result", "status": "error", "result": {"error": str(e)}}
                    return
            
                # === 新机制：检测代码块并自动创建文件 ===
                if has_code_blocks(final_content) and not tool_calls_list:
                    logger.info(f"[Agent] Detected code blocks in response, auto-creating files...")
                    yield {"type": "status", "content": "检测到代码块，正在创建文件..."}
                    
                    # 自动创建文件
                    summary = await process_code_blocks(
                        final_content,
                        context,
                        TOOL_HANDLERS["write_file"]
                    )
                    
                    if summary:
                        # 添加创建摘要到响应
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
                        
                        # === 记录工具调用 ===
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
                        
                        # === 记录工具结果 ===
                        tool_data = self._parse_tool_json(result)
                        self.session_logger.log_tool_result(
                            tool=tool_name,
                            call_id=tc["id"],
                            status=tool_data.get("status", "success") if tool_data else "unknown",
                            result=result,
                            duration_ms=duration_ms
                        )
                        
                        # 先发送通用的 tool_result
                        yield {
                            "type": "tool_result",
                            "name": tool_name,
                            "result": result,
                            "call_id": tc["id"]
                        }
                        
                        # 解析工具结果，发送结构化的展示事件
                        tool_data = self._parse_tool_json(result)
                        if tool_data:
                            status = tool_data.get("status")
                            
                            # write_file: 展示文件创建信息
                            if tool_name == "write_file" and status == "success":
                                # ✅ 检查 notify_frontend 字段
                                notify_frontend = tool_data.get("notify_frontend", True)  # 默认True保持向后兼容
                                
                                # ✅ 兜底：过滤中间脚本文件
                                file_path = tool_data.get("path", "")
                                actual_filename = tool_data.get("actual_filename", "")
                                
                                # 判断是否是中间脚本文件
                                is_script_file = any(actual_filename.endswith(ext) for ext in ['.py', '.sh', '.js', '.ts'])
                                
                                # 只有 notify_frontend=True 且不是脚本文件时才通知前端
                                if notify_frontend and not is_script_file:
                                    relative_path = tool_data.get("relative_path", file_path)
                                    file_size = tool_data.get("size", 0)
                                    lines = tool_data.get("lines", 0)
                                    
                                    # ✅ 处理重命名情况
                                    was_renamed = tool_data.get("renamed", False)
                                    
                                    if was_renamed:
                                        original_name = tool_data.get("original_name", "")
                                        message = f"✅ 文件已创建（重命名）: {original_name} -> {actual_filename} ({lines} 行, {file_size} 字节)"
                                    else:
                                        message = f"✅ 文件已创建: {relative_path} ({lines} 行, {file_size} 字节)"
                                    
                                    yield {
                                        "type": "file_created",
                                        "path": file_path,  # 绝对路径
                                        "relative_path": relative_path,  # 相对路径（更友好）
                                        "actual_filename": actual_filename,  # 实际文件名
                                        "renamed": was_renamed,  # 是否被重命名
                                        "size": file_size,
                                        "lines": lines,
                                        "message": message
                                    }
                                else:
                                    # 记录日志但不通知前端
                                    logger.debug(f"[agent] 跳过文件通知: {actual_filename} (notify_frontend={notify_frontend}, is_script={is_script_file})")
                            
                            # exec/shell_exec: 展示执行结果
                            elif tool_name in ["exec", "shell_exec"] and status == "success":
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
                                
                                # ✅ 检测新创建的文件（exec/shell_exec 返回）
                                created_files = tool_data.get("created_files", [])
                                for file_info in created_files:
                                    file_name = file_info.get("name", "")
                                    
                                    # ✅ 兜底：过滤中间脚本文件
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
                                            "message": f"✅ 文件已创建: {file_name} ({file_info.get('size', 0)} 字节)"
                                        }
                                    else:
                                        logger.debug(f"[agent] 跳过脚本文件通知: {file_name}")
                            
                            # read_file: 展示文件内容（如果不太大）
                            elif tool_name == "read_file" and status == "success":
                                content = tool_data.get("content", "")
                                if len(content) < 10000:  # 小于10KB直接展示
                                    yield {
                                        "type": "file_content",
                                        "path": tool_data.get("path", ""),
                                        "content": content,
                                        "size": len(content)
                                    }
                            
                            # 旧的兼容逻辑（逐步移除）
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
                    
                    # 发送轮次完成事件，帮助前端区分对话轮次
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
            
            # Final response
            clean_answer = context.last_response_text  # No need to clean anymore
            
            # === 记录 session 结束 ===
            self.session_logger.log_session_end(
                status="success",
                total_turns=turn_count
            )
            
            yield {
                "type": "final_result",
                "status": "success",
                "result": {"answer": clean_answer}
            }
        
        except Exception as e:
            # === 记录错误和结束 ===
            if hasattr(self, 'session_logger') and self.session_logger:
                self.session_logger.log_error(str(e), error_type=type(e).__name__)
                self.session_logger.log_session_end(
                    status="error",
                    total_turns=turn_count
                )
            raise
        
        finally:
            # === 关闭 logger ===
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
