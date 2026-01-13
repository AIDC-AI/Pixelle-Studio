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
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass

from agents import Agent, Runner
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
        max_tool_calls: int = 10, 
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
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with skills in XML format."""
        # Use XML format for skills (Claude Code style)
        skills_xml = self.skill_loader.build_skills_xml_prompt(self.user_id)
        
        system_prompt = f"""You are an intelligent agent that helps users accomplish tasks.

<capabilities>
You have access to the following tools:

1. **load_skill**: Load detailed documentation for a specific skill domain (Excel, PowerPoint, etc.)
2. **read_skill_file**: Read specific files from a skill's directory
3. **list_skill_tree**: List all files in a skill directory
4. **execute_code**: Execute Python code for computation, file processing, or MCP tool calls
5. **list_mcp_tools**: Discover available MCP tools for external services

Use these tools to help users accomplish their tasks effectively.
</capabilities>

{skills_xml}

<code_execution_rules>
When using the execute_code tool:

1. **Self-contained**: The script must be executable on its own
2. **Output**: Use `print()` for output you want to see
3. **Final Result**: Print a JSON object with required keys

<pre_injected_helpers>
The following helper functions are automatically available in your Python code:

**File Path Helpers:**
- `skill_path("skill_name", "relative/path")` - Get path to skill resources
- `script_path("filename")` - Get path to user files in scripts/ directory

**MCP Tool Calling (async):**
- `await call_tool("tool_name", {{"arg1": value1, ...}})` - Call an MCP tool
- `await list_mcp_tools()` - Discover all available MCP tools
- Use `asyncio.run(main())` pattern for async code

Example:
```python
import asyncio
import json

async def main():
    result = await call_tool('some_tool', {{'input': 'value'}})
    print(json.dumps({{"status": "success", "result": result}}))

asyncio.run(main())
```
</pre_injected_helpers>

<working_directory>
Your code runs with working directory at backend root. Key directories:
- `skills/` - Skill resources and helper scripts
- `scripts/` - User files and output files
</working_directory>

<file_rules>
**CRITICAL**: File paths are dynamic based on user context.
- **NEVER** use hardcoded paths like `scripts/filename.ext`.
- **ALWAYS** use `script_path("filename.ext")` to access input files and write output files.
- **output_file_names**: List only the filename (NOT the path), e.g., `["output.pptx"]`
</file_rules>

<output_format>
Always end your code with a JSON status output:
```python
print(json.dumps({{
    "status": "success",  # or "error"
    "result": "Description of what was done",
    "output_file_names": ["file.ext"]  # Optional: only filenames, not paths
}}))
```
</output_format>
</code_execution_rules>

<skill_usage>
**IMPORTANT**: When a skill is loaded, follow its documentation exactly!

1. Read the skill's SKILL.md carefully - it contains the correct implementation pattern
2. Different skills have different execution modes:
   - Some skills use MCP tool calling (e.g., call_tool())
   - Some skills use local scripts (subprocess with skill_path())
   - Some skills use Python libraries directly
3. Follow the skill's "Implementation Pattern" or "Basic Workflow" section
4. Do NOT assume a skill needs Node.js or local scripts unless the skill explicitly says so
</skill_usage>

<decision_flow>
When helping users:

1. **Simple Questions**: Answer directly without tools
2. **Domain Tasks**: First use `load_skill` to get guidance, then `execute_code`
3. **File Processing**: Use `execute_code` with appropriate libraries
4. **External Services**: Use `list_mcp_tools` to discover tools, then `execute_code` with `call_tool()`
5. **Errors**: Analyze the error, adjust your approach, and try again
</decision_flow>
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
            full_user_message += "You must access these files using `script_path('filename')`:\n"
            for name in file_names:
                full_user_message += f"- {name}\n"
        elif file_urls:
            full_user_message += "\n\n## User Uploaded Files:\n"
            full_user_message += "You must access these files using `script_path('filename')`:\n"
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
        
        # Configure run
        run_config = RunConfig(
            # max_turns=self.max_tool_calls,
        )
        
        try:
            # Run with streaming
            result = Runner.run_streamed(
                agent,
                input=input_messages,
                context=agent_context,
                run_config=run_config,
            )
            
            current_response_text = ""
            final_output = None
            
            async for event in result.stream_events():
                # Handle different event types
                if isinstance(event, RawResponsesStreamEvent):
                    # Streaming text from LLM
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
                        
                        # Check for empty execute_code arguments (common model issue)
                        if tool_name == "execute_code":
                            if not tool_args or not tool_args.get("code"):
                                logger.warning(f"[{session_id}] execute_code called with empty/missing code parameter. Raw args: {repr(tool_args_raw)[:200]}")
                        
                        yield {
                            "type": "tool_call",
                            "name": tool_name,
                            "arguments": tool_args,
                            "call_id": call_id
                        }
                        
                        # Special handling for execute_code - emit code event
                        if tool_name == "execute_code" and tool_args and tool_args.get("code"):
                            yield {
                                "type": "code",
                                "content": tool_args["code"],
                                "execution_count": agent_context.tool_call_count + 1
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
                        
                        # Special handling for execute_code results
                        if "Execution Result" in str(tool_result):
                            # Parse execution result for frontend
                            try:
                                # Extract status, stdout, stderr from the formatted result
                                result_data = self._parse_execution_result(tool_result)
                                if result_data:
                                    yield {
                                        "type": "execution_result",
                                        "status": result_data.get("status", "success"),
                                        "stdout": result_data.get("stdout", ""),
                                        "stderr": result_data.get("stderr", ""),
                                        "result": result_data.get("result"),
                                        "output_files": result_data.get("output_files", [])
                                    }
                            except Exception as e:
                                logger.warning(f"Failed to parse execution result: {e}")
                        
                        # Special handling for load_skill results
                        if "Skill '" in str(tool_result) and "' Documentation" in str(tool_result):
                            # Extract skill name
                            import re
                            match = re.search(r"Skill '([^']+)' Documentation", str(tool_result))
                            if match:
                                yield {
                                    "type": "skill_loaded",
                                    "skill_name": match.group(1)
                                }
                    
                    elif isinstance(item, MessageOutputItem):
                        # Final message from agent
                        if hasattr(item, 'content') and item.content:
                            for content_part in item.content:
                                if hasattr(content_part, 'text'):
                                    final_output = content_part.text
                                    yield {
                                        "type": "response",
                                        "content": final_output
                                    }
                
                elif isinstance(event, AgentUpdatedStreamEvent):
                    # Agent status update
                    yield {
                        "type": "status",
                        "content": f"Agent processing..."
                    }
            
            # Get final result - final_output is a property, not a method
            final_result = result.final_output
            
            yield {
                "type": "final_result",
                "status": "success",
                "result": {"answer": final_result or current_response_text}
            }
            
        except Exception as e:
            logger.error(f"[Agent] Error: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}
            yield {
                "type": "final_result",
                "status": "error",
                "result": {"error": str(e)}
            }
    
    def _parse_execution_result(self, result_text: str) -> Optional[Dict[str, Any]]:
        """Parse the formatted execution result text back to structured data."""
        result = {
            "status": "success",
            "stdout": "",
            "stderr": "",
            "result": None,
            "output_files": []
        }
        
        # Extract status
        if "**Status**: error" in result_text:
            result["status"] = "error"
        
        # Extract stdout
        import re
        stdout_match = re.search(r'\*\*Output\*\*:\n```\n(.*?)\n```', result_text, re.DOTALL)
        if stdout_match:
            result["stdout"] = stdout_match.group(1)
        
        # Extract stderr
        stderr_match = re.search(r'\*\*Errors\*\*:\n```\n(.*?)\n```', result_text, re.DOTALL)
        if stderr_match:
            result["stderr"] = stderr_match.group(1)
        
        # Extract parsed result
        json_match = re.search(r'\*\*Parsed Result\*\*:\n```json\n(.*?)\n```', result_text, re.DOTALL)
        if json_match:
            try:
                result["result"] = json.loads(json_match.group(1))
            except:
                pass
        
        # Extract output files
        files_section = re.search(r'\*\*Generated Files\*\*:\n(.*?)(?:\n\n|\Z)', result_text, re.DOTALL)
        if files_section:
            file_matches = re.findall(r'\- \[([^\]]+)\]\(([^)]+)\) \((\d+) bytes\)', files_section.group(1))
            for name, url, size in file_matches:
                result["output_files"].append({
                    "file_name": name,
                    "file_url": url,
                    "file_size": int(size)
                })
        
        return result


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
