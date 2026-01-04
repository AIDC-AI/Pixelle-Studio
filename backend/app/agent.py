"""
Skill Agent - Single Agent loop for executing user requests with skill guidance.

This is a simplified agent that:
1. Receives user input (text + optional files)
2. Decides whether to answer directly or generate code
3. If code is generated, executes it and evaluates the result
4. Continues the loop until the task is complete

The agent uses SKILL.md files for domain-specific guidance, which include
error handling patterns and best practices.
"""

import os
import json
import uuid
import socket
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from openai import AsyncOpenAI
import httpx

from app.skills.loader import get_skill_loader
from app.execution.runner import run_script

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# LLM Configuration - Load from environment variables
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://aihubmix.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-4-5")


def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


LOCAL_IP = get_local_ip()
SERVER_PORT = 8001  # Default backend port


@dataclass
class AgentMessage:
    """A message in the agent conversation."""
    role: str  # "user", "assistant", "system", "tool_result"
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass 
class AgentAction:
    """An action decided by the agent."""
    action_type: str  # "respond", "execute_code", "read_skill", "read_skill_file", "list_skill_tree"
    content: str  # Response text or code content
    skill_name: Optional[str] = None
    file_path: Optional[str] = None  # For read_skill_file action

from langsmith import wrappers
class SkillAgent:
    """
    Single Agent that handles user requests with skill guidance.
    
    The agent maintains a conversation history and decides at each step:
    - Answer directly (for simple questions)
    - Generate and execute Python code (for tasks requiring computation)
    - Read a skill for detailed guidance
    
    The agent loop continues until the agent decides the task is complete.
    """
    
    def __init__(self, max_tool_calls: int = 10, history_messages: Optional[List[Dict[str, str]]] = None):
        """
        Initialize the agent.
        
        Args:
            max_tool_calls: Maximum number of code executions (safety limit)
        """
        # Configure client with longer timeout for large requests
        self.client = wrappers.wrap_openai(AsyncOpenAI(
            api_key=LLM_API_KEY, 
            base_url=LLM_BASE_URL,
            timeout=httpx.Timeout(300.0, connect=30.0),  # 5 min total, 30s connect
            max_retries=3,  # Auto-retry on connection errors
        ))
        self.skill_loader = get_skill_loader()
        self.max_tool_calls = max_tool_calls
        self.history_messages = history_messages or []
        
        # Conversation state
        self.messages: List[Dict[str, str]] = []
        self.tool_call_count = 0
        self.loaded_skills: Dict[str, str] = {}  # skill_name -> content
        
        # Script storage - put outside backend to avoid triggering file watcher
        self.script_dir = Path(__file__).parent.parent / "scripts"
        self.script_dir.mkdir(parents=True, exist_ok=True)
        
        # Backend root directory (contains both skills/ and scripts/)
        self.backend_root = Path(__file__).parent.parent
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with skills in XML format (Claude Code style)."""
        # Use XML format for skills (Claude Code style)
        skills_xml = self.skill_loader.build_skills_xml_prompt()
        
        system_prompt = f"""You are an intelligent agent that helps users accomplish tasks.

<capabilities>
You can help users in the following ways:

1. **Direct Response**: For simple questions, explanations, or information requests, respond directly with your answer.

2. **Code Execution**: For tasks requiring computation, file processing, or external operations:
   - Generate Python code wrapped in ```python and ``` markers
   - The code will be executed and you'll see the results
   - Based on results, decide if the task is complete or needs more work

3. **Skills**: You have access to specialized skills that provide domain-specific guidance and code patterns.
</capabilities>

{skills_xml}

<code_execution_rules>
When generating Python code:

1. **Format**: Wrap code in ```python and ``` markers
2. **Self-contained**: The script must be executable on its own
3. **Output**: Use `print()` for output you want to see
4. **Final Result**: Print a JSON object with required keys

<working_directory>
Your code runs with working directory at backend root. Two key directories:
- `skills/` - Skill resources (e.g., skills/pptx/scripts/html2pptx.js)
- `scripts/` - User files and output files (your Python scripts also run from here)

Helper functions are pre-injected in Python:
- `skill_path("pptx", "scripts/html2pptx.js")` -> "skills/pptx/scripts/html2pptx.js"
- `script_path("output.pptx")` -> "scripts/output.pptx"
</working_directory>

<file_rules>
- **Input files**: Read from `scripts/<filename>` (e.g., `scripts/data.xlsx`)
- **Output files**: Write to `scripts/<filename>` (e.g., `scripts/output.pptx`)
- **Skill scripts**: Access via `skill_path()` or direct path like `skills/pptx/scripts/...`
- **output_file_names**: List only the filename (NOT the path), e.g., `["output.pptx"]`
</file_rules>

<nodejs_rules>
When generating Node.js scripts saved to `scripts/` directory:
- Use `path.join(__dirname, '..', 'skills', ...)` to reference skill files
- Use `path.join(__dirname, 'filename')` to reference files in scripts/
- Example: `require(path.join(__dirname, '..', 'skills', 'pptx', 'scripts', 'html2pptx.js'))`
- NEVER use `./skills/...` - Node.js require() resolves relative to script file, not cwd
</nodejs_rules>

<pptx_html_rules>
When generating HTML for PowerPoint (html2pptx):
- **Backgrounds/borders/shadows**: ONLY on `<div>`, NEVER on `<h1>`-`<h6>`, `<p>`, `<ul>`, `<ol>`
  ✗ Wrong: `<h2 style="border-bottom: 3pt solid #fff;">`
  ✓ Right: `<div style="border-bottom: 3pt solid #fff;"><h2>Title</h2></div>`
- **No CSS gradients**: `linear-gradient`, `radial-gradient` don't work. Use solid colors.
- **Text must be in tags**: All text must be inside `<p>`, `<h1>`-`<h6>`, `<ul>`, `<ol>`. Text directly in `<div>` will be lost.
- **Web-safe fonts only**: Arial, Helvetica, Times New Roman, Georgia, Verdana, Tahoma
</pptx_html_rules>

<output_format_examples>
Example 1 - Without output files:
```python
import json
# ... your code ...
print(json.dumps({{"status": "success", "result": "任务完成的描述"}}))
```

Example 2 - With output files:
```python
import json
# ... your code that generates files ...
# Write to scripts/ directory
output_path = script_path("report.xlsx")  # -> "scripts/report.xlsx"
# ... save file to output_path ...
print(json.dumps({{
    "status": "success", 
    "result": "任务完成的描述",
    "output_file_names": ["report.xlsx"]  # Only filename, not full path
}}))
```
</output_format_examples>
</code_execution_rules>

<skill_usage>
When a skill is loaded:
- The skill's SKILL.md documentation will be added to context
- Use relative paths: `skills/<skill_name>/...`
- Follow the skill's patterns and error handling guidance

Example using skill scripts:
```python
# Python script in skill
subprocess.run(['python', skill_path('xlsx', 'recalc.py'), 'scripts/data.xlsx'])

# Node.js script in skill  
subprocess.run(['node', skill_path('pptx', 'scripts/html2pptx.js'), ...])
```
</skill_usage>

<decision_flow>
After seeing code execution results, decide your next action:

1. **Task Complete**: If successful and the user's request is fulfilled → Provide a final response summarizing what was done
2. **Error Occurred**: If there was an error → Analyze it, refer to loaded skill's error handling guidance if available, then generate corrected code
3. **Partial Success**: If more work is needed → Generate additional code to complete the task
4. **Need More Info**: If skill documentation would help → Load the relevant skill first
</decision_flow>
"""        
        return system_prompt
    
    def _parse_agent_response(self, response_text: str) -> AgentAction:
        """
        Parse the agent's response to determine the action.
        
        Supports the following text markers:
        - [LOAD_SKILL: name] - Load SKILL.md content
        - [READ_SKILL_FILE: name, path] - Read a specific file from skill directory
        - [LIST_SKILL_TREE: name] - List skill directory structure
        - ```python ... ``` - Execute Python code
        
        Returns:
            AgentAction with type and content
        """
        import re
        
        # Check for skill load request: [LOAD_SKILL: name]
        if "[LOAD_SKILL:" in response_text:
            match = re.search(r'\[LOAD_SKILL:\s*(\w+)\s*\]', response_text)
            if match:
                skill_name = match.group(1)
                return AgentAction(
                    action_type="read_skill",
                    content=response_text,
                    skill_name=skill_name
                )
        
        # Check for read skill file request: [READ_SKILL_FILE: name, path]
        if "[READ_SKILL_FILE:" in response_text:
            match = re.search(r'\[READ_SKILL_FILE:\s*(\w+)\s*,\s*([^\]]+)\]', response_text)
            if match:
                skill_name = match.group(1)
                file_path = match.group(2).strip()
                return AgentAction(
                    action_type="read_skill_file",
                    content=response_text,
                    skill_name=skill_name,
                    file_path=file_path
                )
        
        # Check for list skill tree request: [LIST_SKILL_TREE: name]
        if "[LIST_SKILL_TREE:" in response_text:
            match = re.search(r'\[LIST_SKILL_TREE:\s*(\w+)\s*\]', response_text)
            if match:
                skill_name = match.group(1)
                return AgentAction(
                    action_type="list_skill_tree",
                    content=response_text,
                    skill_name=skill_name
                )
        
        # Check for code block
        if "```python" in response_text:
            # Extract code
            code_start = response_text.find("```python") + 9
            code_end = response_text.find("```", code_start)
            if code_end > code_start:
                code = response_text[code_start:code_end].strip()
                return AgentAction(
                    action_type="execute_code",
                    content=code
                )
        
        # Default: direct response
        return AgentAction(
            action_type="respond",
            content=response_text
        )
    
    def _build_skill_helpers_code(self) -> str:
        """
        Build the skill_helpers module code to inject into execution environment.
        
        All paths are RELATIVE to the execution cwd (backend root).
        Two root directories: skills/ and scripts/
        """
        return '''
# === Skill Helpers (auto-injected) ===
# Working directory is backend root, containing: skills/ and scripts/

SKILLS_ROOT = "skills"
SCRIPTS_ROOT = "scripts"

def skill_path(skill_name: str, *parts) -> str:
    """Get relative path: skills/<skill_name>/[parts...]"""
    import os
    return os.path.join(SKILLS_ROOT, skill_name, *parts)

def script_path(*parts) -> str:
    """Get relative path: scripts/[parts...]"""
    import os
    return os.path.join(SCRIPTS_ROOT, *parts)
# === End Skill Helpers ===
'''

    async def _execute_code(self, code: str, session_id: str) -> Dict[str, Any]:
        """
        Execute Python code and return results.
        
        Args:
            code: Python code to execute
            session_id: Session ID for script naming
            
        Returns:
            Dict with execution results
        """
        # Build skill helpers injection (provides skill_path() and script_path())
        skill_helpers_code = self._build_skill_helpers_code()
        
        # Wrap code with proper structure
        wrapped_code = f'''import sys
import json
import os
import subprocess
from pathlib import Path
{skill_helpers_code}
{code}
'''
        
        # Save script to scripts/ directory
        script_name = f"{session_id}_{self.tool_call_count:02d}_{uuid.uuid4().hex[:6]}.py"
        script_file = self.script_dir / script_name
        script_file.write_text(wrapped_code)
        
        # Execute and collect output (cwd = backend root, so scripts/ and skills/ are both accessible)
        output_lines = []
        error_lines = []
        result = None
        status = "success"
        
        try:
            async for log in run_script(str(script_file), cwd=str(self.backend_root)):
                if log.get("stream") == "stdout":
                    content = log.get("content", "")
                    output_lines.append(content)
                    # Try to parse JSON result
                    if content.strip().startswith("{"):
                        try:
                            result = json.loads(content.strip())
                        except:
                            pass
                elif log.get("stream") == "stderr":
                    error_lines.append(log.get("content", ""))
                elif log.get("type") == "result":
                    if log.get("status") != "success":
                        status = "error"
        except Exception as e:
            status = "error"
            error_lines.append(str(e))
        
        return {
            "status": status,
            "stdout": "\n".join(output_lines),
            "stderr": "\n".join(error_lines),
            "result": result,
            "script_path": str(script_file)
        }
    
    
    async def run(
        self,
        user_message: str,
        file_urls: List[str] = None,
        file_names: List[str] = None,
        session_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run the agent loop for a user request.
        
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
        self.tool_call_count = 0
        
        # Debug: 打印收到的参数
        logger.debug(f"[Agent DEBUG] file_urls: {file_urls}")
        logger.debug(f"[Agent DEBUG] file_names: {file_names}")
        
        # Build initial user message with file context
        full_user_message = user_message
        
        # 使用 file_names，文件在 scripts/ 目录下
        if file_names:
            full_user_message += "\n\n## 用户上传的文件:\n"
            for name in file_names:
                full_user_message += f"- scripts/{name}\n"
        elif file_urls:
            # 兜底：如果只有 URL，从 URL 中解析文件名
            full_user_message += "\n\n## 用户上传的文件:\n"
            for url in file_urls:
                filename = url.split("/")[-1]
                full_user_message += f"- scripts/{filename}\n"
        
        # Initialize conversation
        # Start from persisted history (Cursor-like session memory)
        self.messages = list(self.history_messages)
        self.messages.append({"role": "user", "content": full_user_message})
        
        yield {"type": "status", "content": "Processing your request..."}
        
        # Track empty response retries to prevent silent empty replies (which break session memory)
        empty_response_retries = 0
        max_empty_retries = 3

        # Track connection retries separately from empty response retries
        connection_retries = 0
        max_connection_retries = 3

        # Agent loop
        while self.tool_call_count < self.max_tool_calls:
            # Get LLM response
            system_prompt = self._build_system_prompt()
            
            try:
                response = await self.client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *self.messages
                    ],
                    max_tokens=16384,  # Increased to handle large code generation
                )
                # Reset connection retry counter on successful request
                connection_retries = 0
                
                logger.debug(f"[Agent DEBUG] LLM 响应为, response: {response}")
                # Defensive: some gateways/models may return empty choices/content
                choices = getattr(response, "choices", None) or []
                if not choices:
                    logger.debug(f"[Agent DEBUG] LLM 返回了空的 choices, response: {response}")
                    empty_response_retries += 1
                    if empty_response_retries >= max_empty_retries:
                        logger.error(f"[Agent ERROR] LLM 返回了空的 choices，超过最大重试次数，返回错误")
                        yield {"type": "error", "content": "LLM 返回了空的 choices，请稍后重试或更换模型。"}
                        return
                    logger.debug(f"[Agent DEBUG] LLM 返回了空的 choices，重试次数: {empty_response_retries}")
                    continue

                msg = getattr(choices[0], "message", None)
                finish_reason = getattr(choices[0], "finish_reason", None)
                assistant_message = getattr(msg, "content", None)
                if isinstance(assistant_message, list):
                    # Normalize list-of-parts to string
                    parts = []
                    for p in assistant_message:
                        if isinstance(p, str):
                            parts.append(p)
                        elif isinstance(p, dict):
                            parts.append(p.get("text") or "")
                        else:
                            parts.append(str(p))
                    assistant_message = "".join(parts)

                if not assistant_message or not str(assistant_message).strip():
                    empty_response_retries += 1
                    if empty_response_retries >= max_empty_retries:
                        yield {"type": "error", "content": "LLM 返回了空响应，请重试。"}
                        return
                    # Use user role with clear marker for system feedback (OpenAI protocol compliance)
                    self.messages.append({
                        "role": "user",
                        "content": "[System Feedback] Your previous response was empty. Please continue the task: either provide the final answer or generate Python code."
                    })
                    continue

                # Reset retry counter on successful response
                empty_response_retries = 0
                
                # Handle truncated response (finish_reason='length')
                # If code block is incomplete, ask model to continue
                if finish_reason == 'length':
                    has_code_start = "```python" in assistant_message
                    has_code_end = assistant_message.count("```") >= 2  # At least open and close
                    
                    if has_code_start and not has_code_end:
                        # Code block was truncated - ask to continue
                        logger.warning("[Agent] Response truncated mid-code, asking to continue...")
                        self.messages.append({"role": "assistant", "content": assistant_message})
                        self.messages.append({
                            "role": "user",
                            "content": "[System Feedback] Your code was truncated due to length limit. Please continue from where you left off. Start with the remaining code (no need to repeat what you already wrote)."
                        })
                        continue
                
                self.messages.append({"role": "assistant", "content": assistant_message})
            
            except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException) as e:
                # Network/connection errors - retry with backoff
                connection_retries += 1
                logger.warning(f"[Agent] Connection error (attempt {connection_retries}/{max_connection_retries}): {e}")
                
                if connection_retries >= max_connection_retries:
                    yield {"type": "error", "content": f"网络连接失败，已重试 {max_connection_retries} 次。请检查网络后重试。错误: {str(e)}"}
                    return
                
                # Wait before retry (exponential backoff)
                wait_time = 2 ** connection_retries  # 2, 4, 8 seconds
                yield {"type": "status", "content": f"网络连接中断，{wait_time} 秒后重试..."}
                await asyncio.sleep(wait_time)
                continue
                
            except Exception as e:
                logger.error(f"[Agent] LLM error: {e}", exc_info=True)
                yield {"type": "error", "content": f"LLM error: {str(e)}"}
                return
            
            # Parse action
            action = self._parse_agent_response(assistant_message)
            
            if action.action_type == "respond":
                # Direct response - task complete
                yield {"type": "response", "content": action.content}
                yield {"type": "final_result", "status": "success", "result": {"answer": action.content}}
                return
            
            elif action.action_type == "read_skill":
                # Load skill's SKILL.md
                skill_name = action.skill_name
                yield {"type": "status", "content": f"Loading skill: {skill_name}"}
                
                skill_content = self.skill_loader.read_skill(skill_name)
                if skill_content:
                    self.loaded_skills[skill_name] = skill_content
                    
                    # Find referenced documents in SKILL.md
                    links = self.skill_loader.parse_skill_links(skill_name)
                    referenced_docs = [link.path for link in links if link.exists and link.path.endswith('.md')]
                    
                    # Build guidance message
                    guidance = f"[System Notification] Skill '{skill_name}' SKILL.md has been loaded.\n\n"
                    
                    if referenced_docs:
                        guidance += "**Important**: The SKILL.md references these detailed documentation files:\n"
                        for doc in referenced_docs[:5]:  # Limit to 5
                            guidance += f"- {doc}\n"
                        guidance += "\nFor file creation tasks, you should read the relevant detailed docs before generating code. "
                        guidance += f"Use `[READ_SKILL_FILE: {skill_name}, <filename>]` to read them.\n\n"
                        guidance += "Review the SKILL.md to understand which workflow applies to your task, then read the corresponding detailed documentation."
                    else:
                        guidance += "Please proceed with the task following the skill's guidance."
                    
                    self.messages.append({"role": "user", "content": guidance})
                    yield {"type": "skill_loaded", "skill_name": skill_name, "referenced_docs": referenced_docs}
                else:
                    self.messages.append({
                        "role": "user",
                        "content": f"[System Notification] Skill '{skill_name}' not found. Please proceed with the task using your general knowledge or try a different approach."
                    })
                
                # Continue loop to let agent use the skill
                continue
            
            elif action.action_type == "read_skill_file":
                # Read a specific file from skill directory
                skill_name = action.skill_name
                file_path = action.file_path
                yield {"type": "status", "content": f"Reading skill file: {skill_name}/{file_path}"}
                
                file_content = self.skill_loader.read_skill_file(skill_name, file_path)
                if file_content:
                    # Add file content to context
                    self.messages.append({
                        "role": "user",
                        "content": f"[System Notification] Content of '{skill_name}/{file_path}':\n\n```\n{file_content}\n```\n\nPlease proceed with the task using this information."
                    })
                    yield {"type": "skill_file_read", "skill_name": skill_name, "file_path": file_path}
                else:
                    self.messages.append({
                        "role": "user",
                        "content": f"[System Notification] File '{skill_name}/{file_path}' not found or not readable. Please check the path or try listing the skill tree first."
                    })
                
                continue
            
            elif action.action_type == "list_skill_tree":
                # List skill directory structure
                skill_name = action.skill_name
                yield {"type": "status", "content": f"Listing skill tree: {skill_name}"}
                
                tree = self.skill_loader.list_skill_tree(skill_name)
                if tree:
                    import json
                    tree_json = json.dumps(tree, indent=2, ensure_ascii=False)
                    self.messages.append({
                        "role": "user",
                        "content": f"[System Notification] Directory structure of skill '{skill_name}':\n\n```json\n{tree_json}\n```\n\nYou can read specific files using [READ_SKILL_FILE: {skill_name}, <path>]."
                    })
                    yield {"type": "skill_tree_listed", "skill_name": skill_name, "tree": tree}
                else:
                    self.messages.append({
                        "role": "user",
                        "content": f"[System Notification] Skill '{skill_name}' not found. Please check the skill name."
                    })
                
                continue
            
            elif action.action_type == "execute_code":
                # Execute code
                self.tool_call_count += 1
                
                yield {
                    "type": "code", 
                    "content": action.content,
                    "execution_count": self.tool_call_count
                }
                yield {"type": "status", "content": f"Executing code..."}
                
                # Execute
                exec_result = await self._execute_code(action.content, session_id)
                
                # Check if there are output files and generate URLs for them
                output_files = []
                if exec_result["result"] and isinstance(exec_result["result"], dict):
                    output_file_names = exec_result["result"].get("output_file_names", [])
                    if output_file_names:
                        for file_name in output_file_names:
                            # Check if file exists in script directory
                            file_path = self.script_dir / file_name
                            if file_path.exists():
                                # Generate LAN URL
                                file_url = f"http://{LOCAL_IP}:{SERVER_PORT}/f/{file_name}"
                                output_files.append({
                                    "file_name": file_name,
                                    "file_url": file_url,
                                    "file_size": file_path.stat().st_size
                                })
                
                exec_result_event = {
                    "type": "execution_result",
                    "status": exec_result["status"],
                    "stdout": exec_result["stdout"],
                    "stderr": exec_result["stderr"],
                    "result": exec_result["result"]
                }
                
                # Add output_files to the event if any
                if output_files:
                    exec_result_event["output_files"] = output_files
                
                yield exec_result_event
                
                # Add execution result to conversation
                # Use user role with clear marker for tool output (OpenAI protocol compliance)
                # Many agent frameworks (LangChain, AutoGPT) use this pattern
                result_message = f"""[Execution Result]
Status: {exec_result["status"]}

Stdout:
{exec_result["stdout"]}

{f"Stderr:{chr(10)}{exec_result['stderr']}" if exec_result["stderr"] else ""}

Based on this result, either:
1. If the task is complete, provide a final response to the user
2. If there was an error or more work is needed, generate additional code
"""
                self.messages.append({"role": "user", "content": result_message})
                
                # Check if we have a successful JSON result
                if exec_result["status"] == "success" and exec_result["result"]:
                    if exec_result["result"].get("status") == "success":
                        # Let agent decide if this is the final result
                        pass
                
                # Continue loop to let agent process result
                continue
        
        # Max tool calls reached
        yield {
            "type": "final_result",
            "status": "incomplete",
            "result": {"error": "Maximum execution limit reached"}
        }


async def run_agent(
    user_message: str,
    file_urls: List[str] = None,
    session_id: str = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function to run the agent.
    
    Args:
        user_message: User's input
        file_urls: Optional file URLs
        session_id: Optional session ID
        
    Yields:
        Agent events
    """
    agent = SkillAgent()
    async for event in agent.run(
        user_message=user_message,
        file_urls=file_urls,
        file_names=None,
        session_id=session_id
    ):
        yield event

