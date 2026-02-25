---
name: 网页抓取
description: 从互联网抓取URL内容并提取为Markdown格式，支持获取任意网页的最新信息
category: search
---

# 网页抓取 Skill

当用户需要获取某个网页的内容时，使用 fetch 工具。此工具可以从互联网抓取URL并将内容提取为Markdown格式。

> ⚠️ **重要提醒**: `call_tool()` 函数已经预注入到 Python 执行环境中，**直接调用即可**。
> **绝对不要**自己定义 `call_tool` 函数、mock 函数或用 subprocess/HTTP 模拟调用！

## 工具

### fetch - 抓取网页内容
从互联网获取URL内容，可选择提取为Markdown格式。

```python
# 基本用法 - 抓取并提取为Markdown
result = call_tool('fetch', {
    'url': 'https://example.com',   # required: 要抓取的URL
    'max_length': 5000,             # optional: 返回的最大字符数
    'start_index': 0,               # optional: 从第几个字符开始返回（用于分段获取大页面）
    'raw': False                    # optional: 是否获取原始HTML内容（默认False，提取Markdown）
})
```

## 使用示例

### 获取网页内容
```python
# 抓取网页并提取为Markdown
content = call_tool('fetch', {
    'url': 'https://docs.python.org/3/tutorial/index.html',
    'max_length': 10000
})
print(content)
```

### 分段获取大页面
```python
# 第一段
part1 = call_tool('fetch', {
    'url': 'https://example.com/long-article',
    'max_length': 5000,
    'start_index': 0
})

# 第二段
part2 = call_tool('fetch', {
    'url': 'https://example.com/long-article',
    'max_length': 5000,
    'start_index': 5000
})
```

### 获取原始HTML
```python
# 获取原始HTML（用于需要解析DOM的场景）
html = call_tool('fetch', {
    'url': 'https://example.com',
    'raw': True,
    'max_length': 20000
})
```

### 结合搜索使用
```python
# 1. 先用Exa搜索找到相关信息
results = call_tool('web_search_exa', {'query': 'Python asyncio教程', 'numResults': 5})

# 2. 如果需要更详细的页面内容，用fetch抓取特定URL
content = call_tool('fetch', {'url': 'https://docs.python.org/3/library/asyncio.html', 'max_length': 8000})
print(content)
```

