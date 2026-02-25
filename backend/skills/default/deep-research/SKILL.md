---
name: 深度研究
description: 综合使用搜索引擎和网页抓取工具进行深度调研，生成结构化研究报告
category: research
---

# 深度研究 Skill

当用户需要对某个主题进行深度调研时，综合使用搜索和网页抓取工具，多轮搜索和抓取，最终生成结构化研究报告。

> ⚠️ **重要提醒**: `call_tool()` 函数已经预注入到 Python 执行环境中，**直接调用即可**。
> **绝对不要**自己定义 `call_tool` 函数、mock 函数或用 subprocess/HTTP 模拟调用！

## 可用工具

### 搜索工具
```python
# Exa网页搜索 - 获取搜索结果（返回干净可用的内容）
result = call_tool('web_search_exa', {
    'query': '搜索关键词',              # required
    'numResults': 10,                   # optional: 结果数量，默认8
    'livecrawl': 'fallback',            # optional: 'fallback'(默认) 或 'preferred'(优先实时爬取)
    'contextMaxCharacters': 10000       # optional: 上下文最大字符数，默认10000
})

# Exa公司研究 - 研究特定公司
result = call_tool('company_research_exa', {
    'companyName': '公司名称',  # required
    'numResults': 3             # optional: 默认3
})

# Exa代码/文档搜索 - 查找代码示例和文档
result = call_tool('get_code_context_exa', {
    'query': '搜索查询',   # required
    'tokensNum': 5000       # optional: 1000-50000，默认5000
})
```

### 网页抓取工具
```python

# 直接URL抓取（适用于已知URL）
result = call_tool('fetch', {
    'url': 'https://example.com',  # required
    'max_length': 10000            # optional: 最大字符数
})
```

## 深度研究流程

### 标准流程
```python
# ⚠️ call_tool() 已预注入，直接使用，不要 import 或自定义！
import json

# ========== 第一阶段：初步搜索 ==========
topic = "用户的研究主题"
results = call_tool('web_search_exa', {
    'query': topic,
    'numResults': 15,
    'livecrawl': 'preferred',        # 优先实时爬取获取最新内容
    'contextMaxCharacters': 15000
})

# 提取和分析搜索结果内容
# Exa搜索直接返回干净的网页内容，可以直接使用
print(results)

# ========== 第二阶段：深度抓取 ==========
# 对于需要更多详情的URL，使用fetch工具
# 注意：zhihu等网站可能会被block，无法fetch，请绕过可能被block的网站
detailed = []
for url_item in important_urls:
    result = call_tool('fetch', {
        'url': url_item,  # required
        'max_length': 10000            # optional: 最大字符数
    })
    detailed.append(result)

# ========== 第三阶段：补充搜索 ==========
# 基于初步结果，进行更有针对性的搜索
sub_results = call_tool('web_search_exa', {
    'query': f'{topic} 最新进展 2026',
    'numResults': 8
})

# 如果涉及特定公司，可以用公司研究工具
company_info = call_tool('company_research_exa', {
    'companyName': '相关公司名',
    'numResults': 5
})

# ========== 第四阶段：整理报告 ==========
# 将所有收集的信息整理为结构化报告
# ⚠️ 重要：报告中的每个关键结论/事实都必须附带引用来源URL（Markdown超链接格式）
report = f"""
# {topic} 深度研究报告

## 研究概述
...根据搜索和抓取的内容整理...

## 主要发现
- 发现1：某某产品推出了新功能 [来源](https://example.com/article1)
- 发现2：某某技术取得突破 [来源](https://example.com/article2)

## 详细分析
### 方向一
具体分析内容...根据[某报告](https://example.com/report)显示...

### 方向二
更多分析...据[媒体报道](https://example.com/news)...

## 结论与建议
1. 结论一... [来源](https://example.com/source1)
2. 结论二... [来源](https://example.com/source2)

## 参考来源
- [来源标题1](https://example.com/article1)
- [来源标题2](https://example.com/article2)
- [来源标题3](https://example.com/article3)
"""
```

### 关键原则
1. **多轮搜索**: 不要只搜索一次，根据初步结果进行补充搜索（但**总计不超过3次搜索调用**）
2. **交叉验证**: 从多个来源获取信息，交叉验证关键事实
3. **深度抓取**: 对重要页面使用 fetch 获取详细内容
4. **结构化输出**: 最终生成清晰的结构化报告，包含来源引用
5. **迭代深入**: 从宏观到微观，逐步深入研究主题的各个方面
6. **善用多种工具**: 综合使用 web_search_exa、company_research_exa 和 fetch 工具获取全面信息
7. **引用来源（必须）**: 报告中的每个关键结论、事实、数据点都**必须**附带引用来源URL。使用 Markdown 超链接格式 `[来源标题](URL)` 嵌入到相关文本旁边。最终报告末尾也要有完整的"参考来源"列表

### ⚠️ 调用频率与错误处理（必须遵守）

1. **每次 call_tool 之间必须加 `time.sleep(2)` 间隔**，避免连续快速调用导致远程服务连接断开
2. **必须检查返回值中的 error 字段**：`call_tool()` 在网络失败时返回 `{"error": "..."}` 而非抛出异常
3. **单次执行中 web_search_exa 调用不超过 3 次**，优先用较大的 `numResults`（如 15-20）减少调用次数
4. **用 try-except 包裹关键逻辑**，确保部分失败不影响整体输出

```python
import time

# ✅ 正确：带间隔和错误检查的多次搜索
def safe_search(query, num_results=15):
    """安全的搜索封装，自动检查错误"""
    result = call_tool('web_search_exa', {'query': query, 'numResults': num_results})
    if isinstance(result, dict) and 'error' in result:
        print(f"⚠️ 搜索失败: {result['error']}")
        return None
    return result

# 第一阶段搜索
results1 = safe_search(f'{topic}', num_results=15)

time.sleep(2)  # ⚠️ 间隔必须

# 第二阶段补充搜索
results2 = safe_search(f'{topic} 最新进展 2026', num_results=10)
```
