---
name: Exa搜索
description: 使用Exa AI搜索引擎搜索网页信息、研究公司、查找代码文档，获取干净可用的内容
category: search
---

# Exa搜索 Skill

当用户需要搜索互联网信息、查找最新资讯、研究公司或查找代码文档时，使用 Exa 搜索工具。

> ⚠️ **重要提醒**: `call_tool()` 函数已经预注入到 Python 执行环境中，**直接调用即可**。
> **绝对不要**自己定义 `call_tool` 函数、mock 函数或用 subprocess/HTTP 模拟调用！

## 工具列表

### web_search_exa - 网页搜索
搜索任意主题，获取干净、可直接使用的网页内容。适合查找当前信息、新闻、事实或回答任何问题。

```python
# 基本搜索
result = call_tool('web_search_exa', {
    'query': '搜索关键词或查询语句',         # required: 搜索关键词
    'numResults': 8,                        # optional: 返回结果数量，默认8
    'livecrawl': 'fallback',                # optional: 'fallback'(默认，缓存无内容时实时爬取) 或 'preferred'(优先实时爬取)
    'type': 'auto',                         # optional: 'auto'(默认，平衡搜索) 或 'fast'(快速搜索)
    'contextMaxCharacters': 10000           # optional: 上下文最大字符数，默认10000
})
```

### company_research_exa - 公司研究
研究任何公司，获取商业信息、新闻和洞察。适合了解公司产品、服务、最新动态或行业地位。

```python
# 公司研究
result = call_tool('company_research_exa', {
    'companyName': '公司名称',  # required: 要研究的公司名称
    'numResults': 3             # optional: 返回结果数量，默认3
})
```

### get_code_context_exa - 代码/文档搜索
查找代码示例、文档和编程解决方案。搜索 GitHub、Stack Overflow 和官方文档。

```python
# 代码文档搜索
result = call_tool('get_code_context_exa', {
    'query': '搜索查询，如 React useState hook examples',  # required: 搜索查询
    'tokensNum': 5000                                       # optional: 返回的token数(1000-50000)，默认5000
})
```

## 使用示例

### 基本搜索流程
```python
# 1. 搜索
results = call_tool('web_search_exa', {'query': '2026年杭州美食推荐', 'numResults': 10})

# 2. 处理搜索结果
# Exa搜索直接返回清洁的网页内容，可以直接使用
print(results)
```

### 公司调研
```python
# 研究某公司
info = call_tool('company_research_exa', {
    'companyName': 'OpenAI',
    'numResults': 5
})
print(info)
```

### 查找代码文档
```python
# 查找Python asyncio相关代码
code_info = call_tool('get_code_context_exa', {
    'query': 'Python asyncio tutorial examples',
    'tokensNum': 8000
})
print(code_info)
```

### 获取最新资讯
```python
# 使用实时爬取模式获取最新信息
results = call_tool('web_search_exa', {
    'query': '最新AI技术进展 2026',
    'numResults': 10,
    'livecrawl': 'preferred',  # 优先实时爬取，获取最新内容
    'contextMaxCharacters': 15000
})
```

## ⚠️ 重要：错误处理与调用频率

### 必须检查返回值
`call_tool()` 在网络异常时会返回 `{"error": "..."}` 而不是抛出异常。**必须检查返回值**：

```python
import time

result = call_tool('web_search_exa', {'query': '搜索词', 'numResults': 10})

# ✅ 正确：检查 error
if isinstance(result, dict) and 'error' in result:
    print(f"搜索失败: {result['error']}")
else:
    # 正常处理结果
    print(result)
```

### 多次调用必须加间隔
连续快速调用会导致远程服务连接不稳定。**多次调用之间必须加 `time.sleep()` 间隔**：

```python
import time

queries = ["查询1", "查询2", "查询3"]
all_results = []

for i, query in enumerate(queries):
    if i > 0:
        time.sleep(2)  # ⚠️ 每次调用间隔至少2秒
    
    result = call_tool('web_search_exa', {'query': query, 'numResults': 10})
    
    if isinstance(result, dict) and 'error' in result:
        print(f"搜索 '{query}' 失败: {result['error']}")
        continue  # 跳过失败的，继续下一个
    
    all_results.append(result)
```

### 调用频率限制
- **单次执行中不要超过 3 次 web_search_exa 调用**（通常 1-2 次 + 增大 numResults 参数即可获取足够结果）
- 优先使用较大的 `numResults` 参数（如 15-20）减少调用次数，而不是多次小查询
- 多个查询之间至少间隔 2 秒


