---
name: Bing搜索
description: 使用必应中文搜索引擎搜索信息，并可抓取网页详细内容
category: search
---

# Bing搜索 Skill

当用户需要搜索互联网信息、查找最新资讯时，使用 Bing 搜索工具。

> ⚠️ **重要提醒**: `call_tool()` 函数已经预注入到 Python 执行环境中，**直接调用即可**。
> **绝对不要**自己定义 `call_tool` 函数、mock 函数或用 subprocess/HTTP 模拟调用！

## 工具列表

### bing_search - 必应搜索
使用必应中文搜索引擎搜索信息。返回搜索结果包括标题、链接和摘要。

```python
# 基本搜索
result = call_tool('bing_search', {
    'query': '搜索关键词或查询语句',  # required: 搜索关键词
    'count': 10,                      # optional: 返回结果数量，默认10条，最多50条
    'offset': 0                       # optional: 结果偏移量，用于分页，默认0
})
```

### crawl_webpage - 抓取网页内容
根据搜索结果的UUID抓取网页内容。支持批量抓取多个网页。会自动过滤黑名单中的网站。

> 注意：需要先使用 bing_search 获取搜索结果，然后通过结果中的 UUID 和 URL 调用此工具。

```python
# 抓取网页内容
result = call_tool('crawl_webpage', {
    'uuids': ['uuid1', 'uuid2'],  # required: 搜索结果的UUID列表
    'urlMap': {                    # required: UUID到URL的映射
        'uuid1': 'https://example.com/page1',
        'uuid2': 'https://example.com/page2'
    }
})
```

## 使用示例

### 基本搜索流程
```python
# 1. 搜索
results = call_tool('bing_search', {'query': '2026年杭州美食推荐', 'count': 5})

# 2. 从搜索结果中提取UUID和URL
uuids = []
url_map = {}
for item in results.get('results', []):
    uid = item.get('uuid')
    url = item.get('url')
    if uid and url:
        uuids.append(uid)
        url_map[uid] = url

# 3. 抓取详细内容
if uuids:
    content = call_tool('crawl_webpage', {
        'uuids': uuids[:3],  # 取前3个结果
        'urlMap': {k: url_map[k] for k in uuids[:3]}
    })
```

### 分页搜索
```python
# 第一页
page1 = call_tool('bing_search', {'query': 'Python教程', 'count': 10, 'offset': 0})

# 第二页
page2 = call_tool('bing_search', {'query': 'Python教程', 'count': 10, 'offset': 10})
```

## ⚠️ 重要：错误处理与调用频率

### 必须检查返回值
`call_tool()` 在网络异常时会返回 `{"error": "..."}` 而不是抛出异常。**必须检查返回值**：

```python
import time

result = call_tool('bing_search', {'query': '搜索词', 'count': 10})

# ✅ 正确：检查 error
if isinstance(result, dict) and 'error' in result:
    print(f"搜索失败: {result['error']}")
else:
    # 正常处理结果
    for item in result.get('results', []):
        print(item.get('title'))
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
    
    result = call_tool('bing_search', {'query': query, 'count': 10})
    
    if isinstance(result, dict) and 'error' in result:
        print(f"搜索 '{query}' 失败: {result['error']}")
        continue  # 跳过失败的，继续下一个
    
    all_results.extend(result.get('results', []))
```

### 调用频率限制
- **单次执行中不要超过 3 次 bing_search 调用**（通常 1-2 次 + 增大 count 参数即可获取足够结果）
- 优先使用较大的 `count` 参数（如 20-30）减少调用次数，而不是多次小查询
- 多个查询之间至少间隔 2 秒

