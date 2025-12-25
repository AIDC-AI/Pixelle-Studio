"""
Skill Loader - Scans skills directory and extracts metadata from SKILL.md files.

This module provides:
1. Scanning skills directory to find all SKILL.md files
2. Extracting YAML frontmatter metadata from each SKILL.md
3. Building a skills_meta index for injection into LLM system prompt
4. Reading full SKILL.md content on demand
5. Reading any file within a skill directory (Progressive Disclosure Level 3)
6. Listing skill directory structure recursively
7. Parsing markdown links in SKILL.md to discover related resources
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Any, Set


# ============================================================================
# Configuration
# ============================================================================

class SkillLoaderConfig:
    """Configuration for SkillLoader."""
    
    # File extensions that can be read as text
    READABLE_EXTENSIONS: Set[str] = {
        # Documentation
        '.md', '.txt', '.rst',
        # Code
        '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml',
        # Config/Data
        '.xml', '.xsd', '.html', '.css', '.csv', '.toml', '.ini',
        # Scripts
        '.sh', '.bat', '.sql',
    }
    
    # Directories to exclude when listing skill tree
    EXCLUDED_DIRS: Set[str] = {
        '__pycache__', '.git', '.svn', 'node_modules',
        '.venv', 'venv', '__MACOSX', '.DS_Store',
    }
    
    # Maximum file size to read (1MB)
    MAX_FILE_SIZE: int = 1024 * 1024
    
    # Maximum directory depth for tree listing
    MAX_TREE_DEPTH: int = 5

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
class LinkInfo:
    """Information about a markdown link found in SKILL.md."""
    text: str           # Link text, e.g., "html2pptx.md"
    path: str           # Link path, e.g., "html2pptx.md" or "scripts/html2pptx.js"
    exists: bool        # Whether the linked file exists
    line_number: int    # Line number in SKILL.md
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileNode:
    """A node in the skill directory tree."""
    name: str
    path: str           # Relative path from skill directory
    type: str           # "file" or "directory"
    size: Optional[int] = None          # File size in bytes (files only)
    extension: Optional[str] = None     # File extension (files only)
    children: Optional[List['FileNode']] = None  # Children (directories only)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "path": self.path,
            "type": self.type,
        }
        if self.type == "file":
            result["size"] = self.size
            result["extension"] = self.extension
        elif self.children is not None:
            result["children"] = [child.to_dict() for child in self.children]
        return result


@dataclass
class SkillMeta:
    """Metadata extracted from SKILL.md frontmatter."""
    name: str
    description: str
    path: str  # Relative path to SKILL.md
    directory: str  # Skill directory path (for accessing helper scripts)
    license: Optional[str] = None
    # Extended fields
    linked_files: Optional[List[str]] = None  # Files linked in SKILL.md
    has_scripts: bool = False  # Has scripts/ directory
    has_resources: bool = False  # Has resources/ directory
    
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
    
    # =========================================================================
    # New Methods for Progressive Disclosure Level 3
    # =========================================================================
    
    def list_skill_tree(self, skill_name: str, max_depth: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Recursively list all files and directories in a skill folder.
        
        Args:
            skill_name: Name of the skill
            max_depth: Maximum recursion depth (default: SkillLoaderConfig.MAX_TREE_DEPTH)
            
        Returns:
            Dictionary representing the directory tree, or None if skill not found
        """
        skill_dir = self.get_skill_directory(skill_name)
        if not skill_dir:
            print(f"[SkillLoader] Skill not found: {skill_name}")
            return None
        
        skill_path = Path(skill_dir)
        if not skill_path.exists():
            return None
        
        max_depth = max_depth or SkillLoaderConfig.MAX_TREE_DEPTH
        
        def build_tree(path: Path, current_depth: int = 0, rel_prefix: str = "") -> FileNode:
            """Recursively build directory tree."""
            name = path.name
            rel_path = f"{rel_prefix}/{name}" if rel_prefix else name
            
            if path.is_file():
                return FileNode(
                    name=name,
                    path=rel_path,
                    type="file",
                    size=path.stat().st_size,
                    extension=path.suffix.lower() if path.suffix else None,
                )
            
            # Directory
            children = []
            if current_depth < max_depth:
                try:
                    for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                        # Skip excluded directories
                        if child.is_dir() and child.name in SkillLoaderConfig.EXCLUDED_DIRS:
                            continue
                        # Skip hidden files/directories
                        if child.name.startswith('.'):
                            continue
                        children.append(build_tree(child, current_depth + 1, rel_path))
                except PermissionError:
                    pass
            
            return FileNode(
                name=name,
                path=rel_path,
                type="directory",
                children=children,
            )
        
        root = build_tree(skill_path)
        return root.to_dict()
    
    def _validate_skill_path(self, skill_name: str, relative_path: str) -> Optional[Path]:
        """
        Validate that a relative path is safe and within the skill directory.
        
        Args:
            skill_name: Name of the skill
            relative_path: Relative path within the skill directory
            
        Returns:
            Absolute Path if valid, None otherwise
        """
        skill_dir = self.get_skill_directory(skill_name)
        if not skill_dir:
            return None
        
        skill_path = Path(skill_dir).resolve()
        
        # Normalize and resolve the target path
        # Remove leading slashes to treat as relative
        clean_path = relative_path.lstrip('/')
        target = (skill_path / clean_path).resolve()
        
        # Security check: ensure target is within skill directory
        try:
            target.relative_to(skill_path)
        except ValueError:
            print(f"[SkillLoader] Path traversal attempt blocked: {relative_path}")
            return None
        
        return target
    
    def read_skill_file(self, skill_name: str, relative_path: str) -> Optional[str]:
        """
        Read a specific file from the skill directory.
        
        This is used to read detailed documentation, scripts, or templates.
        Only text files with allowed extensions can be read.
        
        Args:
            skill_name: Name of the skill
            relative_path: Path relative to skill directory (e.g., "html2pptx.md" or "scripts/html2pptx.js")
            
        Returns:
            File content as string, or None if not found/not readable
        """
        target = self._validate_skill_path(skill_name, relative_path)
        if not target:
            return None
        
        if not target.exists():
            print(f"[SkillLoader] File not found: {skill_name}/{relative_path}")
            return None
        
        if not target.is_file():
            print(f"[SkillLoader] Not a file: {skill_name}/{relative_path}")
            return None
        
        # Check extension
        ext = target.suffix.lower()
        if ext not in SkillLoaderConfig.READABLE_EXTENSIONS:
            print(f"[SkillLoader] File type not readable: {ext}")
            return None
        
        # Check file size
        file_size = target.stat().st_size
        if file_size > SkillLoaderConfig.MAX_FILE_SIZE:
            print(f"[SkillLoader] File too large: {file_size} bytes (max: {SkillLoaderConfig.MAX_FILE_SIZE})")
            return None
        
        try:
            return target.read_text(encoding='utf-8')
        except Exception as e:
            print(f"[SkillLoader] Error reading file: {e}")
            return None
    
    def get_skill_file_path(self, skill_name: str, relative_path: str) -> Optional[str]:
        """
        Get the absolute path to a file in the skill directory.
        
        Use this when you need to execute or reference a script.
        
        Args:
            skill_name: Name of the skill
            relative_path: Path relative to skill directory (e.g., "scripts/html2pptx.js")
            
        Returns:
            Absolute path as string if file exists, None otherwise
        """
        target = self._validate_skill_path(skill_name, relative_path)
        if not target:
            return None
        
        if not target.exists():
            print(f"[SkillLoader] File not found: {skill_name}/{relative_path}")
            return None
        
        return str(target)
    
    def parse_skill_links(self, skill_name: str) -> List[LinkInfo]:
        """
        Parse markdown links in SKILL.md to discover related resources.
        
        Extracts [text](path) style links and checks if targets exist.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            List of LinkInfo objects for all relative links found
        """
        skill_content = self.read_skill(skill_name)
        if not skill_content:
            return []
        
        skill_dir = self.get_skill_directory(skill_name)
        if not skill_dir:
            return []
        
        skill_path = Path(skill_dir)
        links = []
        
        # Pattern for markdown links: [text](path)
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        
        for line_num, line in enumerate(skill_content.split('\n'), start=1):
            for match in link_pattern.finditer(line):
                text = match.group(1)
                path = match.group(2)
                
                # Skip external links (http, https, mailto, etc.)
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', path):
                    continue
                
                # Skip anchor-only links
                if path.startswith('#'):
                    continue
                
                # Remove anchor from path if present
                clean_path = path.split('#')[0]
                if not clean_path:
                    continue
                
                # Check if file exists
                target = (skill_path / clean_path).resolve()
                exists = target.exists()
                
                links.append(LinkInfo(
                    text=text,
                    path=clean_path,
                    exists=exists,
                    line_number=line_num,
                ))
        
        return links
    
    def build_skills_meta_prompt_enhanced(self) -> str:
        """
        Build enhanced skills metadata section for system prompt.
        
        Includes related documents discovered from SKILL.md links.
        
        Returns:
            Formatted string containing all skills' metadata with related docs
        """
        skills = self.scan_skills()
        
        if not skills:
            return "No skills available."
        
        lines = [
            "## Available Skills\n",
            "Use `[LOAD_SKILL: name]` to load a skill's main documentation.",
            "Use `[LIST_SKILL_TREE: name]` to see all files in a skill directory.",
            "Use `[READ_SKILL_FILE: name, path]` to read specific files.\n",
        ]
        
        for skill in skills:
            lines.append(f"### {skill.name}")
            lines.append(f"**Description**: {skill.description}")
            
            # Find related docs
            links = self.parse_skill_links(skill.name)
            existing_docs = [link.path for link in links if link.exists and link.path.endswith('.md')]
            if existing_docs:
                lines.append(f"**Related Docs**: {', '.join(existing_docs[:5])}")
            
            # Check for scripts/resources directories
            skill_dir = Path(self.get_skill_directory(skill.name))
            if (skill_dir / "scripts").exists():
                lines.append("**Has Scripts**: Yes")
            if (skill_dir / "resources").exists():
                lines.append("**Has Resources**: Yes")
            
            lines.append("")
        
        return "\n".join(lines)


# Singleton instance for global access
_skill_loader: Optional[SkillLoader] = None


def get_skill_loader() -> SkillLoader:
    """Get or create the global SkillLoader instance."""
    global _skill_loader
    if _skill_loader is None:
        _skill_loader = SkillLoader()
    return _skill_loader

