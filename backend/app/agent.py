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

from app.skills.loader import get_skill_loader
from app.tools import (
    AgentContext,
    TOOL_SCHEMAS,
    TOOL_HANDLERS,
    execute_code_internal,
)
from app.utils.network import LOCAL_IP, SERVER_PORT
from app.auth.models import AuthStore
from app.config import get_config
from app.context import (
    evaluate_context_window_guard,
    should_compact_history,
    compact_history,
)

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
    
    async def _init_client_with_failover(self) -> AsyncOpenAI:
        """使用故障转移初始化 LLM 客户端"""
        if not config.enable_auth_failover:
            # 不启用故障转移,直接使用默认配置
            logger.info("[Agent] Auth failover disabled, using default config")
            return AsyncOpenAI(timeout=LLM_TIMEOUT)
        
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
                    timeout=LLM_TIMEOUT
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
        return AsyncOpenAI(timeout=LLM_TIMEOUT)
    
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
                    logger.error(f"[Agent] LLM call failed (model={model_name}, thinking={think_level}): {e}")
                    
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
                    
                    else:
                        # 其他错误 - 直接抛出
                        raise e
        
        # 所有模型和 thinking level 都失败
        raise RuntimeError(f"All models and thinking levels failed. Last error: {last_error}")
    
    @staticmethod
    def _extract_execute_blocks(text: str) -> List[str]:
        """Extract code from <execute lang="python">...</execute> blocks."""
        pattern = r'<execute\s+lang=["\']python["\']\s*>(.*?)</execute>'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        return [match.strip() for match in matches if match.strip()]
    
    @staticmethod
    def _has_incomplete_execute_block(text: str) -> bool:
        """Check if text contains an incomplete <execute> block."""
        if not text:
            return False
        open_pattern = r'<execute\s+lang=["\']python["\']\s*>'
        close_pattern = r'</execute>'
        open_count = len(re.findall(open_pattern, text, re.IGNORECASE))
        close_count = len(re.findall(close_pattern, text, re.IGNORECASE))
        return open_count > close_count
    
    @staticmethod
    def _clean_response_text(text: str) -> str:
        """Clean response text by removing <execute> code blocks."""
        if not text:
            return text
        pattern = r'<execute\s+lang=["\']python["\']\s*>.*?</execute>'
        cleaned = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with skills in XML format."""
        skills_xml = self.skill_loader.build_skills_xml_prompt(self.user_id)
        
        system_prompt = f"""You are an intelligent agent designed to help users accomplish complex tasks by leveraging specific skill domains and external tools.

<capabilities>
You have access to the following tools for task execution:
1. **load_skill**: Load detailed documentation for a specific skill domain (Excel, PowerPoint, etc.).
2. **read_skill_file**: Read specific files (templates, logic, etc.) from a skill's directory.
3. **list_skill_tree**: List all files within a skill directory to understand available resources.
4. **list_mcp_tools**: Discover available MCP tools for connecting to external services.
</capabilities>

{skills_xml}

<environment_and_paths>
Your code runs in a backend environment with a fixed file structure.
- **Working Directory**: The root of the backend.
  - `skills/`: Contains internal skill resources and helper scripts. (READ-ONLY)
  - `scripts/`: Destination for all user-related files and outputs. (READ-WRITE)

- **Path Helpers (Pre-injected)**:
  - `user_file("filename")`: Returns the full path to a file in the user's `scripts/` directory.
    - [CRITICAL!]**Writing**: Save any generated file using `user_file("output.xlsx")` as the path.
    - [CRITICAL!]**Reading**: Read previously generated or uploaded files using the SAME helper: `open(user_file("snake.html"), "r")` or `pd.read_excel(user_file("data.xlsx"))`.
    - [CRITICAL!] Don't define `user_file` yourself - it's already injected into your execution environment!
  - `skill_path("skill_name", "relative/path")`: Use this to reference internal skill resources (e.g., templates or JS scripts) inside the `skills/` directory.

**CRITICAL**: Strictly forbidden to create or modify any files within the `skills/` directory. All generated artifacts MUST use `user_file()`.
</environment_and_paths>

<python_execution_protocol>
All logic execution must follow these strict technical rules:

1. **Syntax**: Write code inside `<execute lang="python">...</execute>` tags.
2. **Independent Execution**: Each block runs as a FRESH Python script. 
   - Variables, DataFrames, and objects **DO NOT persist** between blocks.
   - Every block must be **FULLY self-contained**: include all imports, re-read files, and define all necessary logic.
3. **MCP Integration (Async)**:
   - Call MCP tools using: `await call_tool("tool_name", {{"arg1": value1}})`.
   - Use `asyncio.run(main())` pattern for all async code execution.
   - Use `await list_mcp_tools()` to discover available external capabilities.
</python_execution_protocol>

<skill_usage_sop>
When a skill domain is involved, you MUST follow this Standard Operating Procedure:
1. **Discovery**: Read the loaded skill's `SKILL.md` and ALL referenced documentation before writing any code.
2. **Constraint Extraction**: Identify all "CRITICAL", "NEVER", "ALWAYS", or "MUST" rules. These are non-negotiable.
3. **Workflow Adherence**: Execute steps in the exact order specified in the documentation. Do not skip or reorder steps.
4. **No Improvisation**: Do not make assumptions. If the skill documentation provides a specific method, use it exclusively.
</skill_usage_sop>

<decision_flow>
Process user requests using the following logic:

1. **Analyze the request first** - Before doing ANYTHING, understand what the user wants:
   - Simple question? → Answer directly, NO tools needed.
   - General coding task (games, scripts, data processing)? → Write code directly, NO skill needed.
   - Domain-specific task matching a skill (PPT creation, Excel analysis with specific templates)? → Load that ONE skill.

2. **Skill decision** - Check <available_skills> descriptions:
   - If a skill clearly matches → call `load_skill` for that ONE skill only
   - If no skill matches → proceed WITHOUT loading any skill
   - **NEVER load multiple skills** - pick the best one or none

3. **Execute** - Write Python code in `<execute>` tags when needed.

4. **Recover** - If an error occurs, analyze and fix immediately.

**Examples of when NOT to load skills:**
- "写一个贪吃蛇游戏" → No skill needed, just write the game code
- "帮我分析这个CSV文件" → No skill needed unless you need specific xlsx templates
- "What is 2+2?" → No skill needed, just answer
- "Create a simple HTML page" → No skill needed
</decision_flow>

<output_format>
**CRITICAL**: Every code execution that generates files MUST end by printing a JSON status to stdout.
This JSON is parsed by the system to display generated files to the user.

```python
import json

# At the END of your code, after all file operations:
print(json.dumps({{
    "status": "success",  # or "error"
    "result": "Brief description of what was done",
    "output_files": [
        {{"file_name": "generated_file1.pptx"}},
        {{"file_name": "generated_file2.png"}}
    ]  # List ALL files created using user_file() - use ONLY the filename, not the full path
}}))
```

**Rules**:
1. The `output_files` array MUST contain ALL generated files that the user should see
2. Use `{{"file_name": "xxx"}}` format - only the filename, NOT the full path from user_file()
3. If NO files are generated, use an empty array: `"output_files": []`
4. Always print this JSON as the LAST thing in your code
5. Do NOT wrap in try/except that might suppress this output
</output_format>
"""        
        return system_prompt
    
    def _create_context(self, session_id: str) -> AgentContext:
        """Create the context object passed to all tools."""
        return AgentContext(
            user_id=self.user_id,
            session_id=session_id,
            skill_loader=self.skill_loader,
            script_dir=self.script_dir,
            backend_root=self.backend_root,
            mcp_server_url=self.mcp_server_url,
            mcp_server_type=self.mcp_server_type,
            loaded_skills={},
            tool_call_count=0,
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
        
        # Handle execute_code specially (Synthetic Tool Call)
        if name == "execute_code":
            code = args.get("code", "")
            if code:
                return await execute_code_internal(context, code)
            else:
                return json.dumps({"status": "error", "error": "No code provided"})
        
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
        """
        session_id = session_id or str(uuid.uuid4())[:8]
        
        logger.info(f"[Agent] Starting session {session_id}")
        
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
                    
                    self.compaction_attempted = True
                    logger.info(f"[Agent] Compaction complete: {len(history_to_compact)} -> {len(compacted_history)} messages")
                    yield {"type": "status", "content": "✅ History compacted successfully"}
        
        # Agent loop
        MAX_TURNS = self.max_turns
        turn_count = 0
        
        while turn_count < MAX_TURNS:
            turn_count += 1
            logger.info(f"[Agent] Turn #{turn_count}")
            
            # Clear pending code queue for this turn
            context.pending_code_queue = []
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
                        execute_blocks = self._extract_execute_blocks(final_content)
                        existing_count = len(context.pending_code_queue)
                        new_blocks = execute_blocks[existing_count:]
                        for block in new_blocks:
                            context.pending_code_queue.append(block)
                            logger.info(f"[Stream] Found execute block #{len(context.pending_code_queue)}")
                        
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
                
            except Exception as e:
                logger.error(f"[Agent] API Error: {e}", exc_info=True)
                yield {"type": "error", "content": str(e)}
                yield {"type": "final_result", "status": "error", "result": {"error": str(e)}}
                return
            
            # Check for incomplete execute blocks and try to continue
            if self._has_incomplete_execute_block(final_content):
                logger.warning(f"[Agent] Incomplete <execute> block detected, asking model to continue...")
                yield {"type": "status", "content": "Response was truncated, asking model to continue..."}
                
                # Add the incomplete response and ask to continue
                messages.append({"role": "assistant", "content": final_content})
                messages.append({"role": "user", "content": "Your response was truncated. Please continue from where you left off, completing the <execute> block. Do NOT repeat what you already wrote, just continue from the exact point of truncation."})
                continue  # Continue the loop to get more output
            
            # === Synthetic Tool Call: Check for <execute> blocks ===
            if context.pending_code_queue and not tool_calls_list:
                # LLM wrote code but didn't call execute_code explicitly
                # We create a Synthetic Tool Call
                code_to_exec = context.pending_code_queue[-1]
                synthetic_call_id = f"call_synthetic_{uuid.uuid4().hex[:8]}"
                
                logger.info(f"[Agent] Creating Synthetic Tool Call for code block (length: {len(code_to_exec)})")
                yield {"type": "status", "content": "Executing code..."}
                
                # Yield the original code to frontend
                yield {
                    "type": "code",
                    "code": code_to_exec
                }
                
                # Add assistant message with synthetic tool_calls
                assistant_msg = {
                    "role": "assistant",
                    "content": final_content,
                    "tool_calls": [{
                        "id": synthetic_call_id,
                        "type": "function",
                        "function": {
                            "name": "execute_code",
                            "arguments": json.dumps({"code": code_to_exec})
                        }
                    }]
                }
                messages.append(assistant_msg)
                
                # Execute the code
                result = await execute_code_internal(context, code_to_exec)
                
                # Yield execution result to frontend
                tool_data = self._parse_tool_json(result)
                if tool_data:
                    yield {
                        "type": "execution_result",
                        "status": tool_data.get("status"),
                        "stdout": tool_data.get("stdout", ""),
                        "stderr": tool_data.get("stderr", ""),
                        "result": tool_data.get("result"),
                        "output_files": tool_data.get("output_files", [])
                    }
                
                # Add tool result message
                tool_msg = {
                    "role": "tool",
                    "tool_call_id": synthetic_call_id,
                    "content": result
                }
                messages.append(tool_msg)
                
                # Continue loop
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
                    
                    yield {
                        "type": "tool_call",
                        "name": tool_name,
                        "arguments": tc["function"]["arguments"],
                        "call_id": tc["id"]
                    }
                    
                    # Execute tool
                    result = await self._execute_tool(tc, context)
                    
                    yield {
                        "type": "tool_result",
                        "name": tool_name,
                        "result": result,
                        "call_id": tc["id"]
                    }
                    
                    # Parse and yield structured result for UI
                    tool_data = self._parse_tool_json(result)
                    if tool_data:
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
                
                # Continue loop to let LLM process results
                continue
            
            # No tool calls, no code blocks - we're done
            logger.info(f"[Agent] No more actions, finishing turn {turn_count}")
            break
        
        # Final response
        clean_answer = self._clean_response_text(context.last_response_text)
        
        yield {
            "type": "final_result",
            "status": "success",
            "result": {"answer": clean_answer}
        }


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
