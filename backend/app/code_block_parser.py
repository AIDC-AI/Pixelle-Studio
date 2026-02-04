"""
代码块解析器 - write_file 兜底机制

当 LLM 无法使用 write_file（参数过长）时，可以输出特殊格式的代码块：

```language:filename
code content here
```

Agent 会自动检测并创建文件。
"""
import re
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_code_blocks(message: str) -> List[Dict[str, str]]:
    """
    从消息中提取代码块
    
    支持的格式：
    ```python:script.py
    code here
    ```
    
    或
    
    ```bash:install.sh
    #!/bin/bash
    code here
    ```
    
    Returns:
        [{"language": "python", "filename": "script.py", "content": "code here"}, ...]
    """
    # 匹配模式：```language:filename\ncontent\n```
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
        logger.info(f"[code_block_parser] 提取到 {len(code_blocks)} 个代码块")
        for block in code_blocks:
            logger.info(f"  - {block['filename']} ({block['language']}, {len(block['content'])} 字符)")
    
    return code_blocks


def has_code_blocks(message: str) -> bool:
    """检查消息是否包含代码块"""
    pattern = r'```\w+:[^\n]+\n.*?```'
    return bool(re.search(pattern, message, re.DOTALL))


async def process_code_blocks(
    message: str,
    context,  # AgentContext
    write_file_handler
) -> Optional[str]:
    """
    处理消息中的代码块，自动创建文件
    
    Args:
        message: LLM 输出的消息
        context: AgentContext
        write_file_handler: write_file 工具处理函数
    
    Returns:
        处理结果消息（如果有代码块），否则 None
    """
    code_blocks = extract_code_blocks(message)
    
    if not code_blocks:
        return None
    
    # 处理每个代码块
    results = []
    for block in code_blocks:
        filename = block['filename']
        content = block['content']
        language = block['language']
        
        # 调用 write_file
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
    
    # 生成摘要消息
    summary_lines = [
        f"\n📝 自动创建了 {len(results)} 个文件（从代码块）:\n"
    ]
    
    for r in results:
        import json
        try:
            result_data = json.loads(r['result'])
            if result_data.get('status') == 'success':
                summary_lines.append(f"  ✅ {r['filename']} ({r['size']} 字符)")
            else:
                summary_lines.append(f"  ❌ {r['filename']}: {result_data.get('error', 'unknown error')}")
        except:
            summary_lines.append(f"  ⚠️ {r['filename']}: 解析错误")
    
    summary = '\n'.join(summary_lines)
    logger.info(f"[code_block_parser] {summary}")
    
    return summary


def build_code_block_guide() -> str:
    """
    生成代码块格式指南（用于 System Prompt）
    """
    return """
## 代码块格式（write_file 兜底）

如果 write_file 工具的 content 参数过长导致错误，可以使用以下格式：

```python:filename.py
# 你的 Python 代码
def main():
    pass
```

```bash:script.sh
#!/bin/bash
# 你的 Bash 脚本
echo "hello"
```

系统会自动检测并创建这些文件。

**格式要求**:
- 第一行：```language:filename
- 中间：代码内容
- 最后：```

**支持的语言**: python, bash, javascript, typescript, java, etc.
"""

