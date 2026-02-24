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
Command execution tool - exec (non-persistent version)
"""
import asyncio
import subprocess
import uuid
import json
import time
import os
import logging
from pathlib import Path
from typing import Optional, Dict

from .security import validate_command, get_user_workdir

logger = logging.getLogger(__name__)


# Background process registry
_background_processes: Dict[str, Dict] = {}

# ✅ Maximum completed processes to keep (prevents memory leak)
_MAX_COMPLETED_PROCESSES = 50


async def exec_command(
    context,  # AgentContext
    command: str,
    workdir: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: int = 300,
    background: bool = False
) -> str:
    """
    Execute a one-time command (non-persistent).
    
    Args:
        context: AgentContext
        command: Command to execute
        workdir: Working directory (optional)
        env: Environment variables (optional)
        timeout: Timeout in seconds
        background: Whether to run in background
    
    Returns:
        JSON formatted execution result
    """
    # 1. Command security check
    is_safe, error_msg = validate_command(command, context.user_id)
    if not is_safe:
        logger.warning(f"[exec] Command blocked: {command} - {error_msg}")
        return json.dumps({
            "status": "error",
            "error": error_msg
        }, ensure_ascii=False)
    
    # 2. Determine working directory
    if workdir:
        try:
            from .security import validate_path
            # ✅ Pass script_dir to support date subdirectory
            resolved_workdir = validate_path(workdir, context.user_id, operation="read", script_dir=context.script_dir)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": f"Invalid working directory: {e}"
            }, ensure_ascii=False)
    else:
        # ✅ Use context.script_dir (with date subdirectory) consistent with shell_exec
        resolved_workdir = context.script_dir
    
    # 3. Prepare environment variables
    exec_env = dict(os.environ) if env is None else {**os.environ, **env}
    
    # ✅ Inject PYTHONPATH and MCP config for call_tool support
    backend_root = Path(__file__).parent.parent.parent
    existing_pythonpath = exec_env.get("PYTHONPATH", "")
    backend_root_str = str(backend_root)
    if backend_root_str not in existing_pythonpath:
        exec_env["PYTHONPATH"] = f"{backend_root_str}:{existing_pythonpath}" if existing_pythonpath else backend_root_str
    
    # Set MCP server config as env vars (read by _mcp_env_bootstrap.py)
    mcp_url = getattr(context, 'mcp_server_url', None)
    mcp_type = getattr(context, 'mcp_server_type', 'sse')
    if mcp_url:
        exec_env["_MCP_SERVER_URL"] = mcp_url
        exec_env["_MCP_SERVER_TYPE"] = mcp_type
    
    # ✅ If command uses python, replace with .venv Python
    original_command = command
    venv_python = backend_root / ".venv" / "bin" / "python"
    
    if venv_python.exists():
        # Check if command starts with python
        if command.strip().startswith("python ") or command.strip() == "python":
            # Replace with virtual env Python
            command = command.replace("python ", f"{venv_python} ", 1)
            logger.info(f"[exec] Using .venv Python: {venv_python}")
        elif command.strip().startswith("python3 ") or command.strip() == "python3":
            # Replace with virtual env Python
            command = command.replace("python3 ", f"{venv_python} ", 1)
            logger.info(f"[exec] Using .venv Python: {venv_python}")
    else:
        logger.warning(f"[exec] .venv/bin/python not found, using system Python")
    
    # ✅ If running a Python script, inject call_tool bootstrap
    # Default MCP servers (高德/Exa Search/Fetch) are built into mcp_client.py,
    # so bootstrap is always created (not just when mcp_url is set)
    if _is_python_script_command(command):
        bootstrap_file = _ensure_mcp_bootstrap(backend_root, mcp_url, mcp_type)
        if bootstrap_file:
            exec_env["_MCP_BOOTSTRAP"] = str(bootstrap_file)
            # ✅ Create a wrapper that imports bootstrap then runs the actual script
            wrapper = _ensure_mcp_wrapper(backend_root)
            if wrapper:
                command = _wrap_python_command(command, str(wrapper))
                logger.info(f"[exec] Wrapped command with MCP bootstrap: {command[:120]}")
    
    # 4. Generate session ID
    session_id = f"exec_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"[exec] {session_id}: {command} (workdir: {resolved_workdir}, background: {background})")
    
    try:
        if background:
            # Background execution
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(resolved_workdir),
                env=exec_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Register background process
            _background_processes[session_id] = {
                "process": process,
                "command": command,
                "workdir": str(resolved_workdir),
                "started_at": time.time(),
                "user_id": context.user_id,
                "stdout": [],
                "stderr": []
            }
            
            # Start output collection task
            asyncio.create_task(_collect_background_output(session_id))
            
            return json.dumps({
                "status": "running",
                "session_id": session_id,
                "pid": process.pid,
                "message": f"Command started in background (session_id: {session_id})。Use process(action='status', session_id='{session_id}') to check progress."
            }, ensure_ascii=False)
        
        else:
            # ✅ Before execution: record existing files
            before_files = set()
            try:
                if resolved_workdir.exists():
                    before_files = set(f.name for f in resolved_workdir.iterdir() if f.is_file())
            except Exception as e:
                logger.debug(f"[exec] Cannot read working directory: {e}")
            
            # Synchronous execution
            start_time = time.time()
            
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(resolved_workdir),
                env=exec_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                stdout = stdout_data.decode('utf-8', errors='replace')
                stderr = stderr_data.decode('utf-8', errors='replace')
                exit_code = process.returncode
                duration = time.time() - start_time
                
                logger.info(f"[exec] {session_id}: completed (exit_code: {exit_code}, duration: {duration:.2f}s)")
                
                if exit_code != 0:
                    # Execution failed
                    error_msg = f"Command execution failed (exit code {exit_code})"
                    if stderr:
                        error_msg += f"\n\nSTDERR:\n{stderr}"
                    if stdout:
                        error_msg += f"\n\nSTDOUT:\n{stdout}"
                    
                    return json.dumps({
                        "status": "error",
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                        "duration_ms": int(duration * 1000),
                        "error": error_msg
                    }, ensure_ascii=False)
                
                # ✅ After success: detect newly created files
                created_files = []
                try:
                    if resolved_workdir.exists():
                        after_files = set(f.name for f in resolved_workdir.iterdir() if f.is_file())
                        new_file_names = after_files - before_files
                        
                        if new_file_names:
                            for file_name in new_file_names:
                                file_path = resolved_workdir / file_name
                                if file_path.exists():
                                    created_files.append({
                                        "name": file_name,
                                        "path": str(file_path),
                                        "size": file_path.stat().st_size,
                                        "lines": len(file_path.read_text(errors='ignore').splitlines()) if file_path.suffix in ['.py', '.txt', '.md', '.sh'] else 0
                                    })
                                    logger.info(f"[exec] Detected new file: {file_name} ({file_path.stat().st_size} bytes)")
                except Exception as e:
                    logger.debug(f"[exec] File detection failed: {e}")
                
                # Execution successful
                result = {
                    "status": "success",
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "duration_ms": int(duration * 1000)
                }
                
                # ✅ If there are new files, add to result
                if created_files:
                    result["created_files"] = created_files
                
                return json.dumps(result, ensure_ascii=False)
                
            except asyncio.TimeoutError:
                # Timeout, kill process
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass
                
                duration = time.time() - start_time
                logger.warning(f"[exec] {session_id}: timeout after {duration:.2f}s")
                
                return json.dumps({
                    "status": "error",
                    "error": f"Command execution timed out ({timeout}  seconds)",
                    "duration_ms": int(duration * 1000)
                }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"[exec] {session_id}: error - {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"Error executing command: {e}"
        }, ensure_ascii=False)


async def _collect_background_output(session_id: str):
    """Collect background process output"""
    if session_id not in _background_processes:
        return
    
    proc_info = _background_processes[session_id]
    process = proc_info["process"]
    
    try:
        stdout_data, stderr_data = await process.communicate()
        
        proc_info["stdout"] = stdout_data.decode('utf-8', errors='replace').split('\n')
        proc_info["stderr"] = stderr_data.decode('utf-8', errors='replace').split('\n')
        proc_info["exit_code"] = process.returncode
        proc_info["completed_at"] = time.time()
        proc_info["status"] = "completed" if process.returncode == 0 else "failed"
        
        # ✅ Release the process object to free resources
        proc_info["process"] = None
        
        logger.info(f"[background] {session_id}: completed (exit_code: {process.returncode})")
        
    except Exception as e:
        logger.error(f"[background] {session_id}: error - {e}")
        proc_info["status"] = "error"
        proc_info["error"] = str(e)
        proc_info["process"] = None
    
    # ✅ FIX: Cleanup old completed processes to prevent memory leak
    _cleanup_completed_processes()


def _cleanup_completed_processes():
    """Remove old completed processes from the registry to prevent memory leak."""
    completed = [
        (sid, info) for sid, info in _background_processes.items()
        if info.get("status") in ("completed", "failed", "error", "killed")
    ]
    
    if len(completed) > _MAX_COMPLETED_PROCESSES:
        # Sort by completion time, remove oldest
        completed.sort(key=lambda x: x[1].get("completed_at", 0))
        to_remove = completed[:len(completed) - _MAX_COMPLETED_PROCESSES]
        
        for sid, _ in to_remove:
            del _background_processes[sid]
            logger.debug(f"[background] Cleaned up old process: {sid}")
        
        logger.info(f"[background] Cleaned up {len(to_remove)} old completed processes")


async def process_manage(
    context,  # AgentContext
    action: str,
    session_id: Optional[str] = None
) -> str:
    """
    Manage background processes.
    
    Args:
        context: AgentContext
        action: Action type (list | status | logs | kill)
        session_id: Process session ID
    
    Returns:
        JSON formatted result
    """
    if action == "list":
        # List all background processes for current user
        user_processes = [
            {
                "session_id": sid,
                "command": info["command"],
                "started_at": info["started_at"],
                "status": info.get("status", "running"),
                "pid": info["process"].pid if info["process"].returncode is None else None
            }
            for sid, info in _background_processes.items()
            if info["user_id"] == context.user_id
        ]
        
        return json.dumps({
            "status": "success",
            "processes": user_processes,
            "count": len(user_processes)
        }, ensure_ascii=False)
    
    elif action == "status":
        if not session_id:
            return json.dumps({
                "status": "error",
                "error": "status action requires session_id"
            }, ensure_ascii=False)
        
        if session_id not in _background_processes:
            return json.dumps({
                "status": "error",
                "error": f"Session not found: {session_id}"
            }, ensure_ascii=False)
        
        proc_info = _background_processes[session_id]
        
        # Check user permissions
        if proc_info["user_id"] != context.user_id:
            return json.dumps({
                "status": "error",
                "error": "No permission to access this session"
            }, ensure_ascii=False)
        
        process = proc_info["process"]
        is_running = process.returncode is None
        
        result = {
            "status": "success",
            "session_id": session_id,
            "command": proc_info["command"],
            "started_at": proc_info["started_at"],
            "process_status": proc_info.get("status", "running" if is_running else "completed"),
            "exit_code": process.returncode
        }
        
        if "completed_at" in proc_info:
            result["duration_ms"] = int((proc_info["completed_at"] - proc_info["started_at"]) * 1000)
        
        return json.dumps(result, ensure_ascii=False)
    
    elif action == "logs":
        if not session_id:
            return json.dumps({
                "status": "error",
                "error": "logs action requires session_id"
            }, ensure_ascii=False)
        
        if session_id not in _background_processes:
            return json.dumps({
                "status": "error",
                "error": f"Session not found: {session_id}"
            }, ensure_ascii=False)
        
        proc_info = _background_processes[session_id]
        
        # Check user permissions
        if proc_info["user_id"] != context.user_id:
            return json.dumps({
                "status": "error",
                "error": "No permission to access this session"
            }, ensure_ascii=False)
        
        stdout_lines = proc_info.get("stdout", [])
        stderr_lines = proc_info.get("stderr", [])
        
        return json.dumps({
            "status": "success",
            "session_id": session_id,
            "stdout": '\n'.join(stdout_lines),
            "stderr": '\n'.join(stderr_lines),
            "lines_stdout": len(stdout_lines),
            "lines_stderr": len(stderr_lines)
        }, ensure_ascii=False)
    
    elif action == "kill":
        if not session_id:
            return json.dumps({
                "status": "error",
                "error": "kill action requires session_id"
            }, ensure_ascii=False)
        
        if session_id not in _background_processes:
            return json.dumps({
                "status": "error",
                "error": f"Session not found: {session_id}"
            }, ensure_ascii=False)
        
        proc_info = _background_processes[session_id]
        
        # Check user permissions
        if proc_info["user_id"] != context.user_id:
            return json.dumps({
                "status": "error",
                "error": "No permission to access this session"
            }, ensure_ascii=False)
        
        process = proc_info["process"]
        
        if process.returncode is not None:
            return json.dumps({
                "status": "success",
                "message": "Process has ended",
                "exit_code": process.returncode
            }, ensure_ascii=False)
        
        try:
            process.kill()
            await process.wait()
            
            proc_info["status"] = "killed"
            proc_info["completed_at"] = time.time()
            
            logger.info(f"[process] {session_id}: killed")
            
            return json.dumps({
                "status": "success",
                "message": "Process terminated",
                "session_id": session_id
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"[process] Failed to kill {session_id}: {e}")
            return json.dumps({
                "status": "error",
                "error": f"Failed to terminate process: {e}"
            }, ensure_ascii=False)
    
    else:
        return json.dumps({
            "status": "error",
            "error": f"Unknown action: {action}"
        }, ensure_ascii=False)


def _is_python_script_command(command: str) -> bool:
    """Check if command is running a Python script."""
    cmd = command.strip()
    # Match patterns like: python script.py, python3 script.py, /path/to/python script.py
    parts = cmd.split()
    if len(parts) >= 2:
        exe = Path(parts[0]).name
        if exe in ("python", "python3") or "python" in exe:
            # Second part should be a .py file
            if parts[1].endswith(".py"):
                return True
    return True if ("python" in cmd and ".py" in cmd) else False


def _ensure_mcp_bootstrap(backend_root: Path, mcp_url: str = None, mcp_type: str = "sse") -> Optional[Path]:
    """
    Create the MCP bootstrap file that provides call_tool in exec environment.
    
    This file is auto-imported at the start of Python scripts executed via exec,
    making call_tool() transparently available without LLM needing MCP server details.
    
    Architecture:
    - Default MCP servers (高德/Exa Search/Fetch) are built into app.mcp_client.DEFAULT_MCP_SERVERS
    - call_tool() does lazy discovery → auto-routes to the correct server
    - User-specific server (from DB) is optionally registered via env vars
    - LLM never sees any of this; it just uses call_tool() as described in Skills
    """
    bootstrap_dir = backend_root / "app" / "tools" / "_bootstrap"
    bootstrap_dir.mkdir(parents=True, exist_ok=True)
    
    bootstrap_file = bootstrap_dir / "mcp_bootstrap.py"
    
    # Create/update the bootstrap file
    bootstrap_code = '''"""
Auto-generated MCP bootstrap for exec environment.
Provides call_tool() function transparently.

Default MCP servers (高德/Exa Search/Fetch) are built into app.mcp_client.
call_tool() auto-discovers and routes to the correct server.
"""
import os
import sys

def _setup_call_tool():
    """Setup call_tool in the exec environment."""
    # Ensure backend root is in sys.path
    backend_root = os.environ.get("PYTHONPATH", "").split(":")[0]
    if backend_root and backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    
    try:
        from app.mcp_client import call_tool as _async_call_tool
        
        # Optionally register user-specific MCP server from env vars
        mcp_url = os.environ.get("_MCP_SERVER_URL")
        mcp_type = os.environ.get("_MCP_SERVER_TYPE", "sse")
        if mcp_url:
            from app.mcp_client import register_tool_server
            register_tool_server("__user_env__", mcp_url, mcp_type)
        
        import asyncio
        import time as _time
        
        # Rate-limiting: track last call time to enforce minimum interval
        _last_call_time = [0.0]  # mutable container for closure
        _MIN_CALL_INTERVAL = 2.0  # minimum seconds between consecutive calls
        
        def call_tool(tool_name, args=None):
            """
            Call an MCP tool synchronously.
            
            Built-in servers: 高德地图, Exa Search搜索, Fetch网页抓取
            Usage: result = call_tool('web_search_exa', {'query': 'search term'})
            
            Note: Automatically enforces minimum 2s interval between calls
            to prevent remote server connection instability.
            """
            import asyncio
            from app.mcp_client import call_tool as _act
            
            # Enforce minimum interval between calls
            now = _time.time()
            elapsed = now - _last_call_time[0]
            if elapsed < _MIN_CALL_INTERVAL and _last_call_time[0] > 0:
                wait = _MIN_CALL_INTERVAL - elapsed
                _time.sleep(wait)
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result = pool.submit(asyncio.run, _act(tool_name, args or {})).result()
                else:
                    result = loop.run_until_complete(_act(tool_name, args or {}))
            except RuntimeError:
                result = asyncio.run(_act(tool_name, args or {}))
            finally:
                _last_call_time[0] = _time.time()
            
            return result
        
        return call_tool
    except ImportError as e:
        print(f"[MCP Bootstrap] Warning: Cannot import mcp_client: {e}")
        return None

# Auto-setup on import
_call_tool_func = _setup_call_tool()
if _call_tool_func:
    # Make call_tool available as a module-level function
    call_tool = _call_tool_func
'''
    
    try:
        # Only write if content changed
        if bootstrap_file.exists():
            existing = bootstrap_file.read_text()
            if existing == bootstrap_code:
                return bootstrap_file
        
        bootstrap_file.write_text(bootstrap_code)
        logger.info(f"[exec] Created MCP bootstrap: {bootstrap_file}")
        return bootstrap_file
    except Exception as e:
        logger.warning(f"[exec] Failed to create MCP bootstrap: {e}")
        return None


def _ensure_mcp_wrapper(backend_root: Path) -> Optional[Path]:
    """
    Create a wrapper script that imports the MCP bootstrap then runs the target script.
    
    This is the key mechanism that makes call_tool() available in exec-launched Python scripts.
    The wrapper:
    1. Reads and executes the bootstrap file (which defines call_tool in globals)
    2. Runs the target script with call_tool already in builtins
    """
    bootstrap_dir = backend_root / "app" / "tools" / "_bootstrap"
    bootstrap_dir.mkdir(parents=True, exist_ok=True)
    
    wrapper_file = bootstrap_dir / "_run_with_mcp.py"
    
    wrapper_code = '''"""
Auto-generated wrapper: injects call_tool() then runs the target Python script.
Usage: python _run_with_mcp.py <target_script.py> [args...]
"""
import os
import sys
import runpy

def _inject_call_tool():
    """Load MCP bootstrap to make call_tool available as a builtin."""
    bootstrap_path = os.environ.get("_MCP_BOOTSTRAP")
    if not bootstrap_path or not os.path.exists(bootstrap_path):
        return
    
    try:
        # Execute bootstrap in a namespace
        ns = {}
        exec(open(bootstrap_path).read(), ns)
        
        # If bootstrap defined call_tool, inject it into builtins
        # so it's available in ALL subsequently executed scripts
        if "call_tool" in ns:
            import builtins
            builtins.call_tool = ns["call_tool"]
    except Exception as e:
        print(f"[MCP Wrapper] Warning: Failed to load bootstrap: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python _run_with_mcp.py <script.py> [args...]", file=sys.stderr)
        sys.exit(1)
    
    # Inject call_tool into builtins
    _inject_call_tool()
    
    # Fix sys.argv so the target script sees the correct arguments
    target_script = sys.argv[1]
    sys.argv = sys.argv[1:]
    
    # Run the target script
    runpy.run_path(target_script, run_name="__main__")
'''
    
    try:
        if wrapper_file.exists():
            existing = wrapper_file.read_text()
            if existing == wrapper_code:
                return wrapper_file
        
        wrapper_file.write_text(wrapper_code)
        logger.info(f"[exec] Created MCP wrapper: {wrapper_file}")
        return wrapper_file
    except Exception as e:
        logger.warning(f"[exec] Failed to create MCP wrapper: {e}")
        return None


def _wrap_python_command(command: str, wrapper_path: str) -> str:
    """
    Wrap a Python script command to use the MCP wrapper.
    
    Transforms:
        /path/to/python script.py arg1 arg2
    Into:
        /path/to/python /path/to/_run_with_mcp.py script.py arg1 arg2
    """
    cmd = command.strip()
    parts = cmd.split(None, 1)  # Split into [python_exe, rest]
    
    if len(parts) < 2:
        return command  # No script to wrap
    
    python_exe = parts[0]
    script_and_args = parts[1]
    
    return f"{python_exe} {wrapper_path} {script_and_args}"

