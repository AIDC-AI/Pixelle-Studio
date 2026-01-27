"""
Skill Agent - Single Agent loop for executing user requests with skill guidance.

This is a refactored agent using OpenAI Agents SDK that:
1. Receives user input (text + optional files)
2. Uses tool calling to decide actions (load_skill, execute_code, etc.)
3. Streams results back to the client
4. Continues the loop until the task is complete

The agent uses SKILL.md files for domain-specific guidance, which include
error handling patterns and best practices.
"""

import os
import json
import re
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass

from openai import AsyncOpenAI
from agents import Agent, Runner, ModelSettings, set_default_openai_client, OpenAIChatCompletionsModel
from agents.run import RunConfig
from agents.items import (
    TResponseInputItem,
    MessageOutputItem,
    ToolCallItem,
    ToolCallOutputItem,
)
from agents.stream_events import (
    RawResponsesStreamEvent,
    RunItemStreamEvent,
    AgentUpdatedStreamEvent,
)

from app.skills.loader import get_skill_loader
from app.tools import (
    AgentContext,
    load_skill,
    read_skill_file,
    list_skill_tree,
    execute_code,
    list_mcp_tools,
    SKILL_TOOLS,
)
from app.utils.network import LOCAL_IP, SERVER_PORT

from app.llm_adapter import DEFAULT_MODEL

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from agents import Agent, Runner, function_tool, set_default_openai_api, set_tracing_disabled, set_trace_processors
from langsmith.wrappers import OpenAIAgentsTracingProcessor
set_tracing_disabled(False)
set_default_openai_api("chat_completions")
set_trace_processors([OpenAIAgentsTracingProcessor()])

logging.info(f"DEFAULT_MODEL: {DEFAULT_MODEL}")
logging.info(f"OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY')}")
logging.info(f"OPENAI_BASE_URL: {os.getenv('OPENAI_BASE_URL')}")

# Configure OpenAI client with extended timeout for long-running LLM requests
# Default timeout is too short for complex tasks like PPT generation
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "300"))  # 5 minutes default
custom_openai_client = AsyncOpenAI(timeout=LLM_TIMEOUT)
set_default_openai_client(custom_openai_client)
logging.info(f"LLM_TIMEOUT: {LLM_TIMEOUT}s")
# from anthropic import Anthropic
# claude_client = Anthropic(
#     auth_token=os.getenv('ANTHROPIC_API_KEY'),
#     base_url=os.getenv('ANTHROPIC_BASE_URL'),
#     max_retries=0  # 将最大重试次数设置为0，完全禁用重试
# )


class SkillAgent:
    """
    Single Agent that handles user requests with skill guidance.
    
    The agent uses OpenAI Agents SDK with tool calling to:
    - Answer directly (for simple questions)
    - Load skills for domain-specific guidance
    - Execute Python code (for tasks requiring computation)
    - Call MCP tools for external services
    
    The agent loop continues until the agent decides the task is complete.
    """
    
    def __init__(
        self, 
        max_tool_calls: int = 20, 
        history_messages: Optional[List[Dict[str, str]]] = None,
        mcp_server_url: Optional[str] = None,
        mcp_server_type: str = "sse",
        user_id: Optional[int] = None
    ):
        """
        Initialize the agent.
        
        Args:
            max_tool_calls: Maximum number of tool calls (safety limit)
            history_messages: Previous conversation history
            mcp_server_url: URL of the MCP server to use for tool calls
            mcp_server_type: Type of MCP server ("sse" or "http")
            user_id: User ID for isolation and personalization
        """
        self.skill_loader = get_skill_loader()
        self.max_tool_calls = max_tool_calls
        self.history_messages = history_messages or []
        self.mcp_server_url = mcp_server_url
        self.mcp_server_type = mcp_server_type
        # Convert user_id to string for file paths
        self.user_id = str(user_id) if user_id is not None else None
        
        # Script storage - scripts/<user_id>/
        script_subdir = self.user_id if self.user_id else "default"
        self.script_dir = Path(__file__).parent.parent / "scripts" / script_subdir
        self.script_dir.mkdir(parents=True, exist_ok=True)
        
        # Backend root directory (contains both skills/ and scripts/)
        self.backend_root = Path(__file__).parent.parent
    
    @staticmethod
    def _extract_execute_blocks(text: str) -> List[str]:
        """
        Extract code from <execute lang="python">...</execute> blocks.
        
        Returns:
            List[str]: Extracted code blocks
        """
        pattern = r'<execute\s+lang=["\']python["\']\s*>(.*?)</execute>'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        return [match.strip() for match in matches if match.strip()]
    
    @staticmethod
    def _has_incomplete_execute_block(text: str) -> bool:
        """
        Check if text contains an incomplete <execute> block (opened but not closed).
        
        Returns:
            bool: True if there's an incomplete execute block
        """
        if not text:
            return False
        # Count opening and closing tags
        open_pattern = r'<execute\s+lang=["\']python["\']\s*>'
        close_pattern = r'</execute>'
        open_count = len(re.findall(open_pattern, text, re.IGNORECASE))
        close_count = len(re.findall(close_pattern, text, re.IGNORECASE))
        return open_count > close_count
    
    @staticmethod
    def _clean_response_text(text: str) -> str:
        """
        Clean response text by removing <execute> code blocks.
        使用字符串方法替代正则表达式。
        
        Args:
            text: Raw LLM response text that may contain <execute> blocks
            
        Returns:
            str: Cleaned text suitable for final display
        """
        if not text:
            return text
        # Remove <execute lang="python">...</execute> blocks
        pattern = r'<execute\s+lang=["\']python["\']\s*>.*?</execute>'
        cleaned = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)
        # Clean up excessive whitespace left behind
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with skills in XML format."""
        # Use XML format for skills (Claude Code style)
        skills_xml = self.skill_loader.build_skills_xml_prompt(self.user_id)
        
        system_prompt = f"""You are an intelligent agent designed to help users accomplish complex tasks by leveraging specific skill domains and external tools.

<capabilities>
You have access to the following tools for task execution:
1. **load_skill**: Load detailed documentation for a specific skill domain (Excel, PowerPoint, etc.).
2. **read_skill_file**: Read specific files (templates, logic, etc.) from a skill's directory.
3. **list_skill_tree**: List all files within a skill directory to understand available resources.
4. **execute_code**: Execute Python code for computation, file processing, or MCP tool calls. Note: The code is extracted from your latest <execute> block.
5. **list_mcp_tools**: Discover available MCP tools for connecting to external services.
</capabilities>

{skills_xml}

<environment_and_paths>
Your code runs in a backend environment with a fixed file structure.
- **Working Directory**: The root of the backend.
  - `skills/`: Contains internal skill resources and helper scripts. (READ-ONLY)
  - `scripts/`: Destination for all user-related files and outputs. (READ-WRITE)

- **Path Helpers (Pre-injected)**:
  - `user_file("filename")`: Use this for any file the user uploads or any output you generate. It points to the `scripts/` directory.
    - Don't define user_file yourself, it's already defined in the system, just call it directly, otherwise it will cause an error.
  - `skill_path("skill_name", "relative/path")`: Use this to reference internal skill resources (e.g., templates or JS scripts) inside the `skills/` directory.

**CRITICAL**: Strictly forbidden to create or modify any files within the `skills/` directory. All generated artifacts MUST use `user_file()`.
</environment_and_paths>

<python_execution_protocol>
All logic execution must follow these strict technical rules:

1. **Syntax**: [**CRITICAL**] Write code inside `<execute lang="python">...</execute>` tags, then **MUST** call `execute_code()` with no parameters.
2. **Independent Execution**: Each block runs as a FRESH Python script. 
   - Variables, DataFrames, and objects **DO NOT persist** between blocks.
   - Every block must be **FULLY self-contained**: include all imports, re-read files, and define all necessary logic.
3. **MCP Integration (Async)**:
   - Call MCP tools using: `await call_tool("tool_name", {{"arg1": value1}})`.
   - Use `asyncio.run(main())` pattern for all async code execution.
   - Use `await list_mcp_tools()` to discover available external capabilities.
4. **Execution Trigger**: Each `execute_code()` call only runs the **MOST RECENT** <execute> block in your response.
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
1. **Analyze**: Identify if the task is a simple question, a domain-specific task (Skill), or requires external data (MCP).
2. **Initialize**: For domain tasks, use `load_skill` first to get guidance.
3. **Plan & Act**: For any task producing artifacts (PPT, Excel, etc.), you MUST use `execute_code`. Describing the process is insufficient; the user needs the physical file output.
4. **Recover**: If an error occurs, analyze the traceback, adjust your logic, and provide a corrected `<execute>` block immediately.
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
    
    def _create_agent_context(self, session_id: str) -> AgentContext:
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
    
    async def run(
        self,
        user_message: str,
        file_urls: List[str] = None,
        file_names: List[str] = None,
        session_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run the agent loop for a user request using Runner.run_streamed().
        
        This is a generator that yields events as the agent processes the request.
        
        Args:
            user_message: User's input message
            file_urls: Optional list of file URLs (for display/download)
            file_names: Optional list of uploaded file names (e.g. ['9120.xlsx'])
            session_id: Optional session ID
            
        Yields:
            Events dict with type and content
        """
        session_id = session_id or str(uuid.uuid4())[:8]
        
        logger.debug(f"[Agent DEBUG] file_urls: {file_urls}")
        logger.debug(f"[Agent DEBUG] file_names: {file_names}")
        
        # Build initial user message with file context
        full_user_message = user_message
        
        if file_names:
            full_user_message += "\n\n## User Uploaded Files:\n"
            full_user_message += "You must access these files using `user_file('filename')`:\n"
            for name in file_names:
                full_user_message += f"- {name}\n"
        elif file_urls:
            full_user_message += "\n\n## User Uploaded Files:\n"
            full_user_message += "You must access these files using `user_file('filename')`:\n"
            for url in file_urls:
                filename = url.split("/")[-1]
                full_user_message += f"- {filename}\n"
        
        yield {"type": "status", "content": "Processing your request..."}
        
        # Create agent context
        agent_context = self._create_agent_context(session_id)
        
        # Build input messages from history + current message
        input_messages: List[TResponseInputItem] = []
        
        # Add history messages
        for msg in self.history_messages:
            if msg["role"] == "user":
                input_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                input_messages.append({"role": "assistant", "content": msg["content"]})
        
        # Add current user message
        input_messages.append({"role": "user", "content": full_user_message})
        
        # Create agent with tools
        agent = Agent(
            name="SkillAgent",
            instructions=self._build_system_prompt(),
            tools=SKILL_TOOLS,
            model=DEFAULT_MODEL,
        )
        
        if DEFAULT_MODEL.lower().find("claude") != -1:
            agent.model = OpenAIChatCompletionsModel(DEFAULT_MODEL, openai_client=custom_openai_client)
            agent.model_settings = ModelSettings(
                max_tokens=32768,
            )
        
        # Configure run
        run_config = RunConfig()
        
        try:
            # Run with streaming
            result = Runner.run_streamed(
                agent,
                input=input_messages,
                context=agent_context,
                run_config=run_config,
                max_turns=self.max_tool_calls,
            )
            
            current_response_text = ""
            final_output = None
            
            async for event in result.stream_events():
                # Handle different event types
                if isinstance(event, RawResponsesStreamEvent):
                    # Streaming text from LLM
                    # Log event type for debugging
                    event_type_name = type(event.data).__name__ if event.data else "None"
                    logger.debug(f"[{session_id}] RawResponsesStreamEvent: {event_type_name}")
                    
                    # Check if event.data has delta attribute (ResponseTextDeltaEvent has it as a string)
                    if event.data and hasattr(event.data, 'delta') and event.data.delta:
                        delta = event.data.delta
                        # delta can be a string directly (ResponseTextDeltaEvent) 
                        # or an object with content attribute (ResponseDeltaEvent)
                        content_text = ""
                        if isinstance(delta, str):
                            content_text = delta
                        elif hasattr(delta, 'content') and delta.content:
                            if isinstance(delta.content, str):
                                content_text = delta.content
                            elif isinstance(delta.content, list):
                                for part in delta.content:
                                    if hasattr(part, 'text'):
                                        content_text += part.text
                                    elif isinstance(part, dict) and 'text' in part:
                                        content_text += part['text']
                                    elif isinstance(part, str):
                                        content_text += part
                        
                        if content_text:
                            current_response_text += content_text
                            
                            # Extract <execute> blocks from accumulated response
                            execute_blocks = self._extract_execute_blocks(current_response_text)
                            
                            # Add newly found blocks to queue (avoid duplicates)
                            existing_count = len(agent_context.pending_code_queue)
                            new_blocks = execute_blocks[existing_count:]
                            if new_blocks:
                                # 只在发现新 block 时才打印日志
                                logger.debug(f"[{session_id}] Found {len(new_blocks)} new execute block(s)")
                                for block in new_blocks:
                                    agent_context.pending_code_queue.append(block)
                                    logger.info(f"[{session_id}] Extracted execute block #{len(agent_context.pending_code_queue)}, length: {len(block)} chars")
                            
                            yield {
                                "type": "response_delta",
                                "content": content_text,
                                "accumulated": current_response_text
                            }
                
                elif isinstance(event, RunItemStreamEvent):
                    item = event.item
                    
                    if isinstance(item, ToolCallItem):
                        # ToolCallItem has data in raw_item (ResponseFunctionToolCall)
                        raw = item.raw_item
                        tool_name = getattr(raw, 'name', None)
                        tool_args_raw = getattr(raw, 'arguments', None)
                        call_id = getattr(raw, 'call_id', None)
                        
                        # Log raw arguments for debugging
                        logger.info(f"[{session_id}] Tool call: {tool_name}")
                        logger.debug(f"[{session_id}] Raw arguments type: {type(tool_args_raw)}, value: {repr(tool_args_raw)[:500]}")
                        
                        # Parse arguments if string
                        tool_args = tool_args_raw
                        if isinstance(tool_args, str):
                            try:
                                tool_args = json.loads(tool_args)
                            except Exception as e:
                                logger.warning(f"[{session_id}] Failed to parse tool args: {e}, raw: {repr(tool_args_raw)[:200]}")
                                tool_args = {"raw": tool_args}
                        
                        # Note: execute_code工具现在支持两种方式：
                        # 1. Method 1 (Direct): 直接传递code参数
                        # 2. Method 2 (Legacy): 从pending_code_queue获取
                        # 工具本身会处理这两种情况，不需要在这里强制覆盖
                        
                        yield {
                            "type": "tool_call",
                            "name": tool_name,
                            "arguments": tool_args,
                            "call_id": call_id
                        }
                    
                        
                        # Special handling for load_skill
                        if tool_name == "load_skill" and tool_args:
                            yield {
                                "type": "status",
                                "content": f"Loading skill: {tool_args.get('skill_name', 'unknown')}"
                            }
                    
                    elif isinstance(item, ToolCallOutputItem):
                        # Tool execution completed - data is also in raw_item
                        raw = item.raw_item
                        tool_result = item.output
                        
                        yield {
                            "type": "tool_result",
                            "name": getattr(raw, 'name', 'unknown') if raw else 'unknown',
                            "result": tool_result,
                            "call_id": getattr(raw, 'call_id', None) if raw else None
                        }
                        
                        # 解析结构化工具返回值（JSON 格式，无需正则）
                        tool_data = self._parse_tool_json(tool_result)
                        if tool_data:
                            tool_type = tool_data.get("__tool__")
                            
                            if tool_type == "execute_code":
                                # execute_code 返回的结构化数据
                                yield {
                                    "type": "execution_result",
                                    "status": tool_data.get("status"),  # 直接使用，不设默认值
                                    "stdout": tool_data.get("stdout", ""),
                                    "stderr": tool_data.get("stderr", ""),
                                    "result": tool_data.get("result"),
                                    "output_files": tool_data.get("output_files", [])
                                }
                            
                            elif tool_type == "load_skill":
                                # load_skill 返回的结构化数据
                                if tool_data.get("status") == "success":
                                    yield {
                                        "type": "skill_loaded",
                                        "skill_name": tool_data.get("skill_name")
                                    }
                    
                    elif isinstance(item, MessageOutputItem):
                        # Final message from agent
                        if hasattr(item, 'content') and item.content:
                            for content_part in item.content:
                                if hasattr(content_part, 'text'):
                                    final_output = content_part.text
                                    # Clean the response content to remove <execute> blocks
                                    clean_content = self._clean_response_text(final_output)
                                    if clean_content:  # Only yield if there's content after cleaning
                                        yield {
                                            "type": "response",
                                            "content": clean_content
                                        }
                
                elif isinstance(event, AgentUpdatedStreamEvent):
                    # Agent status update
                    yield {
                        "type": "status",
                        "content": f"Agent processing..."
                    }
            
            # Get final result - final_output is a property, not a method
            final_result = result.final_output
            
            # Debug: Log accumulated text vs final_result
            logger.debug(f"[{session_id}] Stream ended. current_response_text length: {len(current_response_text)}, "
                        f"final_result length: {len(final_result) if final_result else 0}")
            if current_response_text and final_result:
                if len(current_response_text) != len(final_result):
                    logger.warning(f"[{session_id}] Length mismatch! "
                                  f"current_response_text: {len(current_response_text)}, "
                                  f"final_result: {len(final_result)}")
            
            # Check for incomplete execute blocks (stream may have been truncated)
            raw_answer = final_result or current_response_text
            if self._has_incomplete_execute_block(raw_answer):
                logger.warning(f"[{session_id}] Detected incomplete <execute> block in response! "
                              f"Response length: {len(raw_answer)} chars. "
                              f"Last 200 chars: {raw_answer[-200:] if len(raw_answer) > 200 else raw_answer}")
                # Yield a warning to frontend
                yield {
                    "type": "status",
                    "content": "⚠️ 检测到响应可能被截断，代码块可能不完整"
                }
            
            # Clean the response text to remove <execute> code blocks for display
            # The code blocks are internal implementation details, not user-facing content
            clean_answer = self._clean_response_text(raw_answer)
            
            yield {
                "type": "final_result",
                "status": "success",
                "result": {"answer": clean_answer}
            }
            
        except Exception as e:
            logger.error(f"[Agent] Error: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}
            yield {
                "type": "final_result",
                "status": "error",
                "result": {"error": str(e)}
            }
    
    def _parse_tool_json(self, result_text: str) -> Optional[Dict[str, Any]]:
        """
        解析工具返回的 JSON 数据。
        
        工具现在返回结构化 JSON，不再需要正则匹配。
        如果解析失败，返回 None（不隐藏错误）。
        """
        if not result_text:
            return None
        
        # 尝试直接解析 JSON
        result_str = str(result_text).strip()
        if result_str.startswith("{"):
            parsed = json.loads(result_str)  # 不捕获异常，让错误暴露
            return parsed
        
        return None


async def run_agent(
    user_message: str,
    file_urls: List[str] = None,
    session_id: str = None,
    user_id: int = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function to run the agent.
    
    Args:
        user_message: User's input
        file_urls: Optional file URLs
        session_id: Optional session ID
        user_id: Optional user ID for isolation
        
    Yields:
        Agent events
    """
    agent = SkillAgent(user_id=user_id)
    async for event in agent.run(
        user_message=user_message,
        file_urls=file_urls,
        file_names=None,
        session_id=session_id
    ):
        yield event
