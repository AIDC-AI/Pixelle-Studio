---
name: 互联网搜索
description: 通过关键词在互联网上搜索相关信息
---

使用必应中文搜索引擎搜索信息。返回搜索结果包括标题、链接和摘要，返回top count的结果：

# bing_search/bing_search-start #
call_tool('bing_search', {query:This Is A String,count:This Is A Number,offset:This Is A Number})
# bing_search/bing_search-end #