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
    
    # ✅ If command uses python, replace with .venv Python
    original_command = command
    backend_root = Path(__file__).parent.parent.parent
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
        
        logger.info(f"[background] {session_id}: completed (exit_code: {process.returncode})")
        
    except Exception as e:
        logger.error(f"[background] {session_id}: error - {e}")
        proc_info["status"] = "error"
        proc_info["error"] = str(e)


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


# Import os module
import os

