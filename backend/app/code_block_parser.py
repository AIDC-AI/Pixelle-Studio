"""
Code block parser - write_file fallback mechanism

When the LLM cannot use write_file (parameter too long), it can output specially formatted code blocks:

```language:filename
code content here
```

The Agent will automatically detect and create files.
"""
import re
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_code_blocks(message: str) -> List[Dict[str, str]]:
    """
    Extract code blocks from a message.
    
    Supported formats:
    ```python:script.py
    code here
    ```
    
    or
    
    ```bash:install.sh
    #!/bin/bash
    code here
    ```
    
    Returns:
        [{"language": "python", "filename": "script.py", "content": "code here"}, ...]
    """
    # Match pattern: ```language:filename\ncontent\n```
    pattern = r'```(\w+):([^\n]+)\n(.*?)```'
    
    matches = re.findall(pattern, message, re.DOTALL)
    
    code_blocks = []
    for language, filename, content in matches:
        code_blocks.append({
            "language": language.strip(),
            "filename": filename.strip(),
            "content": content.strip()
        })
    
    if code_blocks:
        logger.info(f"[code_block_parser] Extracted {len(code_blocks)} code blocks")
        for block in code_blocks:
            logger.info(f"  - {block['filename']} ({block['language']}, {len(block['content'])} chars)")
    
    return code_blocks


def has_code_blocks(message: str) -> bool:
    """Check if message contains code blocks"""
    pattern = r'```\w+:[^\n]+\n.*?```'
    return bool(re.search(pattern, message, re.DOTALL))


async def process_code_blocks(
    message: str,
    context,  # AgentContext
    write_file_handler
) -> Optional[str]:
    """
    Process code blocks in a message, automatically creating files.
    
    Args:
        message: LLM output message
        context: AgentContext
        write_file_handler: write_file tool handler function
    
    Returns:
        Processing result message (if code blocks found), otherwise None
    """
    code_blocks = extract_code_blocks(message)
    
    if not code_blocks:
        return None
    
    # Process each code block
    results = []
    for block in code_blocks:
        filename = block['filename']
        content = block['content']
        language = block['language']
        
        # Call write_file
        result = await write_file_handler(
            context,
            path=filename,
            content=content
        )
        
        results.append({
            "filename": filename,
            "language": language,
            "result": result,
            "size": len(content)
        })
    
    # Generate summary message
    summary_lines = [
        f"\n📝 Automatically created {len(results)} files (from code blocks):\n"
    ]
    
    for r in results:
        import json
        try:
            result_data = json.loads(r['result'])
            if result_data.get('status') == 'success':
                summary_lines.append(f"  ✅ {r['filename']} ({r['size']} chars)")
            else:
                summary_lines.append(f"  ❌ {r['filename']}: {result_data.get('error', 'unknown error')}")
        except:
            summary_lines.append(f"  ⚠️ {r['filename']}: parse error")
    
    summary = '\n'.join(summary_lines)
    logger.info(f"[code_block_parser] {summary}")
    
    return summary


def build_code_block_guide() -> str:
    """
    Generate code block format guide (for System Prompt).
    """
    return """
## Code Block Format (write_file fallback)

If the write_file tool's content parameter is too long and causes errors, use the following format:

```python:filename.py
# Your Python code
def main():
    pass
```

```bash:script.sh
#!/bin/bash
# Your Bash script
echo "hello"
```

The system will automatically detect and create these files.

**Format requirements**:
- First line: ```language:filename
- Middle: code content
- Last line: ```

**Supported languages**: python, bash, javascript, typescript, java, etc.
"""

