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
Persistent shell session management - based on pexpect.
Supports variable persistence and multi-step execution.
"""
import asyncio
import pexpect
import uuid
import time
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass

from .security import get_user_workdir

logger = logging.getLogger(__name__)

# Shared thread pool for running blocking pexpect operations
# This allows asyncio.wait_for() to actually cancel hung pexpect calls
_pexpect_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pexpect")


@dataclass
class ShellSession:
    """Single shell session"""
    session_id: str
    shell_type: str  # bash | python | ipython
    user_id: str
    workdir: Path
    process: pexpect.spawn
    created_at: float
    last_activity: float
    error_count: int = 0
    
    @property
    def is_alive(self) -> bool:
        """Check if the process is still alive"""
        return self.process.isalive()
    
    @property
    def age_seconds(self) -> float:
        """Session age (seconds)"""
        return time.time() - self.created_at
    
    @property
    def idle_seconds(self) -> float:
        """Idle time (seconds)"""
        return time.time() - self.last_activity


class ShellSessionManager:
    """Persistent shell session manager (auto-managed)"""
    
    # Configuration
    MAX_IDLE_TIME = 600  # 10 min inactivity auto-close
    MAX_SESSION_AGE = 3600  # 1 hour max session lifetime
    MAX_ERROR_COUNT = 3  # Auto-close after 3 consecutive errors
    MAX_SESSIONS_PER_USER = 3  # Max 3 sessions per user
    MAX_TOTAL_SESSIONS = 20  # Max 20 global sessions
    
    def __init__(self):
        self.sessions: Dict[str, ShellSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def start_cleanup_task(self):
        """Start automatic cleanup task"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._auto_cleanup())
    
    async def _auto_cleanup(self):
        """
        Auto cleanup expired sessions.
        
        ✅ Fix: Added error counter to prevent silent task death.
        If cleanup fails repeatedly, it logs a critical warning but keeps running.
        """
        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 10
        
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # ✅ Use list() to avoid "dict changed during iteration" errors
                # Collect sessions that need to be closed
                to_close = []
                for sid, session in list(self.sessions.items()):
                    # Check if cleanup is needed
                    if not session.is_alive:
                        to_close.append((sid, "Process has ended"))
                    elif session.idle_seconds > self.MAX_IDLE_TIME:
                        to_close.append((sid, f"Idle timeout ({session.idle_seconds:.0f}s)"))
                    elif session.age_seconds > self.MAX_SESSION_AGE:
                        to_close.append((sid, f"Session timeout ({session.age_seconds:.0f}s)"))
                    elif session.error_count >= self.MAX_ERROR_COUNT:
                        to_close.append((sid, f"Too many errors ({session.error_count})"))
                
                # Close sessions
                for sid, reason in to_close:
                    logger.info(f"[cleanup] Closing session {sid}: {reason}")
                    try:
                        await self._close_session(sid)
                    except Exception as e:
                        logger.error(f"[cleanup] Error closing session {sid}: {e}")
                
                # Check total session count
                if len(self.sessions) > self.MAX_TOTAL_SESSIONS:
                    logger.warning(f"[cleanup] Total session count exceeded ({len(self.sessions)} > {self.MAX_TOTAL_SESSIONS})")
                    await self._emergency_cleanup()
                
                # Reset error counter on successful iteration
                consecutive_errors = 0
                    
            except asyncio.CancelledError:
                logger.info("[cleanup] Cleanup task cancelled")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"[cleanup] Cleanup task error ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {e}")
                
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.critical(f"[cleanup] Too many consecutive errors, cleanup task degraded")
                    # Don't exit - keep trying but with longer interval
                    await asyncio.sleep(60)
    
    async def _emergency_cleanup(self):
        """Emergency cleanup: close oldest idle sessions"""
        logger.warning("[cleanup] Performing emergency cleanup")
        
        # Sort by idle time, close the oldest sessions
        sessions_by_idle = sorted(
            self.sessions.items(),
            key=lambda x: x[1].last_activity
        )
        
        # Close the 10 oldest sessions
        for sid, session in sessions_by_idle[:10]:
            logger.warning(f"[cleanup] Emergency closing session {sid} (idle {session.idle_seconds:.0f}s)")
            await self._close_session(sid)
    
    def _count_user_sessions(self, user_id: str) -> int:
        """Count user session quantity"""
        return sum(1 for s in self.sessions.values() if s.user_id == user_id)
    
    async def _cleanup_old_user_sessions(self, user_id: str, shell_type: str):
        """Clean up user old sessions (if exceeding limit)"""
        user_sessions = [
            (sid, s) for sid, s in self.sessions.items()
            if s.user_id == user_id and s.shell_type == shell_type
        ]
        
        if len(user_sessions) >= self.MAX_SESSIONS_PER_USER:
            # Sort by activity time, close the oldest
            user_sessions.sort(key=lambda x: x[1].last_activity)
            for sid, session in user_sessions[:-1]:  # Keep the newest one
                logger.info(f"[cleanup] Closing user {user_id} old session {sid}")
                await self._close_session(sid)
    
    async def get_or_create_session(
        self,
        user_id: str,
        shell_type: str = "bash",
        workdir: Optional[Path] = None,
        mcp_server_url: Optional[str] = None,
        mcp_server_type: str = "sse"
    ) -> ShellSession:
        """
        Get or create session (auto-managed).
        
        Strategy:
        1. Find existing session for this user (same shell_type)
        2. If found and active, reuse
        3. Otherwise create new session
        
        Args:
            user_id: User ID
            shell_type: Shell type
            workdir: Optional working directory (if not provided, use default)
        """
        # ✅ First check and clean up excess sessions
        if len(self.sessions) >= self.MAX_TOTAL_SESSIONS:
            logger.warning(f"[session] Total session count reached limit ({len(self.sessions)}), performing cleanup")
            await self._emergency_cleanup()
        
        # ✅ Check user session count
        if self._count_user_sessions(user_id) >= self.MAX_SESSIONS_PER_USER:
            logger.info(f"[session] User {user_id} Session count reached limit, cleaning up old sessions")
            await self._cleanup_old_user_sessions(user_id, shell_type)
        
        # Find existing session
        for session in list(self.sessions.values()):
            if (session.user_id == user_id and 
                session.shell_type == shell_type and 
                session.is_alive):
                # ✅ If workdir specified, check if it matches
                if workdir is not None:
                    # Convert to Path objects for comparison (ensure type consistency)
                    session_workdir = Path(session.workdir) if not isinstance(session.workdir, Path) else session.workdir
                    requested_workdir = Path(workdir) if not isinstance(workdir, Path) else workdir
                    
                    # Compare after resolving to absolute paths
                    if session_workdir.resolve() != requested_workdir.resolve():
                        # Working directory mismatch, close old session and create new one
                        logger.info(f"[session] Working directory mismatch, closing old session: {session.session_id}")
                        logger.info(f"[session]   Old: {session_workdir.resolve()}")
                        logger.info(f"[session]   New: {requested_workdir.resolve()}")
                        await self._close_session(session.session_id)
                        continue
                
                # Reuse existing session
                session.last_activity = time.time()
                logger.info(f"[session] Reusing session: {session.session_id} (workdir: {session.workdir})")
                return session
        
        # Create new session
        session_id = f"{shell_type}_{uuid.uuid4().hex[:8]}"
        
        # ✅ Use provided workdir or default user directory
        if workdir is None:
            workdir = get_user_workdir(user_id)
        else:
            # Ensure directory exists
            workdir.mkdir(parents=True, exist_ok=True)
        
        # ✅ Before starting process, check PTY resources
        try:
            import os as os_module
            # Try to detect available PTY count
            pty_count = len([f for f in os_module.listdir('/dev') if f.startswith('pty')])
            logger.debug(f"[session] Current PTY device count: {pty_count}")
        except Exception as e:
            logger.debug(f"[session] Cannot detect PTY count: {e}")
        
        # Start process
        if shell_type == "bash":
            try:
                process = pexpect.spawn(
                    "/bin/bash",
                    ["--norc", "--noprofile"],  # Do not load config files
                    cwd=str(workdir),
                    encoding='utf-8',
                    timeout=300,
                    maxread=10000  # Limit single read
                )
            except OSError as e:
                if 'out of pty devices' in str(e):
                    logger.error("[session] PTY resources exhausted! Performing emergency cleanup")
                    await self._emergency_cleanup()
                    # Retry once
                    process = pexpect.spawn(
                        "/bin/bash",
                        ["--norc", "--noprofile"],
                        cwd=str(workdir),
                        encoding='utf-8',
                        timeout=300,
                        maxread=10000
                    )
                else:
                    raise
            # Bash prompt setup
            process.sendline('export PS1="READY> "')
            process.expect("READY> ", timeout=5)
            prompt = r"READY> "
            
        elif shell_type == "python":
            # ✅ Use .venv Python (includes all installed packages)
            backend_root = Path(__file__).parent.parent.parent
            venv_python = backend_root / ".venv" / "bin" / "python"
            
            if venv_python.exists():
                python_cmd = str(venv_python)
                logger.info(f"[shell_session] Using .venv Python: {python_cmd}")
            else:
                # Fallback to system Python
                python_cmd = "python3"
                logger.warning("[shell_session] .venv/bin/python not found, using system Python")
            
            try:
                process = pexpect.spawn(
                    python_cmd,
                    ["-u"],  # Unbuffered output
                    cwd=str(workdir),
                    encoding='utf-8',
                    timeout=300,
                    maxread=10000
                )
            except OSError as e:
                if 'out of pty devices' in str(e):
                    logger.error("[session] PTY resources exhausted! Performing emergency cleanup")
                    await self._emergency_cleanup()
                    # Retry once
                    process = pexpect.spawn(
                        python_cmd,
                        ["-u"],
                        cwd=str(workdir),
                        encoding='utf-8',
                        timeout=300,
                        maxread=10000
                    )
                else:
                    raise
            prompt = r">>> "
            process.expect(prompt, timeout=5)
            
        elif shell_type == "ipython":
            # ✅ Use .venv IPython (if exists)
            backend_root = Path(__file__).parent.parent.parent
            venv_ipython = backend_root / ".venv" / "bin" / "ipython"
            
            if venv_ipython.exists():
                ipython_cmd = str(venv_ipython)
                logger.info(f"[shell_session] Using .venv IPython: {ipython_cmd}")
            else:
                # Fallback to system IPython
                ipython_cmd = "ipython"
                logger.warning("[shell_session] .venv/bin/ipython not found, using system IPython")
            
            try:
                process = pexpect.spawn(
                    ipython_cmd,
                    ["--no-confirm-exit", "--no-banner", "--colors=NoColor"],
                    cwd=str(workdir),
                    encoding='utf-8',
                    timeout=300,
                    maxread=10000
                )
            except OSError as e:
                if 'out of pty devices' in str(e):
                    logger.error("[session] PTY resources exhausted! Performing emergency cleanup")
                    await self._emergency_cleanup()
                    # Retry once
                    process = pexpect.spawn(
                        ipython_cmd,
                        ["--no-confirm-exit", "--no-banner", "--colors=NoColor"],
                        cwd=str(workdir),
                        encoding='utf-8',
                        timeout=300,
                        maxread=10000
                    )
                else:
                    raise
            prompt = r"In \[\d+\]: "
            process.expect(prompt, timeout=5)
        
        else:
            raise ValueError(f"Unsupported shell type: {shell_type}")
        
        session = ShellSession(
            session_id=session_id,
            shell_type=shell_type,
            user_id=user_id,
            workdir=workdir,
            process=process,
            created_at=time.time(),
            last_activity=time.time()
        )
        
        # Save prompt pattern
        session._prompt = prompt
        
        self.sessions[session_id] = session
        
        logger.info(f"[session] Created new session: {session_id} ({shell_type}, user: {user_id})")
        
        # ✅ Inject call_tool into Python/IPython sessions (transparent to LLM)
        # Always inject: default MCP servers are built into mcp_client.py,
        # plus optionally register user-specific server if provided
        if shell_type in ("python", "ipython"):
            await self._inject_call_tool(session, mcp_server_url, mcp_server_type)
        
        # Ensure cleanup task is running
        self.start_cleanup_task()
        
        return session
    
    async def _inject_call_tool(
        self, 
        session: ShellSession, 
        mcp_server_url: Optional[str] = None, 
        mcp_server_type: str = "sse"
    ):
        """
        Inject call_tool function into Python/IPython session.
        
        This makes `call_tool('tool_name', {args})` available in the execution
        environment without the LLM needing to know about MCP server details.
        
        Architecture:
        - Default MCP servers (高德/Exa Search/Fetch) are built into app.mcp_client
        - call_tool() does lazy discovery → auto-routes to the correct server
        - User-specific server (from DB) is optionally registered on top
        - LLM never sees any of this; it just uses call_tool() as described in Skills
        """
        backend_root = Path(__file__).parent.parent.parent
        
        # Step 1: Setup sys.path and imports
        # mcp_client.py has DEFAULT_MCP_SERVERS built-in, no explicit registration needed
        step1 = (
            f"import sys; sys.path.insert(0, {repr(str(backend_root))}); "
            f"import asyncio"
        )
        
        # Optionally register user-specific MCP server (from DB)
        if mcp_server_url:
            step1 += (
                f"; from app.mcp_client import register_tool_server; "
                f"register_tool_server('__user__', {repr(mcp_server_url)}, {repr(mcp_server_type)})"
            )
        
        # Step 2: Define sync call_tool wrapper with rate-limiting
        # The async call_tool from mcp_client handles:
        # - Routing to registered tools
        # - Lazy discovery from DEFAULT_MCP_SERVERS
        # - Fallback to try each default server
        # Rate-limiting prevents remote server connection instability
        step2 = (
            "import time as _time\n"
            "_last_call_time = [0.0]\n"
            "_MIN_CALL_INTERVAL = 2.0\n"
            "def call_tool(tool_name, args=None):\n"
            "    import asyncio\n"
            "    from app.mcp_client import call_tool as _act\n"
            "    now = _time.time()\n"
            "    elapsed = now - _last_call_time[0]\n"
            "    if elapsed < _MIN_CALL_INTERVAL and _last_call_time[0] > 0:\n"
            "        _time.sleep(_MIN_CALL_INTERVAL - elapsed)\n"
            "    try:\n"
            "        loop = asyncio.get_event_loop()\n"
            "        if loop.is_running():\n"
            "            import concurrent.futures\n"
            "            with concurrent.futures.ThreadPoolExecutor() as pool:\n"
            "                result = pool.submit(asyncio.run, _act(tool_name, args or {})).result()\n"
            "        else:\n"
            "            result = loop.run_until_complete(_act(tool_name, args or {}))\n"
            "    except RuntimeError:\n"
            "        result = asyncio.run(_act(tool_name, args or {}))\n"
            "    finally:\n"
            "        _last_call_time[0] = _time.time()\n"
            "    return result\n"
        )
        
        try:
            # Step 1: Setup imports
            session.process.sendline(step1)
            session.process.expect(session._prompt, timeout=10)
            
            # Step 2: Define call_tool function using exec
            escaped_step2 = repr(step2)
            session.process.sendline(f"exec(compile({escaped_step2}, '<mcp_init>', 'exec'))")
            session.process.expect(session._prompt, timeout=10)
            
            # Step 3: Verify call_tool is actually defined
            session.process.sendline("print('__call_tool_ok__' if callable(call_tool) else '__call_tool_fail__')")
            idx = session.process.expect([session._prompt, pexpect.TIMEOUT], timeout=5)
            output = session.process.before if hasattr(session.process, 'before') else ""
            
            if "__call_tool_ok__" in str(output):
                logger.info(
                    f"[session] ✅ call_tool verified in session {session.session_id} "
                    f"(defaults: 高德/Exa Search/Fetch, user_mcp: {mcp_server_url or 'none'})"
                )
            else:
                logger.warning(
                    f"[session] ⚠️ call_tool injection unverified in session {session.session_id}. "
                    f"Output: {str(output)[:200]}"
                )
            
        except Exception as e:
            logger.warning(f"[session] Failed to inject call_tool into session {session.session_id}: {e}")
    
    async def execute_in_session(
        self,
        session: ShellSession,
        command: str,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Execute command in session.
        
        Returns:
            {"status": "success"|"error", "output": str, ...}
        """
        session.last_activity = time.time()
        
        if not session.is_alive:
            session.error_count += 1
            return {
                "status": "error",
                "error": "Session has ended",
                "session_id": session.session_id
            }
        
        try:
            # Clear buffer
            try:
                session.process.read_nonblocking(size=10000, timeout=0)
            except:
                pass
            
            # ✅ Ensure Python shell executes in correct working directory
            is_python_shell = session.shell_type in ["python", "ipython"]
            if is_python_shell:
                # Before executing user command, switch to correct working directory
                chdir_command = f"import os; os.chdir({repr(str(session.workdir))})"
                session.process.sendline(f"exec(compile({repr(chdir_command)}, '<string>', 'exec'))")
                
                # Wait for chdir to complete (don't capture output)
                try:
                    session.process.expect(session._prompt, timeout=2)
                except Exception as e:
                    logger.debug(f"[exec] chdir wait timeout (may have completed): {e}")
            
            # ✅ For Python/IPython multi-line code, use special handling
            is_multiline = '\n' in command.strip()
            actual_command = command
            
            if is_python_shell and is_multiline:
                # Multi-line Python code: wrap with exec()
                # Use repr() to safely escape code string
                logger.debug(f"[exec] Executing multi-line code: {len(command)} characters")
                
                # Security escape: use repr() to auto-handle all special characters
                escaped = repr(command)
                actual_command = f"exec(compile({escaped}, '<string>', 'exec'))"
                logger.debug(f"[exec] After wrapping: {actual_command[:100]}...")
            
            # Send command
            logger.info(f"[exec] {session.session_id}: Starting command execution, timeout={timeout} seconds")
            logger.debug(f"[exec] Command content (first 200 chars): {actual_command[:200]}")
            session.process.sendline(actual_command)
            logger.debug(f"[exec] Command sent, waiting for response...")
            
            # Wait for output and next prompt
            start_time = time.time()
            
            try:
                # ✅ FIX: Run pexpect.expect in thread executor so asyncio can cancel it
                # pexpect.expect() is synchronous and blocks the event loop.
                # By running it in a thread, asyncio.wait_for() can actually timeout.
                loop = asyncio.get_event_loop()
                
                def _blocking_expect():
                    """Run pexpect.expect in a thread to avoid blocking the event loop."""
                    session.process.expect(session._prompt, timeout=timeout)
                    return session.process.before
                
                logger.debug(f"[exec] Waiting for prompt in thread executor, timeout={timeout} seconds")
                output = await asyncio.wait_for(
                    loop.run_in_executor(_pexpect_executor, _blocking_expect),
                    timeout=timeout + 5  # 5s buffer over pexpect's own timeout
                )
                logger.debug(f"[exec] Received prompt response")
                
                # Clean output (remove echoed command)
                lines = output.split('\n')
                
                # ✅ Remove echoed command (may be original or wrapped command)
                if lines:
                    first_line = lines[0].strip()
                    # Check if first line is echoed command
                    if first_line == command.strip() or first_line == actual_command.strip():
                        lines = lines[1:]
                    # If it's exec(compile(...)), also remove
                    elif first_line.startswith('exec(compile('):
                        lines = lines[1:]
                
                cleaned_output = '\n'.join(lines).strip()
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Reset error count
                session.error_count = 0
                
                logger.info(f"[exec] {session.session_id}: Command executed successfully ({duration_ms}ms)")
                
                return {
                    "status": "success",
                    "output": cleaned_output,
                    "session_id": session.session_id,
                    "duration_ms": duration_ms
                }
            
            except asyncio.TimeoutError:
                duration_ms = int((time.time() - start_time) * 1000)
                duration_sec = duration_ms / 1000
                
                # Try to get existing output
                partial_output = ""
                try:
                    partial_output = session.process.before or ""
                except:
                    pass
                
                session.error_count += 1
                
                error_msg = f"Command execution timed out ({timeout} seconds)"
                logger.error(f"[exec] {session.session_id}: Timeout (asyncio)! Waited {duration_sec:.1f} seconds")
                logger.error(f"[exec] Partial output (first 500 chars): {str(partial_output)[:500]}")
                
                # ✅ FIX: Force kill the hung process to recover the session
                logger.warning(f"[exec] {session.session_id}: Force killing hung session for recovery")
                try:
                    session.process.kill(9)
                except Exception as kill_err:
                    logger.error(f"[exec] {session.session_id}: Failed to kill process: {kill_err}")
                
                return {
                    "status": "error",
                    "error": error_msg,
                    "output": str(partial_output),
                    "session_id": session.session_id,
                    "duration_ms": duration_ms,
                    "timeout_seconds": timeout,
                    "suggestion": "Command was stuck and the session has been terminated. It will auto-restart on next call.\nPossible causes:\n1. Code contains emoji/non-ASCII characters (use write_file+exec instead)\n2. Code execution time too long\n3. Infinite loop or waiting for input"
                }
                
            except pexpect.TIMEOUT:
                duration_ms = int((time.time() - start_time) * 1000)
                duration_sec = duration_ms / 1000
                
                # Try to get existing output
                try:
                    partial_output = session.process.before
                except:
                    partial_output = ""
                
                session.error_count += 1
                
                error_msg = f"Command execution timed out ({timeout} seconds)"
                logger.error(f"[exec] {session.session_id}: Timeout (pexpect)! Waited {duration_sec:.1f} seconds")
                logger.error(f"[exec] Partial output (first 500 chars): {str(partial_output)[:500]}")
                
                # ✅ FIX: Also force kill on pexpect timeout for recovery
                logger.warning(f"[exec] {session.session_id}: Force killing timed-out session for recovery")
                try:
                    session.process.kill(9)
                except Exception as kill_err:
                    logger.error(f"[exec] {session.session_id}: Failed to kill process: {kill_err}")
                
                return {
                    "status": "error",
                    "error": error_msg,
                    "output": str(partial_output),
                    "session_id": session.session_id,
                    "duration_ms": duration_ms,
                    "timeout_seconds": timeout,
                    "suggestion": "Command was stuck and the session has been terminated. It will auto-restart on next call.\nPossible causes:\n1. Code contains emoji/non-ASCII characters (use write_file+exec instead)\n2. Code execution time too long\n3. Infinite loop or waiting for input"
                }
            
            except pexpect.EOF:
                session.error_count += 1
                
                return {
                    "status": "error",
                    "error": "Session ended unexpectedly",
                    "session_id": session.session_id,
                    "suggestion": "Session has crashed, will auto-restart on next call"
                }
        
        except Exception as e:
            session.error_count += 1
            logger.error(f"[exec] {session.session_id}: Error - {e}", exc_info=True)
            
            return {
                "status": "error",
                "error": f"Error executing command: {e}",
                "session_id": session.session_id
            }
    
    async def _close_session(self, session_id: str):
        """
        Close a session with proper timeout and resource cleanup.
        
        ✅ Fixes applied:
        - Added timeout to process.wait() to prevent hanging forever
        - Properly close PTY file descriptors to prevent FD leak
        - Force kill if graceful exit fails
        """
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        try:
            if session.is_alive:
                # Try graceful exit
                try:
                    if session.shell_type == "bash":
                        session.process.sendline("exit")
                    elif session.shell_type in ["python", "ipython"]:
                        session.process.sendline("quit()")
                except Exception:
                    pass
                
                # ✅ FIX: Wait with timeout (was hanging forever before)
                try:
                    # Use expect with timeout instead of blocking wait()
                    session.process.expect(pexpect.EOF, timeout=5)
                except (pexpect.TIMEOUT, pexpect.EOF, Exception):
                    pass
                
                # Force kill if still alive
                if session.is_alive:
                    try:
                        session.process.kill(9)
                    except Exception:
                        pass
            
            # ✅ FIX: Explicitly close the PTY file descriptor to prevent FD leak
            try:
                session.process.close(force=True)
            except Exception:
                pass
        
        except Exception as e:
            logger.error(f"[session] Failed to close session {session_id}: {e}")
        
        finally:
            # Always remove from registry
            self.sessions.pop(session_id, None)
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        return {
            "session_id": session_id,
            "shell_type": session.shell_type,
            "user_id": session.user_id,
            "workdir": str(session.workdir),
            "is_alive": session.is_alive,
            "created_at": session.created_at,
            "age_seconds": session.age_seconds,
            "idle_seconds": session.idle_seconds,
            "error_count": session.error_count
        }
    
    def list_sessions(self, user_id: str) -> list:
        """List all user sessions"""
        return [
            self.get_session_info(sid)
            for sid, session in self.sessions.items()
            if session.user_id == user_id
        ]


# Global manager instance
_session_manager = ShellSessionManager()


async def shell_exec(
    context,  # AgentContext
    command: str,
    shell_type: str = "bash",
    new_session: bool = False,
    timeout: int = 300
) -> str:
    """
    Execute command in a persistent session (auto-managed).
    
    Args:
        context: AgentContext
        command: Command to execute
        shell_type: Shell type (bash | python | ipython)
        new_session: Whether to force create a new session
        timeout: Timeout in seconds
    
    Returns:
        JSON formatted execution result
    """
    try:
        # ✅ Check command length (prevent long code causing pexpect issues)
        MAX_COMMAND_LENGTH = 800   # Max characters (lowered from 1500 for safety)
        MAX_COMMAND_LINES = 30     # Max lines (lowered from 50 for safety)
        
        command_lines = command.count('\n') + 1
        command_length = len(command)
        
        # ✅ Detect emoji and non-ASCII characters (these cause pexpect IO hangs)
        has_non_ascii = bool(re.search(r'[^\x00-\x7F]', command))
        # Emoji pattern: covers most common emoji ranges
        has_emoji = bool(re.search(
            r'[\U0001F300-\U0001F9FF\U00002702-\U000027B0\U0000FE00-\U0000FE0F'
            r'\U0000200D\U00002600-\U000026FF\U00002700-\U000027BF]',
            command
        ))
        
        reject_reason = None
        if has_emoji:
            reject_reason = "Code contains emoji characters which cause pexpect IO hangs"
        elif has_non_ascii and command_length > 500:
            reject_reason = f"Code contains non-ASCII characters and is too long ({command_length} chars)"
        elif command_length > MAX_COMMAND_LENGTH or command_lines > MAX_COMMAND_LINES:
            reject_reason = f"Code too long ({command_length} chars, {command_lines} lines, limit: {MAX_COMMAND_LENGTH}/{MAX_COMMAND_LINES})"
        
        if reject_reason:
            logger.warning(
                f"[shell_exec] Command rejected: {reject_reason} "
                f"(chars={command_length}, lines={command_lines}, "
                f"non_ascii={has_non_ascii}, emoji={has_emoji})"
            )
            return json.dumps({
                "status": "error",
                "error": f"Code not suitable for shell_exec: {reject_reason}",
                "details": {
                    "command_length": command_length,
                    "command_lines": command_lines,
                    "max_length": MAX_COMMAND_LENGTH,
                    "max_lines": MAX_COMMAND_LINES,
                    "has_non_ascii": has_non_ascii,
                    "has_emoji": has_emoji
                },
                "suggestion": (
                    "Please use write_file + exec for this code:\n"
                    "1. write_file('script.py', '...your code...')\n"
                    "2. exec('python script.py')\n\n"
                    "This is more stable and avoids pexpect buffer/IO issues with "
                    "long code or special characters (emoji, Chinese, etc.)."
                )
            }, ensure_ascii=False)
        
        # Security check
        from .security import validate_command
        
        # Python/IPython sessions do not need command validation (they run in restricted environment)
        if shell_type == "bash":
            is_safe, error_msg = validate_command(command, context.user_id)
            if not is_safe:
                logger.warning(f"[shell_exec] Command rejected: {command} - {error_msg}")
                return json.dumps({
                    "status": "error",
                    "error": error_msg
                }, ensure_ascii=False)
        
        # Get or create session
        if new_session:
            # Force create new session (close old ones)
            for sid, session in list(_session_manager.sessions.items()):
                if session.user_id == context.user_id and session.shell_type == shell_type:
                    await _session_manager._close_session(sid)
        
        # ✅ Pass context.script_dir as working directory (with date subdirectory)
        logger.info(f"[shell_exec] Requesting shell session, workdir={context.script_dir}")
        session = await _session_manager.get_or_create_session(
            user_id=context.user_id,
            shell_type=shell_type,
            workdir=context.script_dir,
            mcp_server_url=getattr(context, 'mcp_server_url', None),
            mcp_server_type=getattr(context, 'mcp_server_type', 'sse'),
        )
        logger.info(f"[shell_exec] Got session: {session.session_id}, workdir={session.workdir}")
        
        # ✅ Before execution: record existing files with modification times
        # Using mtime allows detection of OVERWRITTEN files (same name, new content)
        before_files: dict = {}
        try:
            if context.script_dir.exists():
                for f in context.script_dir.iterdir():
                    if f.is_file():
                        before_files[f.name] = f.stat().st_mtime
        except Exception as e:
            logger.debug(f"[shell_exec] Cannot read working directory: {e}")
        
        # Execute command (with additional asyncio timeout protection)
        logger.info(f"[shell_exec] Starting execution, setting {timeout} second timeout protection")
        try:
            # Add additional 10 seconds buffer for asyncio timeout
            async_timeout = timeout + 10
            result = await asyncio.wait_for(
                _session_manager.execute_in_session(
                    session=session,
                    command=command,
                    timeout=timeout
                ),
                timeout=async_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"[shell_exec] asyncio timeout protection triggered! Command execution exceeded {async_timeout} seconds")
            
            # ✅ FIX: Force close the stuck session for self-recovery
            logger.warning(f"[shell_exec] Force closing stuck session {session.session_id} for recovery")
            try:
                await _session_manager._close_session(session.session_id)
                logger.info(f"[shell_exec] Successfully closed stuck session {session.session_id}")
            except Exception as close_err:
                logger.error(f"[shell_exec] Failed to close stuck session: {close_err}")
            
            result = {
                "status": "error",
                "error": f"Command execution severely timed out (>{async_timeout} seconds). Session has been terminated and will auto-restart.",
                "session_id": session.session_id,
                "suggestion": (
                    "The session was stuck and has been forcefully closed. It will auto-restart on next call.\n"
                    "Suggestions:\n"
                    "1. Use write_file + exec instead of shell_exec for long/complex code\n"
                    "2. Avoid emoji and non-ASCII characters in shell_exec\n"
                    "3. Check for infinite loops or code waiting for user input"
                )
            }
        
        # ✅ After execution: detect new or modified files (using mtime comparison)
        created_files = []
        try:
            if context.script_dir.exists():
                for f in context.script_dir.iterdir():
                    if not f.is_file():
                        continue
                    
                    file_name = f.name
                    current_mtime = f.stat().st_mtime
                    
                    # Check if file is new or was modified during execution
                    is_new = file_name not in before_files
                    is_modified = (not is_new) and (current_mtime > before_files[file_name])
                    
                    if is_new or is_modified:
                        # Skip intermediate script files
                        if any(file_name.endswith(ext) for ext in ['.py', '.sh', '.js', '.ts']):
                            continue
                        
                        created_files.append({
                            "name": file_name,
                            "path": str(f),
                            "size": f.stat().st_size,
                            "lines": 0
                        })
                        action = "new" if is_new else "modified"
                        logger.info(f"[shell_exec] Detected {action} file: {file_name} ({f.stat().st_size} bytes)")
        except Exception as e:
            logger.debug(f"[shell_exec] File detection failed: {e}")
        
        # ✅ If there are new files, add to result
        if created_files:
            result["created_files"] = created_files
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"[shell_exec] Error: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"Execution failed: {e}"
        }, ensure_ascii=False)


async def shell_session_manage(
    context,  # AgentContext
    action: str,
    session_id: Optional[str] = None
) -> str:
    """
    Manage shell sessions.
    
    Args:
        context: AgentContext
        action: Action type (list | info | close)
        session_id: Session ID (required for some operations)
    
    Returns:
        JSON formatted result
    """
    if action == "list":
        sessions = _session_manager.list_sessions(context.user_id)
        return json.dumps({
            "status": "success",
            "sessions": sessions,
            "count": len(sessions)
        }, ensure_ascii=False)
    
    elif action == "info":
        if not session_id:
            return json.dumps({
                "status": "error",
                "error": "info action requires session_id"
            }, ensure_ascii=False)
        
        info = _session_manager.get_session_info(session_id)
        if info is None:
            return json.dumps({
                "status": "error",
                "error": f"Session not found: {session_id}"
            }, ensure_ascii=False)
        
        # Check permissions
        if info["user_id"] != context.user_id:
            return json.dumps({
                "status": "error",
                "error": "No permission to access this session"
            }, ensure_ascii=False)
        
        return json.dumps({
            "status": "success",
            **info
        }, ensure_ascii=False)
    
    elif action == "close":
        if not session_id:
            return json.dumps({
                "status": "error",
                "error": "close action requires session_id"
            }, ensure_ascii=False)
        
        # Check permissions
        if session_id in _session_manager.sessions:
            session = _session_manager.sessions[session_id]
            if session.user_id != context.user_id:
                return json.dumps({
                    "status": "error",
                    "error": "No permission to access this session"
                }, ensure_ascii=False)
        
        await _session_manager._close_session(session_id)
        
        return json.dumps({
            "status": "success",
            "message": f"Session {session_id} closed"
        }, ensure_ascii=False)
    
    else:
        return json.dumps({
            "status": "error",
            "error": f"Unknown action: {action}"
        }, ensure_ascii=False)

