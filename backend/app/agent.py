"""
Skill Agent - Native OpenAI API implementation.

This agent uses direct OpenAI API calls (not Agents SDK) to:
1. Receive user input (text + optional files)
2. Stream LLM responses with tool calling support
3. Execute tools and continue the conversation loop
4. Support implicit code execution via <execute> blocks (Synthetic Tool Call)

Key features:
- Full control over message history format
- Synthetic Tool Call for implicit code execution
- Streaming support for real-time output
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

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# LLM Configuration
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "300"))
# Max tokens for LLM output - important for Bedrock/Claude which may have low defaults
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "16384"))

logging.info(f"DEFAULT_MODEL: {DEFAULT_MODEL}")
logging.info(f"LLM_TIMEOUT: {LLM_TIMEOUT}s")
logging.info(f"LLM_MAX_TOKENS: {LLM_MAX_TOKENS}")


class SkillAgent:
    """
    Agent that handles user requests using native OpenAI API.
    
    Features:
    - Direct OpenAI API calls (no SDK abstraction)
    - Full control over message history
    - Synthetic Tool Call for implicit code execution
    - Streaming response support
    """
    
    def __init__(
        self, 
        max_turns: int = 20, 
        history_messages: Optional[List[Dict[str, str]]] = None,
        mcp_server_url: Optional[str] = None,
        mcp_server_type: str = "sse",
        user_id: Optional[int] = None
    ):
        """
        Initialize the agent.
        
        Args:
            max_turns: Maximum number of conversation turns (safety limit)
            history_messages: Previous conversation history
            mcp_server_url: URL of the MCP server for tool calls
            mcp_server_type: Type of MCP server ("sse" or "http")
            user_id: User ID for isolation and personalization
        """
        self.client = AsyncOpenAI(timeout=LLM_TIMEOUT)
        self.model = DEFAULT_MODEL
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
  - `user_file("filename")`: Use this for any file the user uploads or any output you generate. It points to the `scripts/` directory.
    - [CRITICAL!]Don't define user_file yourself, it's already defined in the system, you should call it directly!
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
1. **Analyze**: Identify if the task is a simple question, a domain-specific task (Skill), or requires external data (MCP).
2. **Initialize**: For domain tasks, use `load_skill` first to get guidance.
3. **Plan & Act**: For any task producing artifacts (PPT, Excel, etc.), write the Python code in `<execute>` tags.
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
        file_urls: List[str] = None,
        file_names: List[str] = None,
        session_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run the agent loop for a user request.
        
        This implements:
        1. Build messages with history + current user message
        2. Call OpenAI API with streaming
        3. Process tool calls (both explicit and Synthetic)
        4. Continue loop until no more tool calls
        """
        session_id = session_id or str(uuid.uuid4())[:8]
        
        logger.info(f"[Agent] Starting session {session_id}")
        logger.debug(f"[Agent] file_urls: {file_urls}, file_names: {file_names}")
        
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
        
        # Create context
        context = self._create_context(session_id)
        
        # Build messages
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self._build_system_prompt()}
        ]
        
        # Add history
        for msg in self.history_messages:
            if msg["role"] in ["user", "assistant"]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": full_user_message})
        
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
                # Call OpenAI API with streaming
                # max_tokens is important to prevent truncation, especially for Bedrock/Claude
                if "claude" in self.model.lower():
                    response_stream = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=TOOL_SCHEMAS if TOOL_SCHEMAS else None,
                        stream=True,
                        max_tokens=LLM_MAX_TOKENS
                    )
                else:
                    response_stream = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=TOOL_SCHEMAS if TOOL_SCHEMAS else None,
                        stream=True,
                    )
                
                # Process stream
                final_content = ""
                tool_calls_accumulator: Dict[int, Dict] = {}
                
                async for chunk in response_stream:
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
    file_urls: List[str] = None,
    session_id: str = None,
    user_id: int = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function to run the agent.
    """
    agent = SkillAgent(user_id=user_id)
    async for event in agent.run(
        user_message=user_message,
        file_urls=file_urls,
        file_names=None,
        session_id=session_id
    ):
        yield event
