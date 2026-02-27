# Docker 镜像大小分析报告

> 分析日期: 2026-02-27

## 一、总览

后端镜像是主要的膨胀源头，预估构建后大小约 **1.8 ~ 2.2 GB**。前端镜像使用了多阶段构建，问题不大（约 200-300MB）。

## 二、后端镜像 (backend) — 逐层大小排序

| 排名 | 组件 | 预估大小 | 类别 | 说明 |
|------|------|----------|------|------|
| 🥇 1 | **PyTorch (torch)** | **353 MB** | Python依赖 | 由 `sentence-transformers` 传递引入 |
| 🥈 2 | **fonts-noto-cjk** | **120~180 MB** | 系统包 | CJK 字体，非常庞大 |
| 🥉 3 | **python:3.11-slim 基础镜像** | **~150 MB** | 基础镜像 | - |
| 4 | **Node.js + npm (via apt)** | **~80-100 MB** | 系统包 | Debian 源安装的 Node.js |
| 5 | **onnxruntime** | **111 MB** | Python依赖 | 由 `sentence-transformers` 传递引入 |
| 6 | **react-icons** | **83 MB** | Node依赖 | PPTX skill 用到的图标库 |
| 7 | **scipy** | **70 MB** | Python依赖 | 由 `sentence-transformers` 传递引入 |
| 8 | **transformers (HuggingFace)** | **54 MB** | Python依赖 | 由 `sentence-transformers` 传递引入 |
| 9 | **pandas** | **48 MB** | Python依赖 | 数据处理 |
| 10 | **sklearn (scikit-learn)** | **30 MB** | Python依赖 | 由 `sentence-transformers` 传递引入 |
| 11 | **sympy** | **29 MB** | Python依赖 | 由 torch 传递引入 |
| 12 | **matplotlib** | **25 MB** | Python依赖 | 图表生成 |
| 13 | **numpy** | **23 MB** | Python依赖 | 数据处理 |
| 14 | **cryptography** | **22 MB** | Python依赖 | JWT 认证 |
| 15 | **lxml** | **21 MB** | Python依赖 | XML 处理 |
| 16 | **git** | **~20 MB** | 系统包 | 是否真的需要？ |
| 17 | **@img/sharp** | **15 MB** | Node依赖 | 图片处理 |
| 18 | **fonts-wqy-zenhei** | **~15 MB** | 系统包 | 中文字体 |
| 19 | **sqlalchemy** | **14 MB** | Python依赖 | ORM |
| 20 | **pillow** | **13 MB** | Python依赖 | 图片处理 |
| 21 | **playwright + playwright-core** | **~13 MB** | Node依赖 | HTML→PPTX 渲染 |
| 22 | **fontTools** | **12 MB** | Python依赖 | 字体处理 |
| 23 | **openai** | **11 MB** | Python依赖 | LLM API |

### Python 依赖总计: ~987 MB
### Node 依赖总计: ~131 MB
### 系统包总计: ~240-320 MB
### 基础镜像: ~150 MB

---

## 三、关键发现 — 最大优化机会

### 🔴 问题 #1: `sentence-transformers` 及其依赖链 (~650 MB) — 但实际未使用！

**这是最大的问题。** `sentence-transformers` 在 `pyproject.toml` 中被声明为依赖，但在 `main.py` 中相关代码已被**注释掉**：

```python
# from app.tool_search.selector import select_tools
# from app.tool_search.search_agent import SearchAgent
```

它引入了以下巨大传递依赖:
- `torch`: 353 MB
- `onnxruntime`: 111 MB
- `scipy`: 70 MB
- `transformers`: 54 MB
- `sklearn`: 30 MB
- `sympy`: 29 MB
- 其他 (tokenizers, huggingface_hub, safetensors 等): ~10 MB

**总计: 约 650+ MB 完全无用的依赖！**

### 🟠 问题 #2: `fonts-noto-cjk` 字体 (~120-180 MB)

CJK 字体非常大。可以考虑:
- 只安装 `fonts-noto-cjk-extra` 的子集
- 或使用更轻量的 `fonts-wqy-zenhei`（已安装，~15 MB）单独作为中文字体

### 🟠 问题 #3: `react-icons` (83 MB)

整个 react-icons 库包含数千个图标。PPTX skill 只用到少量图标来渲染 SVG→PNG。考虑:
- 使用按需引入或只安装需要的子包
- 或将常用图标预渲染为 PNG 图片

### 🟡 问题 #4: Node.js 通过 apt 安装 (~80-100 MB)

Debian apt 源中的 Node.js 版本较老且较大。建议:
- 使用 NodeSource 的特定版本安装
- 或使用多阶段构建，只复制 Node 二进制文件

### 🟡 问题 #5: Playwright (~13 MB npm 包 + 浏览器未安装?)

Playwright 在 `html2pptx.js` 中使用 chromium 来渲染 HTML。但 Dockerfile 中**没有安装 Playwright 浏览器**（`npx playwright install chromium`），意味着:
- 这个功能在 Docker 中可能根本无法工作
- 如果不需要，可以移除 playwright 依赖

### 🟡 问题 #6: `git` 系统包 (~20 MB)

Dockerfile 安装了 git，可能用于 `uv` 安装 git 依赖。如果所有依赖都来自 PyPI，可以移除。

---

## 四、前端镜像 (frontend)

前端使用了**多阶段构建**，优化已比较到位:
- 构建阶段: node:20-alpine + 529MB node_modules (临时)
- 运行阶段: node:20-alpine (~180 MB) + Next.js standalone 输出
- 最终镜像预估: ~200-300 MB ✅

---

## 五、优化建议 (按效果排序)

| 优先级 | 操作 | 预估节省 | 难度 |
|--------|------|----------|------|
| P0 | 移除 `sentence-transformers` 依赖 | **~650 MB** | 低 |
| P1 | 精简 CJK 字体 (去掉 noto-cjk 只留 wqy) | **~120-170 MB** | 低 |
| P1 | 精简 react-icons (按需引入或预渲染) | **~80 MB** | 中 |
| P2 | Node.js 安装方式优化 (多阶段) | **~30-50 MB** | 中 |
| P2 | 审视 playwright 是否需要 | **~13 MB** | 低 |
| P2 | 移除 git 系统包 | **~20 MB** | 低 |
| P3 | 使用 `--no-cache-dir` 清理 pip/uv 缓存 | **~10-50 MB** | 低 |
| P3 | 后端也采用多阶段构建 | **~50-100 MB** | 高 |

### 最佳预期效果

如果实施 P0 + P1 优化，可以将后端镜像从 ~2 GB 降到 ~1.0-1.2 GB，减少约 **40-50%**。

