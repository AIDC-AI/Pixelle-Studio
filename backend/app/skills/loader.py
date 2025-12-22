"""
Skill Loader - Scans skills directory and extracts metadata from SKILL.md files.

This module provides:
1. Scanning skills directory to find all SKILL.md files
2. Extracting YAML frontmatter metadata from each SKILL.md
3. Building a skills_meta index for injection into LLM system prompt
4. Reading full SKILL.md content on demand
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any

# Try to import yaml, fallback to simple parser if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def parse_simple_yaml(content: str) -> Dict[str, Any]:
    """
    Simple YAML parser for frontmatter - handles basic key: value pairs.
    Falls back when PyYAML is not installed.
    """
    result = {}
    for line in content.strip().split('\n'):
        line = line.strip()
        if ':' in line:
            # Find the first colon
            idx = line.index(':')
            key = line[:idx].strip()
            value = line[idx+1:].strip()
            # Remove surrounding quotes
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            result[key] = value
    return result


@dataclass
class SkillMeta:
    """Metadata extracted from SKILL.md frontmatter."""
    name: str
    description: str
    path: str  # Relative path to SKILL.md
    directory: str  # Skill directory path (for accessing helper scripts)
    license: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SkillLoader:
    """
    Loads and manages skills from the skills directory.
    
    Skills directory structure:
    skills/
    ├── xlsx/
    │   ├── SKILL.md          # Main skill documentation
    │   ├── recalc.py         # Helper script
    │   └── LICENSE.txt       # Optional license
    ├── video/
    │   ├── SKILL.md
    │   └── ...
    """
    
    def __init__(self, skills_dir: Optional[str] = None):
        """
        Initialize the skill loader.
        
        Args:
            skills_dir: Path to skills directory. If None, uses default location.
        """
        if skills_dir is None:
            # Default: backend/skills/
            self.skills_dir = Path(__file__).parent.parent.parent / "skills"
        else:
            self.skills_dir = Path(skills_dir)
        
        self._skills_cache: Dict[str, SkillMeta] = {}
        self._content_cache: Dict[str, str] = {}
    
    def scan_skills(self) -> List[SkillMeta]:
        """
        Scan skills directory and extract metadata from all SKILL.md files.
        
        Returns:
            List of SkillMeta objects
        """
        skills = []
        
        if not self.skills_dir.exists():
            print(f"[SkillLoader] Skills directory not found: {self.skills_dir}")
            return skills
        
        # Iterate through subdirectories
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_md_path = skill_dir / "SKILL.md"
            if not skill_md_path.exists():
                continue
            
            try:
                meta = self._extract_metadata(skill_md_path, skill_dir)
                if meta:
                    skills.append(meta)
                    self._skills_cache[meta.name] = meta
                    print(f"[SkillLoader] Loaded skill: {meta.name}")
            except Exception as e:
                print(f"[SkillLoader] Error loading skill from {skill_dir}: {e}")
        
        print(f"[SkillLoader] Total skills loaded: {len(skills)}")
        return skills
    
    def _extract_metadata(self, skill_md_path: Path, skill_dir: Path) -> Optional[SkillMeta]:
        """
        Extract YAML frontmatter metadata from SKILL.md file.
        
        Args:
            skill_md_path: Path to SKILL.md file
            skill_dir: Path to skill directory
            
        Returns:
            SkillMeta if successful, None otherwise
        """
        content = skill_md_path.read_text(encoding='utf-8')
        
        # Extract YAML frontmatter (between --- markers)
        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(frontmatter_pattern, content, re.DOTALL)
        
        if not match:
            print(f"[SkillLoader] No frontmatter found in {skill_md_path}")
            return None
        
        try:
            if HAS_YAML:
                frontmatter = yaml.safe_load(match.group(1))
            else:
                frontmatter = parse_simple_yaml(match.group(1))
        except Exception as e:
            print(f"[SkillLoader] Invalid YAML in {skill_md_path}: {e}")
            return None
        
        # Required fields
        name = frontmatter.get('name')
        description = frontmatter.get('description')
        
        if not name or not description:
            print(f"[SkillLoader] Missing required fields in {skill_md_path}")
            return None
        
        return SkillMeta(
            name=name,
            description=description,
            path=str(skill_md_path.relative_to(self.skills_dir.parent)),
            directory=str(skill_dir.relative_to(self.skills_dir.parent)),
            license=frontmatter.get('license')
        )
    
    def get_skill_meta(self, skill_name: str) -> Optional[SkillMeta]:
        """
        Get metadata for a specific skill.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            SkillMeta if found, None otherwise
        """
        # Ensure skills are loaded
        if not self._skills_cache:
            self.scan_skills()
        
        return self._skills_cache.get(skill_name)
    
    def read_skill(self, skill_name: str) -> Optional[str]:
        """
        Read full content of a skill's SKILL.md file.
        
        This is the method LLM calls to get detailed skill documentation.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Full SKILL.md content if found, None otherwise
        """
        # Check content cache first
        if skill_name in self._content_cache:
            return self._content_cache[skill_name]
        
        # Get meta to find path
        meta = self.get_skill_meta(skill_name)
        if not meta:
            print(f"[SkillLoader] Skill not found: {skill_name}")
            return None
        
        # Read full content
        skill_md_path = self.skills_dir.parent / meta.path
        if not skill_md_path.exists():
            print(f"[SkillLoader] SKILL.md not found: {skill_md_path}")
            return None
        
        content = skill_md_path.read_text(encoding='utf-8')
        self._content_cache[skill_name] = content
        
        return content
    
    def get_skill_directory(self, skill_name: str) -> Optional[str]:
        """
        Get the absolute path to a skill's directory.
        
        Useful for accessing helper scripts in the skill directory.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Absolute path to skill directory if found, None otherwise
        """
        meta = self.get_skill_meta(skill_name)
        if not meta:
            return None
        
        skill_dir = self.skills_dir.parent / meta.directory
        return str(skill_dir.absolute())
    
    def list_skill_files(self, skill_name: str) -> List[str]:
        """
        List all files in a skill's directory.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            List of filenames in the skill directory
        """
        skill_dir = self.get_skill_directory(skill_name)
        if not skill_dir:
            return []
        
        skill_path = Path(skill_dir)
        if not skill_path.exists():
            return []
        
        return [f.name for f in skill_path.iterdir() if f.is_file()]
    
    def build_skills_meta_prompt(self) -> str:
        """
        Build skills metadata section for system prompt.
        
        Returns:
            Formatted string containing all skills' metadata
        """
        skills = self.scan_skills()
        
        if not skills:
            return "No skills available."
        
        lines = ["## Available Skills\n"]
        
        for skill in skills:
            lines.append(f"### {skill.name}")
            lines.append(f"**Description**: {skill.description}")
            lines.append(f"**Path**: {skill.path}")
            
            # List helper scripts
            files = self.list_skill_files(skill.name)
            helper_scripts = [f for f in files if f.endswith('.py') and f != '__init__.py']
            if helper_scripts:
                lines.append(f"**Helper Scripts**: {', '.join(helper_scripts)}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def clear_cache(self):
        """Clear all caches."""
        self._skills_cache.clear()
        self._content_cache.clear()


# Singleton instance for global access
_skill_loader: Optional[SkillLoader] = None


def get_skill_loader() -> SkillLoader:
    """Get or create the global SkillLoader instance."""
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = SkillLoader()
    return _skill_loader

