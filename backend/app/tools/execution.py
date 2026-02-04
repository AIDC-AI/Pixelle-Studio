"""
命令执行工具 - exec（非持久化版本）
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


# 后台进程注册表
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
    执行一次性命令（非持久化）
    
    Args:
        context: AgentContext
        command: 要执行的命令
        workdir: 工作目录（可选）
        env: 环境变量（可选）
        timeout: 超时时间（秒）
        background: 是否后台运行
    
    Returns:
        JSON 格式的执行结果
    """
    # 1. 命令安全检查
    is_safe, error_msg = validate_command(command, context.user_id)
    if not is_safe:
        logger.warning(f"[exec] Command blocked: {command} - {error_msg}")
        return json.dumps({
            "status": "error",
            "error": error_msg
        }, ensure_ascii=False)
    
    # 2. 确定工作目录
    if workdir:
        try:
            from .security import validate_path
            # ✅ 传入 script_dir 以支持日期子目录
            resolved_workdir = validate_path(workdir, context.user_id, operation="read", script_dir=context.script_dir)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": f"工作目录无效: {e}"
            }, ensure_ascii=False)
    else:
        # ✅ 使用 context.script_dir（包含日期子目录）与 shell_exec 保持一致
        resolved_workdir = context.script_dir
    
    # 3. 准备环境变量
    exec_env = dict(os.environ) if env is None else {**os.environ, **env}
    
    # ✅ 如果命令使用 python，替换为 .venv 中的 Python
    original_command = command
    backend_root = Path(__file__).parent.parent.parent
    venv_python = backend_root / ".venv" / "bin" / "python"
    
    if venv_python.exists():
        # 检查命令是否以 python 开头
        if command.strip().startswith("python ") or command.strip() == "python":
            # 替换为虚拟环境的 Python
            command = command.replace("python ", f"{venv_python} ", 1)
            logger.info(f"[exec] 使用 .venv Python: {venv_python}")
        elif command.strip().startswith("python3 ") or command.strip() == "python3":
            # 替换为虚拟环境的 Python
            command = command.replace("python3 ", f"{venv_python} ", 1)
            logger.info(f"[exec] 使用 .venv Python: {venv_python}")
    else:
        logger.warning(f"[exec] .venv/bin/python 不存在，使用系统 Python")
    
    # 4. 生成会话ID
    session_id = f"exec_{uuid.uuid4().hex[:8]}"
    
    logger.info(f"[exec] {session_id}: {command} (workdir: {resolved_workdir}, background: {background})")
    
    try:
        if background:
            # 后台执行
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(resolved_workdir),
                env=exec_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 注册后台进程
            _background_processes[session_id] = {
                "process": process,
                "command": command,
                "workdir": str(resolved_workdir),
                "started_at": time.time(),
                "user_id": context.user_id,
                "stdout": [],
                "stderr": []
            }
            
            # 启动输出收集任务
            asyncio.create_task(_collect_background_output(session_id))
            
            return json.dumps({
                "status": "running",
                "session_id": session_id,
                "pid": process.pid,
                "message": f"命令已在后台启动 (session_id: {session_id})。使用 process(action='status', session_id='{session_id}') 查看进度。"
            }, ensure_ascii=False)
        
        else:
            # ✅ 执行前：记录现有文件
            before_files = set()
            try:
                if resolved_workdir.exists():
                    before_files = set(f.name for f in resolved_workdir.iterdir() if f.is_file())
            except Exception as e:
                logger.debug(f"[exec] 无法读取工作目录: {e}")
            
            # 同步执行
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
                    # 执行失败
                    error_msg = f"命令执行失败 (退出码 {exit_code})"
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
                
                # ✅ 执行成功后：检测新创建的文件
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
                                    logger.info(f"[exec] 检测到新文件: {file_name} ({file_path.stat().st_size} bytes)")
                except Exception as e:
                    logger.debug(f"[exec] 文件检测失败: {e}")
                
                # 执行成功
                result = {
                    "status": "success",
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "duration_ms": int(duration * 1000)
                }
                
                # ✅ 如果有新文件，添加到结果中
                if created_files:
                    result["created_files"] = created_files
                
                return json.dumps(result, ensure_ascii=False)
                
            except asyncio.TimeoutError:
                # 超时，终止进程
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass
                
                duration = time.time() - start_time
                logger.warning(f"[exec] {session_id}: timeout after {duration:.2f}s")
                
                return json.dumps({
                    "status": "error",
                    "error": f"命令执行超时 ({timeout} 秒)",
                    "duration_ms": int(duration * 1000)
                }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"[exec] {session_id}: error - {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"执行命令时发生错误: {e}"
        }, ensure_ascii=False)


async def _collect_background_output(session_id: str):
    """收集后台进程的输出"""
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
    管理后台进程
    
    Args:
        context: AgentContext
        action: 操作类型 (list | status | logs | kill)
        session_id: 进程会话ID
    
    Returns:
        JSON 格式的结果
    """
    if action == "list":
        # 列出当前用户的所有后台进程
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
                "error": "status 操作需要 session_id"
            }, ensure_ascii=False)
        
        if session_id not in _background_processes:
            return json.dumps({
                "status": "error",
                "error": f"会话不存在: {session_id}"
            }, ensure_ascii=False)
        
        proc_info = _background_processes[session_id]
        
        # 检查用户权限
        if proc_info["user_id"] != context.user_id:
            return json.dumps({
                "status": "error",
                "error": "无权访问该会话"
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
                "error": "logs 操作需要 session_id"
            }, ensure_ascii=False)
        
        if session_id not in _background_processes:
            return json.dumps({
                "status": "error",
                "error": f"会话不存在: {session_id}"
            }, ensure_ascii=False)
        
        proc_info = _background_processes[session_id]
        
        # 检查用户权限
        if proc_info["user_id"] != context.user_id:
            return json.dumps({
                "status": "error",
                "error": "无权访问该会话"
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
                "error": "kill 操作需要 session_id"
            }, ensure_ascii=False)
        
        if session_id not in _background_processes:
            return json.dumps({
                "status": "error",
                "error": f"会话不存在: {session_id}"
            }, ensure_ascii=False)
        
        proc_info = _background_processes[session_id]
        
        # 检查用户权限
        if proc_info["user_id"] != context.user_id:
            return json.dumps({
                "status": "error",
                "error": "无权访问该会话"
            }, ensure_ascii=False)
        
        process = proc_info["process"]
        
        if process.returncode is not None:
            return json.dumps({
                "status": "success",
                "message": "进程已结束",
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
                "message": "进程已终止",
                "session_id": session_id
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"[process] Failed to kill {session_id}: {e}")
            return json.dumps({
                "status": "error",
                "error": f"终止进程失败: {e}"
            }, ensure_ascii=False)
    
    else:
        return json.dumps({
            "status": "error",
            "error": f"未知操作: {action}"
        }, ensure_ascii=False)


# 导入 os 模块
import os

