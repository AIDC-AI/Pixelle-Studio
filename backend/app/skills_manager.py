"""
Skills Manager - Generate Skill summaries

Used to display available Skills in the System Prompt.
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def get_skills_summary(user_id: Optional[str] = None) -> str:
    """
    Generate Skills summary (for System Prompt).
    
    Args:
        user_id: User ID (optional, for user-customized skills)
    
    Returns:
        Skills summary text
    """
    backend_root = Path(__file__).parent.parent
    
    # Default skills directory
    default_skills_dir = backend_root / "skills" / "default"
    
    # User skills directory (if any)
    user_skills_dir = backend_root / "skills" / user_id if user_id else None
    
    skills = []
    
    # Scan default skills
    if default_skills_dir.exists():
        skills.extend(_scan_skills_directory(default_skills_dir, "default"))
    
    # Scan user skills
    if user_skills_dir and user_skills_dir.exists():
        skills.extend(_scan_skills_directory(user_skills_dir, user_id))
    
    if not skills:
        return "No Skills available."
    
    # Generate summary
    lines = [
        "## Available Skills\n",
        f"Total {len(skills)}  Skills, use read_file to load detailed documentation.\n"
    ]
    
    # Group by category
    by_category = {}
    for skill in skills:
        category = skill.get('category', 'other')
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(skill)
    
    # Output
    for category, items in sorted(by_category.items()):
        lines.append(f"\n### {category.title()}")
        for skill in items:
            lines.append(f"- **{skill['name']}**: {skill['description']}")
            lines.append(f"  Path: `{skill['path']}`")
    
    lines.append("\n**Usage**: Use `read_file('{skill_path}')` to load Skill detailed documentation.\n")
    
    return '\n'.join(lines)


def _scan_skills_directory(directory: Path, source: str) -> List[Dict[str, str]]:
    """Scan skills directory"""
    skills = []
    
    # Find all SKILL.md or skill.md files
    for skill_file in directory.rglob("*[Ss][Kk][Ii][Ll][Ll].md"):
        skill_info = _parse_skill_file(skill_file, source)
        if skill_info:
            skills.append(skill_info)
    
    return skills


def _parse_skill_file(skill_file: Path, source: str) -> Optional[Dict[str, str]]:
    """Parse Skill file and extract metadata"""
    try:
        content = skill_file.read_text(encoding='utf-8')
        
        # Extract title (first line starting with #)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else skill_file.parent.name
        
        # Extract description (first paragraph after title)
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
        
        # Extract category (from path)
        # e.g.: skills/default/data/xlsx/SKILL.md → category: data
        parts = skill_file.parts
        skills_index = next((i for i, p in enumerate(parts) if p == 'skills'), None)
        if skills_index and len(parts) > skills_index + 3:
            category = parts[skills_index + 2]  # default/data/...
        else:
            category = 'other'
        
        return {
            "name": title,
            "description": description or "No description",
            "path": str(skill_file),
            "category": category,
            "source": source
        }
        
    except Exception as e:
        logger.error(f"[skills_manager] Failed to parse Skill {skill_file}: {e}")
        return None


import re

