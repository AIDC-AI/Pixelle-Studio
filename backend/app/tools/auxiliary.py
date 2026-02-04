"""
辅助工具 - edit_file, grep, find, ls
"""
import asyncio
import json
import re
import subprocess
from pathlib import Path
from typing import Optional, List

from .security import validate_path, get_user_workdir

import logging
logger = logging.getLogger(__name__)


async def edit_file(
    context,  # AgentContext
    path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False
) -> str:
    """
    编辑文件（字符串替换）
    
    Args:
        context: AgentContext
        path: 文件路径
        old_string: 要替换的字符串
        new_string: 替换后的字符串
        replace_all: 是否替换所有匹配（默认只替换第一个）
    
    Returns:
        JSON 格式的结果
    """
    try:
        # ✅ 安全检查，传入 script_dir 以支持日期子目录
        resolved_path = validate_path(path, context.user_id, operation="write", script_dir=context.script_dir)
        
        # 检查文件是否存在
        if not resolved_path.exists():
            return json.dumps({
                "status": "error",
                "error": f"文件不存在: {path}"
            }, ensure_ascii=False)
        
        # 读取文件
        content = await asyncio.to_thread(
            resolved_path.read_text,
            encoding='utf-8'
        )
        
        # 检查 old_string 是否存在
        if old_string not in content:
            # 查找相似内容
            lines = content.split('\n')
            similar_lines = [
                (i+1, line) for i, line in enumerate(lines)
                if old_string[:20] in line or any(
                    word in line for word in old_string.split() if len(word) > 3
                )
            ]
            
            error_msg = f"未找到要替换的字符串\n\n"
            if similar_lines:
                error_msg += "可能的相似行:\n"
                for line_no, line in similar_lines[:3]:
                    error_msg += f"  行 {line_no}: {line[:100]}\n"
            
            return json.dumps({
                "status": "error",
                "error": error_msg
            }, ensure_ascii=False)
        
        # 执行替换
        if replace_all:
            new_content = content.replace(old_string, new_string)
            count = content.count(old_string)
        else:
            # 只替换第一个
            new_content = content.replace(old_string, new_string, 1)
            count = 1
        
        # 写入文件
        await asyncio.to_thread(
            resolved_path.write_text,
            new_content,
            encoding='utf-8'
        )
        
        logger.info(f"[edit_file] {path}: 替换 {count} 处")
        
        return json.dumps({
            "status": "success",
            "path": str(resolved_path),
            "replacements": count,
            "message": f"已替换 {count} 处"
        }, ensure_ascii=False)
        
    except PermissionError as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"[edit_file] 错误: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"编辑文件失败: {e}"
        }, ensure_ascii=False)


async def grep(
    context,  # AgentContext
    pattern: str,
    path: str,
    case_insensitive: bool = False,
    recursive: bool = False,
    context_lines: int = 0
) -> str:
    """
    搜索文件内容
    
    Args:
        context: AgentContext
        pattern: 搜索模式（支持正则表达式）
        path: 文件或目录路径
        case_insensitive: 忽略大小写
        recursive: 递归搜索目录
        context_lines: 显示上下文行数
    
    Returns:
        JSON 格式的结果
    """
    try:
        # ✅ 安全检查，传入 script_dir 以支持日期子目录
        resolved_path = validate_path(path, context.user_id, operation="read", script_dir=context.script_dir)
        
        if not resolved_path.exists():
            return json.dumps({
                "status": "error",
                "error": f"路径不存在: {path}"
            }, ensure_ascii=False)
        
        results = []
        
        if resolved_path.is_file():
            # 搜索单个文件
            matches = await _grep_file(
                resolved_path, 
                pattern, 
                case_insensitive, 
                context_lines
            )
            if matches:
                results.append({
                    "file": str(resolved_path),
                    "matches": matches
                })
        
        elif resolved_path.is_dir() and recursive:
            # 递归搜索目录
            for file_path in resolved_path.rglob("*"):
                if file_path.is_file():
                    try:
                        matches = await _grep_file(
                            file_path, 
                            pattern, 
                            case_insensitive, 
                            context_lines
                        )
                        if matches:
                            results.append({
                                "file": str(file_path),
                                "matches": matches
                            })
                    except:
                        pass  # 跳过无法读取的文件
        
        else:
            return json.dumps({
                "status": "error",
                "error": "路径必须是文件，或使用 recursive=True 搜索目录"
            }, ensure_ascii=False)
        
        # 格式化输出
        if not results:
            output = f"未找到匹配 '{pattern}' 的内容"
        else:
            output_lines = []
            for result in results:
                output_lines.append(f"\n文件: {result['file']}")
                for match in result['matches']:
                    output_lines.append(f"  行 {match['line_number']}: {match['line']}")
                    if 'context' in match:
                        for ctx_line in match['context']:
                            output_lines.append(f"       {ctx_line}")
            output = '\n'.join(output_lines)
        
        return json.dumps({
            "status": "success",
            "pattern": pattern,
            "results": results,
            "total_matches": sum(len(r['matches']) for r in results),
            "output": output
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"[grep] 错误: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"搜索失败: {e}"
        }, ensure_ascii=False)


async def _grep_file(
    file_path: Path, 
    pattern: str, 
    case_insensitive: bool,
    context_lines: int
) -> List[dict]:
    """搜索单个文件"""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        # 编译正则表达式
        flags = re.IGNORECASE if case_insensitive else 0
        regex = re.compile(pattern, flags)
        
        matches = []
        for i, line in enumerate(lines):
            if regex.search(line):
                match_info = {
                    "line_number": i + 1,
                    "line": line
                }
                
                # 添加上下文
                if context_lines > 0:
                    context = []
                    for j in range(max(0, i - context_lines), min(len(lines), i + context_lines + 1)):
                        if j != i:
                            context.append(f"{j+1}: {lines[j]}")
                    match_info["context"] = context
                
                matches.append(match_info)
        
        return matches
        
    except Exception:
        return []


async def find(
    context,  # AgentContext
    pattern: str,
    directory: str = "."
) -> str:
    """
    查找文件（按文件名）
    
    Args:
        context: AgentContext
        pattern: 文件名模式（支持 glob，如 *.py）
        directory: 搜索目录
    
    Returns:
        JSON 格式的结果
    """
    try:
        # ✅ 安全检查，传入 script_dir 以支持日期子目录
        resolved_dir = validate_path(directory, context.user_id, operation="read", script_dir=context.script_dir)
        
        if not resolved_dir.exists():
            return json.dumps({
                "status": "error",
                "error": f"目录不存在: {directory}"
            }, ensure_ascii=False)
        
        if not resolved_dir.is_dir():
            return json.dumps({
                "status": "error",
                "error": f"不是目录: {directory}"
            }, ensure_ascii=False)
        
        # 使用 glob 搜索
        matches = list(resolved_dir.rglob(pattern))
        
        # 过滤和格式化结果
        files = []
        dirs = []
        
        for match in matches:
            rel_path = str(match.relative_to(resolved_dir))
            if match.is_file():
                files.append({
                    "path": str(match),
                    "name": match.name,
                    "size": match.stat().st_size
                })
            elif match.is_dir():
                dirs.append({
                    "path": str(match),
                    "name": match.name
                })
        
        # 格式化输出
        output_lines = []
        if files:
            output_lines.append(f"文件 ({len(files)}):")
            for f in files[:20]:  # 限制显示数量
                output_lines.append(f"  {f['path']}")
        if dirs:
            output_lines.append(f"\n目录 ({len(dirs)}):")
            for d in dirs[:20]:
                output_lines.append(f"  {d['path']}/")
        
        if not files and not dirs:
            output_lines.append(f"未找到匹配 '{pattern}' 的文件或目录")
        
        return json.dumps({
            "status": "success",
            "pattern": pattern,
            "files": files,
            "dirs": dirs,
            "total": len(files) + len(dirs),
            "output": '\n'.join(output_lines)
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"[find] 错误: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"查找失败: {e}"
        }, ensure_ascii=False)


async def ls(
    context,  # AgentContext
    path: str = ".",
    recursive: bool = False,
    show_hidden: bool = False,
    limit: int = 10,
    pattern: Optional[str] = None
) -> str:
    """
    列出目录内容
    
    Args:
        context: AgentContext
        path: 目录路径
        recursive: 递归列出子目录
        show_hidden: 显示隐藏文件
        limit: 最多返回的条目数（默认10，避免爆上下文）
        pattern: 文件名过滤模式（支持通配符，如 "*.pdf"）
    
    Returns:
        JSON 格式的结果
    """
    try:
        # ✅ 安全检查，传入 script_dir 以支持日期子目录
        resolved_path = validate_path(path, context.user_id, operation="read", script_dir=context.script_dir)
        
        if not resolved_path.exists():
            return json.dumps({
                "status": "error",
                "error": f"路径不存在: {path}"
            }, ensure_ascii=False)
        
        if not resolved_path.is_dir():
            # 如果是文件，返回文件信息
            stat = resolved_path.stat()
            return json.dumps({
                "status": "success",
                "type": "file",
                "path": str(resolved_path),
                "name": resolved_path.name,
                "size": stat.st_size,
                "output": f"文件: {resolved_path.name} ({stat.st_size} 字节)"
            }, ensure_ascii=False)
        
        # 列出目录内容
        items = []
        
        if recursive:
            # 递归列出
            for item in resolved_path.rglob("*"):
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                # ✅ 应用pattern过滤
                if pattern and not item.match(pattern):
                    continue
                
                rel_path = str(item.relative_to(resolved_path))
                stat = item.stat()
                
                items.append({
                    "path": str(item),
                    "name": rel_path,
                    "type": "dir" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None
                })
        else:
            # 只列出当前目录
            for item in resolved_path.iterdir():
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                # ✅ 应用pattern过滤
                if pattern:
                    import fnmatch
                    if not fnmatch.fnmatch(item.name, pattern):
                        continue
                
                stat = item.stat()
                
                items.append({
                    "path": str(item),
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None
                })
        
        # 排序（目录在前，按名称）
        items.sort(key=lambda x: (x['type'] != 'dir', x['name']))
        
        # 检查是否超过限制
        total_items = len(items)
        truncated = total_items > limit
        if truncated:
            items = items[:limit]
        
        # 格式化输出
        output_lines = [f"目录: {resolved_path}"]
        if pattern:
            output_lines[0] += f" (过滤: {pattern})"
        output_lines[0] += "\n"
        
        if truncated:
            output_lines.append(f"⚠️ 警告: 目录包含 {total_items} 个项目，仅显示前 {limit} 个\n")
            output_lines.append(f"建议: 使用 pattern 参数过滤，如 ls(path='.', pattern='*.pdf', limit=20)\n")
        
        dirs = [i for i in items if i['type'] == 'dir']
        files = [i for i in items if i['type'] == 'file']
        
        if dirs:
            output_lines.append(f"目录 ({len(dirs)}):")
            for d in dirs:
                output_lines.append(f"  {d['name']}/")
        
        if files:
            output_lines.append(f"\n文件 ({len(files)}):")
            for f in files:
                size_str = f"{f['size']:,}" if f['size'] is not None else "?"
                output_lines.append(f"  {f['name']} ({size_str} 字节)")
        
        if not items:
            output_lines.append("(空目录)")
        
        result = {
            "status": "success",
            "path": str(resolved_path),
            "items": items,
            "total": len(items),
            "total_all": total_items,  # 实际总数
            "truncated": truncated,  # 是否被截断
            "output": '\n'.join(output_lines)
        }
        
        if pattern:
            result["pattern"] = pattern
        
        return json.dumps(result, ensure_ascii=False)
        
    except PermissionError as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        }, ensure_ascii=False)
    
    except Exception as e:
        logger.error(f"[ls] 错误: {e}", exc_info=True)
        return json.dumps({
            "status": "error",
            "error": f"列出目录失败: {e}"
        }, ensure_ascii=False)

