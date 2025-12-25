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


# LLM Configuration
LLM_BASE_URL = "https://REDACTED_BASE_URL_HOST/v1"
LLM_API_KEY = "REDACTED_API_KEY"
LLM_MODEL = "us.anthropic.claude-opus-4-20250514-v1:0"


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
        self.client = AsyncOpenAI(
            api_key=LLM_API_KEY, 
            base_url=LLM_BASE_URL,
            timeout=httpx.Timeout(300.0, connect=30.0),  # 5 min total, 30s connect
            max_retries=3,  # Auto-retry on connection errors
        )
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
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with skills metadata."""
        # Use enhanced prompt that includes related docs info
        skills_meta = self.skill_loader.build_skills_meta_prompt_enhanced()
        
        system_prompt = f"""You are an intelligent agent that helps users accomplish tasks.

## Your Capabilities

1. **Direct Response**: For simple questions, explanations, or information requests, respond directly.

2. **Code Execution**: For tasks requiring computation, file processing, or external operations:
   - Generate Python code wrapped in ```python code blocks
   - The code will be executed and you'll see the results
   - Based on results, decide if the task is complete or needs more work

3. **Skills**: You have access to specialized skills that provide domain-specific guidance.
   - Review the available skills below
   - If a skill is relevant, ask to load it using: [LOAD_SKILL: skill_name]
   - Once loaded, follow the skill's guidance and code patterns

{skills_meta}

## Code Generation Rules

When generating Python code:
1. Wrap code in ```python and ``` markers
2. The script must be self-contained and executable
3. Use `print()` for output that you want to see
4. For final results, print a JSON object with "status", "result", and optionally "output_file_names" keys
5. Follow patterns from loaded skills when available

**IMPORTANT: If your code generates any output files (xlsx, csv, pdf, images, etc.), you MUST include `output_file_names` in your final JSON output!**

Example output format (without output files):
```python
import json
# ... your code ...
print(json.dumps({{"status": "success", "result": "任务完成的描述"}}))
```

Example output format (with output files):
```python
import json
# ... your code that generates files ...
output_files = ["report.xlsx", "chart.png"]  # List all generated files
print(json.dumps({{
    "status": "success", 
    "result": "任务完成的描述",
    "output_file_names": output_files
}}))
```

## Skill Helper Scripts

When a skill is loaded, you can use its helper scripts. The skill directory path will be provided.
Example: `subprocess.run(['python', 'path/to/skill/recalc.py', 'file.xlsx'])`

## Decision Flow

After seeing code execution results:
- If successful and task complete → Provide final response to user
- If error occurred → Analyze error, generate corrected code (follow skill's error handling guidance)
- If partial success → Generate additional code to complete the task
"""
        
        # Add loaded skills content
        if self.loaded_skills:
            system_prompt += "\n\n## Loaded Skill Documentation\n"
            for skill_name, content in self.loaded_skills.items():
                system_prompt += f"\n### Skill: {skill_name}\n"
                system_prompt += content
                skill_dir = self.skill_loader.get_skill_directory(skill_name)
                if skill_dir:
                    system_prompt += f"\n\n**Skill Directory**: {skill_dir}\n"
        
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
        
        This provides convenient functions for accessing skill resources during code execution.
        """
        skills_dir = str(self.skill_loader.skills_dir.absolute())
        
        return f'''
# === Skill Helpers (auto-injected) ===
class SkillHelpers:
    """Access skill resources during code execution."""
    
    SKILLS_DIR = r"{skills_dir}"
    
    @staticmethod
    def get_file_path(skill_name: str, relative_path: str) -> str:
        """
        Get absolute path to a file in skill directory.
        
        Args:
            skill_name: Name of the skill (e.g., "pptx", "xlsx")
            relative_path: Path relative to skill directory (e.g., "scripts/html2pptx.js")
            
        Returns:
            Absolute path to the file
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        from pathlib import Path
        path = Path(SkillHelpers.SKILLS_DIR) / skill_name / relative_path
        if path.exists():
            return str(path.absolute())
        raise FileNotFoundError(f"Skill file not found: {{skill_name}}/{{relative_path}}")
    
    @staticmethod
    def get_script_path(skill_name: str, script_name: str) -> str:
        """
        Get path to a script in skill's scripts/ directory.
        
        Args:
            skill_name: Name of the skill
            script_name: Script filename (e.g., "html2pptx.js", "recalc.py")
            
        Returns:
            Absolute path to the script
        """
        return SkillHelpers.get_file_path(skill_name, f"scripts/{{script_name}}")
    
    @staticmethod
    def get_skill_dir(skill_name: str) -> str:
        """
        Get absolute path to a skill's root directory.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Absolute path to skill directory
        """
        from pathlib import Path
        path = Path(SkillHelpers.SKILLS_DIR) / skill_name
        if path.exists():
            return str(path.absolute())
        raise FileNotFoundError(f"Skill not found: {{skill_name}}")
    
    @staticmethod
    def list_scripts(skill_name: str) -> list:
        """
        List all scripts in a skill's scripts/ directory.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            List of script filenames
        """
        from pathlib import Path
        scripts_dir = Path(SkillHelpers.SKILLS_DIR) / skill_name / "scripts"
        if not scripts_dir.exists():
            return []
        return [f.name for f in scripts_dir.iterdir() if f.is_file()]

skill_helpers = SkillHelpers()
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
        # Build skill helpers injection
        # skill_helpers_code = self._build_skill_helpers_code()
        
        # Wrap code with proper structure
        wrapped_code = f'''import sys
import json
import os
import subprocess
from pathlib import Path
{code}
'''
        
        # Save script
        script_name = f"{session_id}_{self.tool_call_count:02d}_{uuid.uuid4().hex[:6]}.py"
        script_path = self.script_dir / script_name
        script_path.write_text(wrapped_code)
        
        # Execute and collect output
        output_lines = []
        error_lines = []
        result = None
        status = "success"
        
        try:
            async for log in run_script(str(script_path), cwd=str(self.script_dir)):
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
            "script_path": str(script_path)
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
        
        # 使用 file_names，文件就在当前工作目录 (scripts/) 下
        if file_names:
            full_user_message += "\n\n## 用户上传的文件（在当前目录下）:\n"
            for name in file_names:
                full_user_message += f"- {name}\n"
        elif file_urls:
            # 兜底：如果只有 URL，从 URL 中解析文件名
            full_user_message += "\n\n## 用户上传的文件（在当前目录下）:\n"
            for url in file_urls:
                filename = url.split("/")[-1]
                full_user_message += f"- {filename}\n"
        
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
                    #max_tokens=,
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

