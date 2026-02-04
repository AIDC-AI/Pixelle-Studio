"""
Skills 管理器 - 生成 Skill 摘要

用于在 System Prompt 中展示可用的 Skills
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def get_skills_summary(user_id: Optional[str] = None) -> str:
    """
    生成 Skills 摘要（用于 System Prompt）
    
    Args:
        user_id: 用户ID（可选，用于用户自定义 skills）
    
    Returns:
        Skills 摘要文本
    """
    backend_root = Path(__file__).parent.parent
    
    # 默认 skills 目录
    default_skills_dir = backend_root / "skills" / "default"
    
    # 用户 skills 目录（如果有）
    user_skills_dir = backend_root / "skills" / user_id if user_id else None
    
    skills = []
    
    # 扫描默认 skills
    if default_skills_dir.exists():
        skills.extend(_scan_skills_directory(default_skills_dir, "default"))
    
    # 扫描用户 skills
    if user_skills_dir and user_skills_dir.exists():
        skills.extend(_scan_skills_directory(user_skills_dir, user_id))
    
    if not skills:
        return "暂无可用的 Skills。"
    
    # 生成摘要
    lines = [
        "## 可用的 Skills\n",
        f"共 {len(skills)} 个 Skills，使用 read_file 工具加载详细文档。\n"
    ]
    
    # 按类别分组
    by_category = {}
    for skill in skills:
        category = skill.get('category', 'other')
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(skill)
    
    # 输出
    for category, items in sorted(by_category.items()):
        lines.append(f"\n### {category.title()}")
        for skill in items:
            lines.append(f"- **{skill['name']}**: {skill['description']}")
            lines.append(f"  路径: `{skill['path']}`")
    
    lines.append("\n**使用方法**: 使用 `read_file('{skill_path}')` 加载 Skill 详细文档。\n")
    
    return '\n'.join(lines)


def _scan_skills_directory(directory: Path, source: str) -> List[Dict[str, str]]:
    """扫描 skills 目录"""
    skills = []
    
    # 查找所有 SKILL.md 或 skill.md 文件
    for skill_file in directory.rglob("*[Ss][Kk][Ii][Ll][Ll].md"):
        skill_info = _parse_skill_file(skill_file, source)
        if skill_info:
            skills.append(skill_info)
    
    return skills


def _parse_skill_file(skill_file: Path, source: str) -> Optional[Dict[str, str]]:
    """解析 Skill 文件，提取元信息"""
    try:
        content = skill_file.read_text(encoding='utf-8')
        
        # 提取标题（第一个 # 开头的行）
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else skill_file.parent.name
        
        # 提取描述（标题后的第一段）
        lines = content.split('\n')
        description = ""
        in_description = False
        for line in lines:
            if line.startswith('# '):
                in_description = True
                continue
            if in_description and line.strip():
                description = line.strip()
                break
        
        # 提取类别（从路径）
        # 例如：skills/default/data/xlsx/SKILL.md → category: data
        parts = skill_file.parts
        skills_index = next((i for i, p in enumerate(parts) if p == 'skills'), None)
        if skills_index and len(parts) > skills_index + 3:
            category = parts[skills_index + 2]  # default/data/...
        else:
            category = 'other'
        
        return {
            "name": title,
            "description": description or "无描述",
            "path": str(skill_file),
            "category": category,
            "source": source
        }
        
    except Exception as e:
        logger.error(f"[skills_manager] 解析 Skill 失败 {skill_file}: {e}")
        return None


import re

