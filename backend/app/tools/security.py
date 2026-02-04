"""
安全检查模块 - 路径和命令白名单验证
"""
from pathlib import Path
from typing import Tuple, Optional
import shlex
import logging

logger = logging.getLogger(__name__)


# 命令白名单
ALLOWED_COMMANDS = {
    # 读取类
    "cat", "head", "tail", "less", "more",
    "grep", "egrep", "fgrep", "ag", "rg",
    "find", "ls", "tree", "du", "stat",
    "wc", "cut", "sort", "uniq", "diff",
    
    # 基础命令
    "echo", "pwd", "cd", "mkdir", "touch", "cp", "mv",
    
    # Python
    "python", "python3", "pip", "pip3",
    
    # 其他工具
    "git", "curl", "wget", "jq", "awk", "sed",
    
    # Shell
    "bash", "sh", "zsh"
}

# 命令黑名单（一期禁止删除操作和包安装）
BLOCKED_COMMANDS = {
    # 删除类
    "rm", "rmdir", "unlink", "del",
    
    # 危险命令
    "sudo", "su", "chmod", "chown", "chgrp",
    "kill", "pkill", "killall",
    "dd", "mkfs", "fdisk", "parted",
    
    # 网络危险
    "nc", "netcat", "nmap",
    
    # 系统
    "reboot", "shutdown", "halt", "poweroff", "init",
    
    # 包管理（禁止用户自行安装包）
    "pip", "pip3", "easy_install", "conda",
    "npm", "yarn", "gem", "cargo"
}


def validate_path(
    path: str, 
    user_id: Optional[str], 
    operation: str = "read",
    script_dir: Optional[Path] = None
) -> Path:
    """
    验证并解析路径
    
    Args:
        path: 文件路径
        user_id: 用户ID
        operation: 操作类型 ("read" | "write")
        script_dir: 可选的脚本目录（通常是 context.script_dir，包含日期子目录）
    
    Returns:
        解析后的绝对路径
    
    Raises:
        PermissionError: 路径不被允许
    
    规则:
        - 读取: 允许访问 skills/ (所有skill目录) 和 scripts/{user_id}/
        - 写入: 只允许 scripts/{user_id}/
        - 禁止: 系统目录、其他用户目录、路径遍历
    """
    # 获取 backend 根目录
    # security.py 在 app/tools/ 下，所以需要往上两层到 backend/
    backend_root = Path(__file__).parent.parent.parent
    
    # ✅ 优先使用传入的 script_dir（包含日期子目录）
    # 如果没有提供，使用旧的不带日期的路径（向后兼容）
    if script_dir:
        user_scripts_dir = script_dir
        # 用户目录的父目录（用于权限检查）
        user_scripts_parent = backend_root / "scripts" / (user_id or "default")
    else:
        # 向后兼容：不带日期的路径
        user_scripts_dir = backend_root / "scripts" / (user_id or "default")
        user_scripts_parent = user_scripts_dir
    
    # Skills 目录（包括 default 和用户自己的）
    skills_root = backend_root / "skills"
    default_skills_dir = skills_root / "default"
    user_skills_dir = skills_root / (user_id or "default")
    
    # 解析路径
    if Path(path).is_absolute():
        resolved = Path(path).resolve()
    else:
        # 特殊处理：如果路径以 "skills/" 开头，基于 backend_root 解析
        # 这样 LLM 可以使用 "skills/default/pdf/SKILL.md" 这样的相对路径
        if path.startswith("skills/") or path.startswith("skills\\"):
            resolved = (backend_root / path).resolve()
        else:
            # 其他相对路径基于用户工作目录
            resolved = (user_scripts_dir / path).resolve()
    
    # 规则 1: 写操作只能在用户目录（包括日期子目录）
    if operation == "write":
        if not _is_subpath(resolved, user_scripts_parent):
            raise PermissionError(
                f"写入被拒绝: 只能写入您的工作目录\n"
                f"允许: {user_scripts_parent}\n"
                f"尝试: {resolved}"
            )
        return resolved
    
    # 规则 2: 读操作可以访问 skills（所有子目录）和用户工作目录（包括日期子目录）
    if operation == "read":
        allowed_dirs = [
            user_scripts_parent,   # 用户工作目录（包括所有日期子目录）
            skills_root,           # 所有 skills（包括子目录）
        ]
        
        if any(_is_subpath(resolved, allowed) for allowed in allowed_dirs):
            return resolved
        
        raise PermissionError(
            f"读取被拒绝: 只能读取 skills 目录或您的工作目录\n"
            f"允许目录:\n"
            f"  - 工作目录: {user_scripts_parent}\n"
            f"  - Skills: {skills_root} (及所有子目录)\n"
            f"尝试访问: {resolved}"
        )
    
    raise ValueError(f"未知操作类型: {operation}")


def validate_command(command: str, user_id: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    验证命令是否安全
    
    Args:
        command: 要执行的命令
        user_id: 用户ID
    
    Returns:
        (is_safe, error_message)
        - is_safe: 命令是否安全
        - error_message: 如果不安全，返回错误信息
    """
    # 1. 解析命令
    try:
        tokens = shlex.split(command)
    except ValueError as e:
        return False, f"命令解析失败: {e}"
    
    if not tokens:
        return False, "空命令"
    
    # 提取主命令
    main_command = tokens[0]
    cmd_name = Path(main_command).name
    
    # 2. 检查黑名单
    if cmd_name in BLOCKED_COMMANDS:
        return False, (
            f"命令 '{cmd_name}' 被禁止\n"
            f"原因: 该命令可能造成系统损坏或数据丢失\n"
            f"提示: 一期不支持删除和系统管理操作"
        )
    
    # 2.5 特殊检查：python -m pip 等绕过方式
    if cmd_name in ["python", "python3"]:
        # 检查是否有 -m pip 参数
        if len(tokens) >= 3 and tokens[1] == "-m" and tokens[2] in ["pip", "pip3"]:
            return False, (
                f"禁止使用 'python -m pip' 安装包\n"
                f"原因: 当前环境为共享环境，不支持用户自行安装包\n"
                f"提示: 如需特定包，请联系管理员"
            )
    
    # 3. 检查白名单（可选，目前采用宽松策略）
    # if cmd_name not in ALLOWED_COMMANDS:
    #     return False, f"命令 '{cmd_name}' 不在允许列表中"
    
    # 4. 检查危险模式（放宽限制，&& 和 || 允许）
    dangerous_patterns = [
        (";", "命令注入风险"),
        # && 和 || 是常用功能，允许
        # "|" 和 ">" 允许（管道和重定向是常用功能）
    ]
    
    for pattern, reason in dangerous_patterns:
        if pattern in command:
            # 但允许在字符串中出现
            if f'"{pattern}"' in command or f"'{pattern}'" in command:
                continue
            return False, f"命令包含危险字符 '{pattern}' ({reason})"
    
    # 5. 检查路径参数（如果有文件路径）
    for token in tokens[1:]:
        if token.startswith("-"):
            continue  # 选项参数，跳过
        
        # 检查是否看起来像路径
        if "/" in token or "\\" in token or token.endswith((".txt", ".py", ".csv", ".json")):
            try:
                # 尝试验证路径
                validate_path(token, user_id, operation="read")
            except PermissionError:
                # 路径验证失败，但不一定是错误（可能是参数而非路径）
                # 记录警告但允许执行
                logger.warning(f"Command contains potentially invalid path: {token}")
    
    return True, None


def _is_subpath(path: Path, parent: Path) -> bool:
    """
    检查 path 是否在 parent 目录下
    
    Args:
        path: 要检查的路径
        parent: 父目录
    
    Returns:
        True 如果 path 在 parent 下
    """
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def get_user_workdir(user_id: Optional[str]) -> Path:
    """
    获取用户工作目录
    
    Args:
        user_id: 用户ID
    
    Returns:
        用户工作目录的绝对路径
    """
    # security.py 在 app/tools/ 下，所以需要往上两层到 backend/
    backend_root = Path(__file__).parent.parent.parent
    workdir = backend_root / "scripts" / (user_id or "default")
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir

