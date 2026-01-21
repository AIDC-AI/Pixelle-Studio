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
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass

from openai import AsyncOpenAI

from agents import RunContextWrapper
from agents.tool_context import ToolContext
from agents.usage import Usage

from app.skills.loader import get_skill_loader
from app.tools import (
    AgentContext,
    load_skill,
    read_skill_file,
    list_skill_tree,
    execute_code,
    list_mcp_tools,
    final_answer,
    SKILL_TOOLS,
)
from app.utils.network import LOCAL_IP, SERVER_PORT

from app.llm_adapter import DEFAULT_MODEL

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# OpenAI client will be initialized per-request

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
    def _clean_response_text(text: str) -> str:
        """
        Clean response text by removing <execute> code blocks.
        This is used to generate a clean final answer without code details.
        
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
        
        system_prompt = f"""You are an intelligent agent that helps users accomplish tasks.

<capabilities>
You have access to the following tools:

1. **load_skill**: Load detailed documentation for a specific skill domain (Excel, PowerPoint, etc.)
2. **read_skill_file**: Read specific files from a skill's directory
3. **list_skill_tree**: List all files in a skill directory
4. **execute_code**: Execute Python code for computation, file processing, or MCP tool calls
5. **list_mcp_tools**: Discover available MCP tools for external services
6. **final_answer**: Submit the final answer when the task is fully completed (REQUIRED to end)

Use these tools to help users accomplish their tasks effectively.
</capabilities>

{skills_xml}

<code_execution_rules>
**How to Execute Python Code**:

1. Write code in `<execute lang="python">...</execute>` tags
2. Call `execute_code()` with NO parameters - code is extracted automatically

**Example**:
```
I'll create the HTML files:

<execute lang="python">
import json
import os

html_content = '''<!DOCTYPE html>
<html><body><h1>Hello</h1></body></html>'''

with open(script_path("output.html"), "w") as f:
    f.write(html_content)

print(json.dumps({{"status": "success", "result": "File created"}}))
</execute>
```

Then call: execute_code()

**Rules**:
- **CRITICAL: Each execute block runs as an INDEPENDENT Python script**
- Variables, DataFrames, and objects DO NOT persist between execute blocks
- Every execute block MUST be FULLY self-contained:
  - Include ALL imports (pandas, json, etc.)
  - Re-read input files if needed (e.g., `df = pd.read_csv(script_path('file.csv'))`)
  - Include ALL processing logic
- If you need to both analyze AND generate output, put ALL code in ONE execute block
- Always print JSON result at the end
- **Each execute_code() call runs the MOST RECENT (last) <execute> block in your response**

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
**CRITICAL**: You MUST strictly follow the loaded skill's documentation!

When a skill is loaded:
1. **Read ALL referenced docs FIRST**: If SKILL.md says "Read X.md completely", you MUST read it BEFORE writing any code
2. **EXTRACT CONSTRAINTS BEFORE CODING**: After reading docs, identify ALL "CRITICAL", "NEVER", "ALWAYS", "MUST" rules. List them mentally and OBEY them
3. **Follow the EXACT workflow**: Execute steps in the exact order specified. Do not skip steps or reorder
4. **Do NOT improvise**: Your assumptions may be wrong. The skill doc knows the correct approach

**WARNING**: Common failure mode is reading docs but ignoring constraints. Do NOT do this - every "CRITICAL" or "NEVER" rule exists for a reason.
</skill_usage>

<decision_flow>
When helping users:

1. **Simple Questions**: Answer directly, then call `final_answer` to complete
2. **Domain Tasks**: First use `load_skill` to get guidance, then `execute_code` to accomplish the task
3. **File Processing**: Use `execute_code` with appropriate libraries
4. **External Services**: Use `list_mcp_tools` to discover tools, then `execute_code` with `call_tool()`
5. **Errors**: Analyze the error, adjust your approach, and try again

**IMPORTANT**: For any task that produces files (PPT, Excel, images, etc.), you MUST call execute_code to actually generate the files. Just describing or showing code is NOT enough - the user needs the actual output files!
</decision_flow>

<completion_rules>
**CRITICAL: How to Complete Tasks**

1. You MUST call `final_answer` tool to submit your final answer when done
2. NEVER end your response without a tool call - always either:
   - Call a tool to continue working, OR
   - Call `final_answer` to complete the task
3. If code execution returns unexpected results (e.g., 0 records found when expecting some), 
   analyze and fix the issue before calling `final_answer`
4. Verify your results are correct before submitting the final answer
5. The `final_answer` tool is the ONLY way to properly end a task

**Examples of when to continue vs. when to finish:**
- Code returns error → Fix and retry (DO NOT call final_answer)
- Results look wrong or empty → Investigate and fix (DO NOT call final_answer)
- Task completed successfully with correct results → Call final_answer
</completion_rules>
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
    
    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Convert SKILL_TOOLS (FunctionTool objects) to OpenAI function schemas."""
        schemas = []
        for tool in SKILL_TOOLS:
            # FunctionTool objects have name, description, and params_json_schema attributes
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or f"Tool: {tool.name}",
                    "parameters": tool.params_json_schema
                }
            }
            schemas.append(schema)
        
        return schemas
    
    async def _execute_tool(
        self, 
        tool_name: str, 
        tool_args: Dict[str, Any], 
        agent_context: AgentContext
    ) -> str:
        """Execute a tool by name and return the result."""
        # Find the tool (FunctionTool object)
        tool_map = {
            "load_skill": load_skill,
            "read_skill_file": read_skill_file,
            "list_skill_tree": list_skill_tree,
            "execute_code": execute_code,
            "list_mcp_tools": list_mcp_tools,
            "final_answer": final_answer,
        }
        
        tool_func = tool_map.get(tool_name)
        if not tool_func:
            return f"Error: Unknown tool '{tool_name}'"
        
        try:
            # Create ToolContext for proper FunctionTool invocation
            tool_ctx = ToolContext(
                context=agent_context,
                usage=Usage(),
                tool_name=tool_name,
                tool_call_id=str(uuid.uuid4()),
                tool_arguments=json.dumps(tool_args)
            )
            
            # Call the tool using on_invoke_tool method
            result = await tool_func.on_invoke_tool(tool_ctx, json.dumps(tool_args))
            return result
        except Exception as e:
            logger.error(f"[Tool] Error executing {tool_name}: {e}", exc_info=True)
            return f"Error executing {tool_name}: {str(e)}"

    async def run(
        self,
        user_message: str,
        file_urls: List[str] = None,
        file_names: List[str] = None,
        session_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run the agent loop for a user request using custom orchestrator.
        
        This implements a custom Agent Loop that:
        1. Only terminates when final_answer tool is called
        2. Injects continue prompts if LLM responds without tool calls
        3. Gives full control over the termination condition
        
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
        
        # Build messages list for OpenAI API
        messages: List[Dict[str, Any]] = []
        
        # Add system prompt
        messages.append({"role": "system", "content": self._build_system_prompt()})
        
        # Add history messages
        for msg in self.history_messages:
            if msg["role"] == "user":
                messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                messages.append({"role": "assistant", "content": msg["content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": full_user_message})
        
        # Get tool schemas
        tools = self._get_tool_schemas()
        
        # Initialize OpenAI client
        client = AsyncOpenAI()
        
        step_count = 0
        no_tool_call_count = 0  # Track consecutive responses without tool calls
        max_no_tool_calls = 3  # Max retries before giving up
        final_answer_content = ""
        
        try:
            # Custom Agent Loop - continues until task_completed or max steps
            while not agent_context.task_completed and step_count < self.max_tool_calls:
                step_count += 1
                logger.info(f"[{session_id}] Agent loop step {step_count}/{self.max_tool_calls}")
                
                yield {"type": "status", "content": f"Processing step {step_count}..."}
                
                # Call LLM with streaming
                current_response_text = ""
                tool_calls_data = []  # Accumulate tool calls from stream
                current_tool_call = None
                
                response = await client.chat.completions.create(
                    model=DEFAULT_MODEL,
                    messages=messages,
                    tools=tools,
                    stream=True,
                    max_completion_tokens=32768,
                    max_tokens=16384,
                )
                
                async for chunk in response:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if not delta:
                        continue
                    
                    # Handle content streaming
                    if delta.content:
                        current_response_text += delta.content
                        
                        # Extract <execute> blocks from accumulated response
                        execute_blocks = self._extract_execute_blocks(current_response_text)
                        
                        # Add newly found blocks to queue
                        existing_count = len(agent_context.pending_code_queue)
                        for block in execute_blocks[existing_count:]:
                            agent_context.pending_code_queue.append(block)
                            logger.info(f"[{session_id}] Extracted execute block #{len(agent_context.pending_code_queue)}, length: {len(block)} chars")
                        
                        yield {
                            "type": "response_delta",
                            "content": delta.content,
                            "accumulated": current_response_text
                        }
                    
                    # Handle tool calls streaming
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            if tc.index is not None:
                                try:
                                    idx = int(tc.index)  # Ensure it's an integer
                                    
                                    # Handle negative indices (some APIs return -1 for all chunks)
                                    if idx < 0:
                                        if idx == -1:
                                            # -1 means: append to last tool call, or create first one
                                            # If we have an id, it's a new tool call; otherwise append to existing
                                            if tc.id and tc.id.strip():
                                                # New tool call with id - append to list
                                                idx = len(tool_calls_data)
                                            else:
                                                # Continuation of existing tool call - use last index
                                                idx = max(0, len(tool_calls_data) - 1)
                                        else:
                                            continue  # Skip other negative indices
                                    
                                    # Ensure we have enough slots
                                    while len(tool_calls_data) <= idx:
                                        tool_calls_data.append({
                                            "id": None,
                                            "name": "",
                                            "arguments": ""
                                        })
                                    
                                    if tc.id:
                                        tool_calls_data[idx]["id"] = tc.id
                                    if tc.function:
                                        if tc.function.name:
                                            tool_calls_data[idx]["name"] = tc.function.name
                                        if tc.function.arguments:
                                            tool_calls_data[idx]["arguments"] += tc.function.arguments
                                except (ValueError, IndexError, TypeError) as e:
                                    logger.warning(f"[{session_id}] Error processing tool call at index {tc.index}: {e}")
                
                # Process the complete response
                finish_reason = chunk.choices[0].finish_reason if chunk.choices else None
                
                # Build assistant message for history
                # NOTE: We intentionally avoid using tool_calls field and tool role
                # because some API gateways don't fully support the OpenAI tool call protocol.
                # Instead, we use user role to inject tool results (more compatible).
                
                if tool_calls_data and tool_calls_data[0]["name"]:
                    # Reset no_tool_call counter
                    no_tool_call_count = 0
                    
                    # Build tool call description for assistant message
                    # This preserves the LLM's intent without using tool_calls protocol
                    tool_names = [tc["name"] for tc in tool_calls_data if tc["name"]]
                    assistant_content = current_response_text or ""
                    if not assistant_content.strip():
                        # If LLM only returned tool calls without text, add a description
                        assistant_content = f"[Calling tools: {', '.join(tool_names)}]"
                    
                    assistant_message = {"role": "assistant", "content": assistant_content}
                    messages.append(assistant_message)
                    
                    # Execute each tool call
                    for tc in tool_calls_data:
                        if not tc["name"]:
                            continue
                        
                        tool_name = tc["name"]
                        tool_call_id = tc["id"]
                        
                        # Parse arguments
                        try:
                            tool_args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                        except json.JSONDecodeError as e:
                            logger.warning(f"[{session_id}] Failed to parse tool args: {e}")
                            tool_args = {}
                        
                        # Special handling for execute_code - inject code from queue
                        if tool_name == "execute_code" and agent_context.pending_code_queue:
                            # Don't pass code arg - the tool will get it from queue
                            pass
                        
                        logger.info(f"[{session_id}] Tool call: {tool_name}")
                        
                        # Yield tool_call event for frontend
                        yield {
                            "type": "tool_call",
                            "name": tool_name,
                            "arguments": tool_args if tool_name != "execute_code" else {"code": agent_context.pending_code_queue[-1] if agent_context.pending_code_queue else ""},
                            "call_id": tool_call_id
                        }
                        
                        # Special status for load_skill
                        if tool_name == "load_skill" and tool_args:
                            yield {
                                "type": "status",
                                "content": f"Loading skill: {tool_args.get('skill_name', 'unknown')}"
                            }
                        
                        # Execute the tool
                        tool_result = await self._execute_tool(tool_name, tool_args, agent_context)
                        
                        logger.info(f"[{session_id}] Tool result: {tool_name}")
                        
                        # Yield tool_result event
                        yield {
                            "type": "tool_result",
                            "name": tool_name,
                            "result": tool_result,
                            "call_id": tool_call_id
                        }
                        
                        # Special handling for execute_code results
                        if tool_name == "execute_code" and "Execution Result" in str(tool_result):
                            try:
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
                        if tool_name == "load_skill" and "Skill '" in str(tool_result):
                            match = re.search(r"Skill '([^']+)' Documentation", str(tool_result))
                            if match:
                                yield {
                                    "type": "skill_loaded",
                                    "skill_name": match.group(1)
                                }
                        
                        # Check if final_answer was called
                        if tool_name == "final_answer":
                            final_answer_content = agent_context.final_answer_content
                            logger.info(f"[{session_id}] Task completed via final_answer")
                        
                        # Add tool result to messages using USER role (for API gateway compatibility)
                        # This avoids using "tool" role which some gateways don't support properly
                        tool_result_message = f"""[Tool Result: {tool_name}]

{tool_result}

Based on this result, either:
1. If the task is complete and results are correct, call `final_answer` with your summary
2. If there was an error or more work is needed, continue with the appropriate tool call"""
                        
                        messages.append({
                            "role": "user",
                            "content": tool_result_message
                        })
                
                else:
                    # No tool calls in response
                    no_tool_call_count += 1
                    
                    if current_response_text:
                        messages.append({"role": "assistant", "content": current_response_text})
                    
                    # If task not completed and no tool calls, inject a continue prompt
                    if not agent_context.task_completed and no_tool_call_count < max_no_tool_calls:
                        logger.info(f"[{session_id}] No tool call but task not completed, injecting continue prompt (attempt {no_tool_call_count})")
                        
                        continue_prompt = """[System] You haven't called the `final_answer` tool yet. 

If the task is complete and results are correct, call `final_answer` with your summary.
If there's more work to do or issues to fix, continue with the appropriate tool call.

Remember: You MUST call `final_answer` to properly complete the task."""
                        
                        messages.append({"role": "user", "content": continue_prompt})
                        
                        yield {
                            "type": "status",
                            "content": "Prompting agent to continue or finalize..."
                        }
                    elif no_tool_call_count >= max_no_tool_calls:
                        # Give up after max retries - force completion
                        logger.warning(f"[{session_id}] Max no-tool-call retries reached, forcing completion")
                        agent_context.task_completed = True
                        final_answer_content = current_response_text
            
            # Determine final answer
            if agent_context.final_answer_content:
                clean_answer = agent_context.final_answer_content
            else:
                # Fallback to last response text if no explicit final_answer
                clean_answer = self._clean_response_text(current_response_text) if current_response_text else "Task completed."
            
            logger.info(f"[{session_id}] Final: success")
            
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
