"""
持久化 Shell 会话管理 - 基于 pexpect
支持变量持久化和多步执行
"""
import asyncio
import pexpect
import uuid
import time
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass

from .security import get_user_workdir

logger = logging.getLogger(__name__)


@dataclass
class ShellSession:
    """单个 Shell 会话"""
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
        """检查进程是否还活着"""
        return self.process.isalive()
    
    @property
    def age_seconds(self) -> float:
        """会话年龄（秒）"""
        return time.time() - self.created_at
    
    @property
    def idle_seconds(self) -> float:
        """空闲时间（秒）"""
        return time.time() - self.last_activity


class ShellSessionManager:
    """持久化 Shell 会话管理器（自动管理）"""
    
    # 配置
    MAX_IDLE_TIME = 600  # 10分钟无活动自动关闭（降低到10分钟）
    MAX_SESSION_AGE = 3600  # 1小时最大生命周期（降低到1小时）
    MAX_ERROR_COUNT = 3  # 连续3次错误自动关闭（更严格）
    MAX_SESSIONS_PER_USER = 3  # 每个用户最多3个会话
    MAX_TOTAL_SESSIONS = 20  # 全局最多20个会话
    
    def __init__(self):
        self.sessions: Dict[str, ShellSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def start_cleanup_task(self):
        """启动自动清理任务"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._auto_cleanup())
    
    async def _auto_cleanup(self):
        """自动清理过期会话"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次（更频繁）
                
                # 收集需要关闭的会话
                to_close = []
                for sid, session in self.sessions.items():
                    # 检查是否需要清理
                    if not session.is_alive:
                        to_close.append((sid, "进程已结束"))
                    elif session.idle_seconds > self.MAX_IDLE_TIME:
                        to_close.append((sid, f"空闲超时 ({session.idle_seconds:.0f}s)"))
                    elif session.age_seconds > self.MAX_SESSION_AGE:
                        to_close.append((sid, f"会话超时 ({session.age_seconds:.0f}s)"))
                    elif session.error_count >= self.MAX_ERROR_COUNT:
                        to_close.append((sid, f"错误过多 ({session.error_count})"))
                
                # 关闭会话
                for sid, reason in to_close:
                    logger.info(f"[cleanup] 关闭会话 {sid}: {reason}")
                    await self._close_session(sid)
                
                # 检查总会话数
                if len(self.sessions) > self.MAX_TOTAL_SESSIONS:
                    logger.warning(f"[cleanup] 总会话数超限 ({len(self.sessions)} > {self.MAX_TOTAL_SESSIONS})")
                    await self._emergency_cleanup()
                    
            except Exception as e:
                logger.error(f"[cleanup] 清理任务错误: {e}")
    
    async def _emergency_cleanup(self):
        """紧急清理：关闭最老的空闲会话"""
        logger.warning("[cleanup] 执行紧急清理")
        
        # 按照空闲时间排序，关闭最老的会话
        sessions_by_idle = sorted(
            self.sessions.items(),
            key=lambda x: x[1].last_activity
        )
        
        # 关闭前10个最老的会话
        for sid, session in sessions_by_idle[:10]:
            logger.warning(f"[cleanup] 紧急关闭会话 {sid} (空闲 {session.idle_seconds:.0f}s)")
            await self._close_session(sid)
    
    def _count_user_sessions(self, user_id: str) -> int:
        """统计用户的会话数量"""
        return sum(1 for s in self.sessions.values() if s.user_id == user_id)
    
    async def _cleanup_old_user_sessions(self, user_id: str, shell_type: str):
        """清理用户的旧会话（如果超过限制）"""
        user_sessions = [
            (sid, s) for sid, s in self.sessions.items()
            if s.user_id == user_id and s.shell_type == shell_type
        ]
        
        if len(user_sessions) >= self.MAX_SESSIONS_PER_USER:
            # 按活动时间排序，关闭最老的
            user_sessions.sort(key=lambda x: x[1].last_activity)
            for sid, session in user_sessions[:-1]:  # 保留最新的一个
                logger.info(f"[cleanup] 关闭用户 {user_id} 的旧会话 {sid}")
                await self._close_session(sid)
    
    async def get_or_create_session(
        self,
        user_id: str,
        shell_type: str = "bash",
        workdir: Optional[Path] = None
    ) -> ShellSession:
        """
        获取或创建会话（自动管理）
        
        策略：
        1. 查找该用户的现有会话（相同 shell_type）
        2. 如果有且活跃，复用
        3. 否则创建新会话
        
        Args:
            user_id: 用户ID
            shell_type: Shell 类型
            workdir: 可选的工作目录（如果不提供则使用默认）
        """
        # ✅ 先检查并清理超限的会话
        if len(self.sessions) >= self.MAX_TOTAL_SESSIONS:
            logger.warning(f"[session] 总会话数达到上限 ({len(self.sessions)}), 执行清理")
            await self._emergency_cleanup()
        
        # ✅ 检查用户会话数
        if self._count_user_sessions(user_id) >= self.MAX_SESSIONS_PER_USER:
            logger.info(f"[session] 用户 {user_id} 会话数达到上限，清理旧会话")
            await self._cleanup_old_user_sessions(user_id, shell_type)
        
        # 查找现有会话
        for session in list(self.sessions.values()):
            if (session.user_id == user_id and 
                session.shell_type == shell_type and 
                session.is_alive):
                # ✅ 如果指定了 workdir，检查是否匹配
                if workdir is not None:
                    # 转换为 Path 对象进行比较（确保类型一致）
                    session_workdir = Path(session.workdir) if not isinstance(session.workdir, Path) else session.workdir
                    requested_workdir = Path(workdir) if not isinstance(workdir, Path) else workdir
                    
                    # 解析为绝对路径后比较
                    if session_workdir.resolve() != requested_workdir.resolve():
                        # 工作目录不匹配，关闭旧会话并创建新的
                        logger.info(f"[session] 工作目录不匹配，关闭旧会话: {session.session_id}")
                        logger.info(f"[session]   旧: {session_workdir.resolve()}")
                        logger.info(f"[session]   新: {requested_workdir.resolve()}")
                        await self._close_session(session.session_id)
                        continue
                
                # 复用现有会话
                session.last_activity = time.time()
                logger.info(f"[session] 复用会话: {session.session_id} (workdir: {session.workdir})")
                return session
        
        # 创建新会话
        session_id = f"{shell_type}_{uuid.uuid4().hex[:8]}"
        
        # ✅ 使用提供的 workdir 或默认的用户目录
        if workdir is None:
            workdir = get_user_workdir(user_id)
        else:
            # 确保目录存在
            workdir.mkdir(parents=True, exist_ok=True)
        
        # ✅ 启动进程前，检查PTY资源
        try:
            import os as os_module
            # 尝试检测可用的PTY数量
            pty_count = len([f for f in os_module.listdir('/dev') if f.startswith('pty')])
            logger.debug(f"[session] 当前PTY设备数: {pty_count}")
        except Exception as e:
            logger.debug(f"[session] 无法检测PTY数量: {e}")
        
        # 启动进程
        if shell_type == "bash":
            try:
                process = pexpect.spawn(
                    "/bin/bash",
                    ["--norc", "--noprofile"],  # 不加载配置文件
                    cwd=str(workdir),
                    encoding='utf-8',
                    timeout=300,
                    maxread=10000  # 限制单次读取
                )
            except OSError as e:
                if 'out of pty devices' in str(e):
                    logger.error("[session] PTY资源耗尽！执行紧急清理")
                    await self._emergency_cleanup()
                    # 重试一次
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
            # Bash prompt 设置
            process.sendline('export PS1="READY> "')
            process.expect("READY> ", timeout=5)
            prompt = r"READY> "
            
        elif shell_type == "python":
            # ✅ 使用 .venv 中的 Python（包含所有已安装的包）
            backend_root = Path(__file__).parent.parent.parent
            venv_python = backend_root / ".venv" / "bin" / "python"
            
            if venv_python.exists():
                python_cmd = str(venv_python)
                logger.info(f"[shell_session] 使用 .venv Python: {python_cmd}")
            else:
                # 降级到系统 Python
                python_cmd = "python3"
                logger.warning("[shell_session] .venv/bin/python 不存在，使用系统 Python")
            
            try:
                process = pexpect.spawn(
                    python_cmd,
                    ["-u"],  # 无缓冲输出
                    cwd=str(workdir),
                    encoding='utf-8',
                    timeout=300,
                    maxread=10000
                )
            except OSError as e:
                if 'out of pty devices' in str(e):
                    logger.error("[session] PTY资源耗尽！执行紧急清理")
                    await self._emergency_cleanup()
                    # 重试一次
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
            # ✅ 使用 .venv 中的 IPython（如果存在）
            backend_root = Path(__file__).parent.parent.parent
            venv_ipython = backend_root / ".venv" / "bin" / "ipython"
            
            if venv_ipython.exists():
                ipython_cmd = str(venv_ipython)
                logger.info(f"[shell_session] 使用 .venv IPython: {ipython_cmd}")
            else:
                # 降级到系统 IPython
                ipython_cmd = "ipython"
                logger.warning("[shell_session] .venv/bin/ipython 不存在，使用系统 IPython")
            
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
                    logger.error("[session] PTY资源耗尽！执行紧急清理")
                    await self._emergency_cleanup()
                    # 重试一次
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
            raise ValueError(f"不支持的 shell 类型: {shell_type}")
        
        session = ShellSession(
            session_id=session_id,
            shell_type=shell_type,
            user_id=user_id,
            workdir=workdir,
            process=process,
            created_at=time.time(),
            last_activity=time.time()
        )
        
        # 保存 prompt 模式
        session._prompt = prompt
        
        self.sessions[session_id] = session
        
        logger.info(f"[session] 创建新会话: {session_id} ({shell_type}, user: {user_id})")
        
        # 确保清理任务运行
        self.start_cleanup_task()
        
        return session
    
    async def execute_in_session(
        self,
        session: ShellSession,
        command: str,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        在会话中执行命令
        
        Returns:
            {"status": "success"|"error", "output": str, ...}
        """
        session.last_activity = time.time()
        
        if not session.is_alive:
            session.error_count += 1
            return {
                "status": "error",
                "error": "会话已结束",
                "session_id": session.session_id
            }
        
        try:
            # 清空缓冲区
            try:
                session.process.read_nonblocking(size=10000, timeout=0)
            except:
                pass
            
            # ✅ 确保 Python shell 在正确的工作目录下执行
            is_python_shell = session.shell_type in ["python", "ipython"]
            if is_python_shell:
                # 在执行用户命令前，先切换到正确的工作目录
                chdir_command = f"import os; os.chdir({repr(str(session.workdir))})"
                session.process.sendline(f"exec(compile({repr(chdir_command)}, '<string>', 'exec'))")
                
                # 等待 chdir 完成（不捕获输出）
                try:
                    session.process.expect(session._prompt, timeout=2)
                except Exception as e:
                    logger.debug(f"[exec] chdir 等待超时（可能已完成）: {e}")
            
            # ✅ 对于 Python/IPython 的多行代码，使用特殊处理
            is_multiline = '\n' in command.strip()
            actual_command = command
            
            if is_python_shell and is_multiline:
                # 多行 Python 代码：使用 exec() 包装
                # 使用 repr() 来安全地转义代码字符串
                logger.debug(f"[exec] 执行多行代码: {len(command)} 字符")
                
                # 安全转义：使用 repr() 自动处理所有特殊字符
                escaped = repr(command)
                actual_command = f"exec(compile({escaped}, '<string>', 'exec'))"
                logger.debug(f"[exec] 包装后: {actual_command[:100]}...")
            
            # 发送命令
            logger.info(f"[exec] {session.session_id}: 开始执行命令，超时={timeout}秒")
            logger.debug(f"[exec] 命令内容（前200字符）: {actual_command[:200]}")
            session.process.sendline(actual_command)
            logger.debug(f"[exec] 命令已发送，等待响应...")
            
            # 等待输出和下一个 prompt
            start_time = time.time()
            
            try:
                # 等待 prompt 重新出现
                logger.debug(f"[exec] 等待 prompt，超时={timeout}秒")
                session.process.expect(session._prompt, timeout=timeout)
                logger.debug(f"[exec] 收到 prompt 响应")
                
                # 获取输出
                output = session.process.before
                
                # 清理输出（移除回显的命令）
                lines = output.split('\n')
                
                # ✅ 移除回显的命令（可能是原始命令或包装后的命令）
                if lines:
                    first_line = lines[0].strip()
                    # 检查第一行是否是回显的命令
                    if first_line == command.strip() or first_line == actual_command.strip():
                        lines = lines[1:]
                    # 如果是 exec(compile(...))，也移除
                    elif first_line.startswith('exec(compile('):
                        lines = lines[1:]
                
                cleaned_output = '\n'.join(lines).strip()
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                # 重置错误计数
                session.error_count = 0
                
                logger.info(f"[exec] {session.session_id}: 命令执行成功 ({duration_ms}ms)")
                
                return {
                    "status": "success",
                    "output": cleaned_output,
                    "session_id": session.session_id,
                    "duration_ms": duration_ms
                }
                
            except pexpect.TIMEOUT:
                duration_ms = int((time.time() - start_time) * 1000)
                duration_sec = duration_ms / 1000
                
                # 尝试获取已有输出
                try:
                    partial_output = session.process.before
                except:
                    partial_output = ""
                
                session.error_count += 1
                
                error_msg = f"⚠️ 命令执行超时 ({timeout} 秒)"
                logger.error(f"[exec] {session.session_id}: 超时！已等待 {duration_sec:.1f}秒")
                logger.error(f"[exec] 部分输出（前500字符）: {partial_output[:500]}")
                
                return {
                    "status": "error",
                    "error": error_msg,
                    "output": partial_output,
                    "session_id": session.session_id,
                    "duration_ms": duration_ms,
                    "timeout_seconds": timeout,
                    "suggestion": "命令可能卡住了。可能的原因：\n1. 代码执行时间过长\n2. 等待用户输入\n3. 死循环或资源不足\n建议：检查代码逻辑，减少数据量，或增加timeout参数"
                }
            
            except pexpect.EOF:
                session.error_count += 1
                
                return {
                    "status": "error",
                    "error": "会话意外结束",
                    "session_id": session.session_id,
                    "suggestion": "会话已崩溃，将在下次调用时自动重启"
                }
        
        except Exception as e:
            session.error_count += 1
            logger.error(f"[exec] {session.session_id}: 错误 - {e}", exc_info=True)
            
            return {
                "status": "error",
                "error": f"执行命令时发生错误: {e}",
                "session_id": session.session_id
            }
    
    async def _close_session(self, session_id: str):
        """关闭会话"""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        
        try:
            if session.is_alive:
                # 尝试优雅退出
                if session.shell_type == "bash":
                    session.process.sendline("exit")
                elif session.shell_type in ["python", "ipython"]:
                    session.process.sendline("quit()")
                
                # 等待进程结束
                try:
                    session.process.wait()
                except:
                    pass
                
                # 强制关闭
                if session.is_alive:
                    session.process.kill(9)
        
        except Exception as e:
            logger.error(f"[session] 关闭会话失败 {session_id}: {e}")
        
        finally:
            del self.sessions[session_id]
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
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
        """列出用户的所有会话"""
        return [
            self.get_session_info(sid)
            for sid, session in self.sessions.items()
            if session.user_id == user_id
        ]


# 全局管理器实例
_session_manager = ShellSessionManager()


async def shell_exec(
    context,  # AgentContext
    command: str,
    shell_type: str = "bash",
    new_session: bool = False,
    timeout: int = 300
) -> str:
    """
    在持久化会话中执行命令（自动管理）
    
    Args:
        context: AgentContext
        command: 要执行的命令
        shell_type: Shell 类型 (bash | python | ipython)
        new_session: 是否强制创建新会话
        timeout: 超时时间（秒）
    
    Returns:
        JSON 格式的执行结果
    """
    try:
        # ✅ 检查命令长度（防止长代码导致pexpect问题）
        MAX_COMMAND_LENGTH = 1500  # 最大字符数
        MAX_COMMAND_LINES = 50     # 最大行数
        
        command_lines = command.count('\n') + 1
        command_length = len(command)
        
        if command_length > MAX_COMMAND_LENGTH or command_lines > MAX_COMMAND_LINES:
            logger.warning(
                f"[shell_exec] 命令过长: {command_length} 字符, {command_lines} 行 "
                f"(限制: {MAX_COMMAND_LENGTH} 字符, {MAX_COMMAND_LINES} 行)"
            )
            return json.dumps({
                "status": "error",
                "error": f"⚠️ 代码过长，不适合在 shell_exec 中执行",
                "details": {
                    "command_length": command_length,
                    "command_lines": command_lines,
                    "max_length": MAX_COMMAND_LENGTH,
                    "max_lines": MAX_COMMAND_LINES
                },
                "suggestion": (
                    "请使用 write_file + exec 的方式执行长代码：\n"
                    "1. write_file('script.py', '...你的代码...')\n"
                    "2. exec('python script.py')\n\n"
                    "这样更稳定可靠，避免 pexpect 缓冲区问题。"
                )
            }, ensure_ascii=False)
        
        # 安全检查
        from .security import validate_command
        
        # Python/IPython 会话不需要命令验证（它们运行在受限环境中）
        if shell_type == "bash":
            is_safe, error_msg = validate_command(command, context.user_id)
            if not is_safe:
                logger.warning(f"[shell_exec] 命令被拒绝: {command} - {error_msg}")
                return json.dumps({
                    "status": "error",
                    "error": error_msg
                }, ensure_ascii=False)
        
        # 获取或创建会话
        if new_session:
            # 强制创建新会话（关闭旧的）
            for sid, session in list(_session_manager.sessions.items()):
                if session.user_id == context.user_id and session.shell_type == shell_type:
                    await _session_manager._close_session(sid)
        
        # ✅ 传递 context.script_dir 作为工作目录（包含日期子目录）
        logger.info(f"[shell_exec] 请求 shell 会话，workdir={context.script_dir}")
        session = await _session_manager.get_or_create_session(
            user_id=context.user_id,
            shell_type=shell_type,
            workdir=context.script_dir
        )
        logger.info(f"[shell_exec] 获得会话: {session.session_id}, workdir={session.workdir}")
        
        # ✅ 执行前：记录现有文件
        before_files = set()
        try:
            if context.script_dir.exists():
                before_files = set(f.name for f in context.script_dir.iterdir() if f.is_file())
        except Exception as e:
            logger.debug(f"[shell_exec] 无法读取工作目录: {e}")
        
        # 执行命令（带额外的asyncio超时保护）
        logger.info(f"[shell_exec] 开始执行，设置 {timeout}秒超时保护")
        try:
            # 添加额外10秒的缓冲时间给asyncio超时
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
            logger.error(f"[shell_exec] asyncio超时保护触发！命令执行超过 {async_timeout} 秒")
            result = {
                "status": "error",
                "error": f"⚠️ 命令执行严重超时 (>{async_timeout}秒)",
                "session_id": session.session_id,
                "suggestion": "命令可能完全卡住。建议：\n1. 检查代码是否有死循环\n2. 检查是否在等待用户输入\n3. 尝试使用new_session=True强制创建新会话"
            }
        
        # ✅ 执行后：检测新文件
        after_files = set()
        created_files = []
        try:
            if context.script_dir.exists():
                after_files = set(f.name for f in context.script_dir.iterdir() if f.is_file())
                new_file_names = after_files - before_files
                
                if new_file_names:
                    for file_name in new_file_names:
                        file_path = context.script_dir / file_name
                        if file_path.exists():
                            created_files.append({
                                "name": file_name,
                                "path": str(file_path),
                                "size": file_path.stat().st_size,
                                "lines": len(file_path.read_text(errors='ignore').splitlines()) if file_path.suffix in ['.py', '.txt', '.md', '.sh'] else 0
                            })
                            logger.info(f"[shell_exec] 检测到新文件: {file_name} ({file_path.stat().st_size} bytes)")
        except Exception as e:
            logger.debug(f"[shell_exec] 文件检测失败: {e}")
        
        # ✅ 如果有新文件，添加到结果中
        if created_files:
            result["created_files"] = created_files
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"[shell_exec] 错误: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"执行失败: {e}"
        }, ensure_ascii=False)


async def shell_session_manage(
    context,  # AgentContext
    action: str,
    session_id: Optional[str] = None
) -> str:
    """
    管理 Shell 会话
    
    Args:
        context: AgentContext
        action: 操作类型 (list | info | close)
        session_id: 会话 ID（某些操作需要）
    
    Returns:
        JSON 格式的结果
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
                "error": "info 操作需要 session_id"
            }, ensure_ascii=False)
        
        info = _session_manager.get_session_info(session_id)
        if info is None:
            return json.dumps({
                "status": "error",
                "error": f"会话不存在: {session_id}"
            }, ensure_ascii=False)
        
        # 检查权限
        if info["user_id"] != context.user_id:
            return json.dumps({
                "status": "error",
                "error": "无权访问该会话"
            }, ensure_ascii=False)
        
        return json.dumps({
            "status": "success",
            **info
        }, ensure_ascii=False)
    
    elif action == "close":
        if not session_id:
            return json.dumps({
                "status": "error",
                "error": "close 操作需要 session_id"
            }, ensure_ascii=False)
        
        # 检查权限
        if session_id in _session_manager.sessions:
            session = _session_manager.sessions[session_id]
            if session.user_id != context.user_id:
                return json.dumps({
                    "status": "error",
                    "error": "无权访问该会话"
                }, ensure_ascii=False)
        
        await _session_manager._close_session(session_id)
        
        return json.dumps({
            "status": "success",
            "message": f"会话 {session_id} 已关闭"
        }, ensure_ascii=False)
    
    else:
        return json.dumps({
            "status": "error",
            "error": f"未知操作: {action}"
        }, ensure_ascii=False)

