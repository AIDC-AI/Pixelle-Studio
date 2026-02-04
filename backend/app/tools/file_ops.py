"""
文件操作工具 - read_file, write_file
"""
from pathlib import Path
from typing import Optional
import json
import asyncio
import logging

from .security import validate_path

logger = logging.getLogger(__name__)


async def read_file(
    context,  # AgentContext
    path: str,
    encoding: str = "utf-8"
) -> str:
    """
    读取文件内容
    
    Args:
        context: AgentContext
        path: 文件路径
        encoding: 文件编码
    
    Returns:
        文件内容或错误信息
    """
    try:
        # ✅ 安全检查，传入 script_dir 以支持日期子目录
        resolved_path = validate_path(path, context.user_id, operation="read", script_dir=context.script_dir)
        
        # 检查文件是否存在
        if not resolved_path.exists():
            # 提供更详细的错误信息
            return json.dumps({
                "status": "error",
                "error": f"文件不存在: {path}",
                "resolved_path": str(resolved_path),
                "suggestion": f"确认文件路径是否正确。工作目录: {resolved_path.parent}"
            }, ensure_ascii=False)
        
        if not resolved_path.is_file():
            return json.dumps({
                "status": "error",
                "error": f"不是文件: {path}"
            }, ensure_ascii=False)
        
        # 异步读取文件
        content = await asyncio.to_thread(
            resolved_path.read_text,
            encoding=encoding
        )
        
        # 判断是否是 skill 文件
        is_skill_file = "skills/" in str(resolved_path) or "/skills/" in str(resolved_path)
        
        # 统计信息
        lines = content.count('\n') + 1
        size = len(content)
        
        # 大文件警告（但仍返回完整内容）
        warning = ""
        if not is_skill_file and lines > 1000:
            warning = (
                f"⚠️ 文件较大（{lines} 行，{size} 字节）\n\n"
                f"建议：对于大数据文件，使用 exec 命令查看部分内容：\n"
                f"  - exec(\"head -n 100 {path}\")  # 查看前 100 行\n"
                f"  - exec(\"wc -l {path}\")        # 统计行数\n"
                f"  - exec(\"tail -n 100 {path}\")  # 查看最后 100 行\n\n"
                f"---\n\n"
            )
        
        logger.info(f"[read_file] {path} ({lines} lines, {size} bytes)")
        
        return warning + content
        
    except PermissionError as e:
        logger.error(f"[read_file] Permission denied: {path} - {e}")
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"[read_file] Error reading {path}: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"读取文件失败: {e}"
        }, ensure_ascii=False)


async def write_file(
    context,  # AgentContext
    path: str,
    content: str,
    encoding: str = "utf-8",
    notify_frontend: bool = False
) -> str:
    """
    创建或覆盖文件
    
    Args:
        context: AgentContext
        path: 文件路径
        content: 文件内容
        encoding: 文件编码
        notify_frontend: 是否通知前端（默认False，只有最终用户文件才为True）
    
    Returns:
        JSON 格式的结果
    """
    try:
        # ✅ 如果是相对路径，基于 context.script_dir（包含日期子目录）解析
        # 如果是绝对路径，保持不变
        if not Path(path).is_absolute():
            # 相对路径相对于当前工作目录（包含日期）
            full_path = str(context.script_dir / path)
        else:
            full_path = path
        
        # ✅ 安全检查，传入 script_dir 以支持日期子目录
        resolved_path = validate_path(full_path, context.user_id, operation="write", script_dir=context.script_dir)
        
        # 创建父目录
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ✅ 处理同名文件冲突：自动重命名
        original_path = resolved_path
        if resolved_path.exists():
            stem = resolved_path.stem
            suffix = resolved_path.suffix
            counter = 2
            while resolved_path.exists():
                resolved_path = resolved_path.parent / f"{stem}_{counter}{suffix}"
                counter += 1
            
            logger.info(f"[write_file] 文件已存在，自动重命名: {original_path.name} -> {resolved_path.name}")
        
        # 异步写入文件
        await asyncio.to_thread(
            resolved_path.write_text,
            content,
            encoding=encoding
        )
        
        # 统计信息
        lines = content.count('\n') + 1
        size = len(content)
        
        # 检查是否被重命名
        was_renamed = (resolved_path != original_path)
        
        logger.info(f"[write_file] {resolved_path.name} ({lines} lines, {size} bytes) notify_frontend={notify_frontend}")
        
        result = {
            "status": "success",
            "path": str(resolved_path),
            "relative_path": path,  # 原始相对路径
            "actual_filename": resolved_path.name,  # 实际文件名（可能被重命名）
            "renamed": was_renamed,  # ✅ 总是返回此字段
            "size": size,
            "lines": lines,
            "notify_frontend": notify_frontend,  # ✅ 标记是否通知前端
            "message": f"文件已写入: {resolved_path.name} ({lines} 行，{size} 字节)"
        }
        
        # 如果被重命名，添加额外信息
        if was_renamed:
            result["original_name"] = original_path.name
            result["message"] = f"文件已写入（重命名）: {original_path.name} -> {resolved_path.name} ({lines} 行，{size} 字节)"
        
        return json.dumps(result, ensure_ascii=False)
        
    except PermissionError as e:
        logger.error(f"[write_file] Permission denied: {path} - {e}")
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"[write_file] Error writing {path}: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"写入文件失败: {e}"
        }, ensure_ascii=False)

