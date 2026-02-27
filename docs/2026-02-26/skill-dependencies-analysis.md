# Skill 依赖分析报告

## 分析日期：2026-02-26

---

## 一、各 Skill 依赖汇总

### 1. PPTX Skill (`backend/skills/default/pptx/`)

#### Python 依赖
| 包名 | 用途 | 来源 |
|------|------|------|
| `python-pptx` | PPTX 解析和操作 | scripts/thumbnail.py, replace.py, rearrange.py, inventory.py |
| `pillow` (PIL) | 缩略图生成、图片处理 | scripts/thumbnail.py, inventory.py |
| `six` | Python 2/3 兼容 | scripts/rearrange.py |
| `defusedxml` | 安全 XML 解析 | ooxml/scripts/unpack.py, pack.py |
| `lxml` | XML Schema 验证 | ooxml/scripts/validation/base.py, docx.py |
| `markitdown[pptx]` | 文本内容提取 | SKILL.md 提及 |

#### Node.js 依赖
| 包名 | 用途 | 来源 |
|------|------|------|
| `pptxgenjs` | HTML 转 PPTX | scripts/html2pptx.js |
| `playwright` | HTML 渲染引擎 | scripts/html2pptx.js |
| `react`, `react-dom` | 图标渲染 | SKILL.md |
| `react-icons` | 图标库 | SKILL.md |
| `sharp` | SVG 光栅化、图片处理 | SKILL.md |

#### 系统依赖
| 包名 | 用途 |
|------|------|
| `libreoffice` | PDF 转换 |
| `poppler-utils` | PDF 转图片 (pdftoppm) |

---

### 2. DOCX Skill (`backend/skills/default/docx/`)

#### Python 依赖
| 包名 | 用途 | 来源 |
|------|------|------|
| `python-docx` | DOCX 创建（Agent 使用） | Agent 运行时需要 |
| `defusedxml` | 安全 XML 解析 | scripts/utilities.py, ooxml/scripts/ |
| `lxml` | XML Schema 验证 | ooxml/scripts/validation/ |

#### Node.js 依赖
| 包名 | 用途 | 来源 |
|------|------|------|
| `docx` | 创建新 Word 文档 | SKILL.md (docx-js workflow) |

#### 系统依赖
| 包名 | 用途 |
|------|------|
| `pandoc` | 文本提取和格式转换 |
| `libreoffice` | PDF 转换 |
| `poppler-utils` | PDF 转图片 |

---

### 3. PDF Skill (`backend/skills/default/pdf/`)

#### Python 依赖
| 包名 | 用途 | 来源 |
|------|------|------|
| `pypdf` | PDF 基础操作（合并、拆分、旋转） | scripts/fill_*.py, check_*.py, extract_*.py |
| `pdfplumber` | 文本和表格提取 | SKILL.md |
| `reportlab` | 创建 PDF | SKILL.md |
| `pillow` (PIL) | 图片处理、验证图生成 | scripts/create_validation_image.py |
| `pdf2image` | PDF 转图片 | scripts/convert_pdf_to_images.py |
| `pytesseract` | OCR 识别 | SKILL.md |
| `pypdfium2` | PDF 渲染引擎 | SKILL.md (reference.md) |

#### 系统依赖
| 包名 | 用途 |
|------|------|
| `poppler-utils` | pdftotext, pdftoppm, pdfimages |
| `qpdf` | PDF 操作命令行工具 |
| `tesseract-ocr` | OCR 引擎（pytesseract 后端） |

---

### 4. XLSX Skill (`backend/skills/default/xlsx/`)

#### Python 依赖
| 包名 | 用途 | 来源 |
|------|------|------|
| `openpyxl` | Excel 读写、公式、格式 | recalc.py, SKILL.md |
| `pandas` | 数据分析 | SKILL.md |

#### 系统依赖
| 包名 | 用途 |
|------|------|
| `libreoffice` | 公式重算 (recalc.py) |

---

### 5. Deep Research Skill (`backend/skills/default/deep-research/`)
- 无额外依赖，使用 MCP 工具 (`call_tool`)

### 6. Exa Search Skill (`backend/skills/default/exa-search/`)
- 无额外依赖，使用 MCP 工具 (`call_tool`)

### 7. 高德地图 Skill (`backend/skills/default/amap/`)
- 无额外依赖，使用 MCP 工具 (`call_tool`)

### 8. Social Media Video Skill (`backend/skills/default/social-media-video/`)
- 无额外依赖，使用 MCP 工具 (`call_tool`)

---

## 二、依赖更新操作记录

### 后端 Python 依赖 (pyproject.toml)

**新增的包：**
- `python-docx` — Agent 创建 DOCX 文件需要
- `defusedxml` — OOXML 安全 XML 解析
- `lxml` — OOXML Schema 验证（已作为间接依赖安装）
- `six` — Python 2/3 兼容层（已作为间接依赖安装）
- `markitdown[pptx]` — PPTX 文本内容提取

**已有的包（无需变更）：**
- python-pptx, reportlab, fpdf, pypdfium2, pypdf, pdfplumber, pdf2image, pytesseract
- pillow, matplotlib, openpyxl, pandas, numpy

### 后端 Node.js 依赖 (backend/package.json)

**新增的包：**
- `docx` (^9.0.0) — 用于创建新 Word 文档

**已有的包（无需变更）：**
- playwright, pptxgenjs, react, react-dom, react-icons, sharp

### 前端依赖 (frontend/package.json)

**已有的包（无需变更）：**
- `docx-preview` — DOCX 文件预览渲染

---

## 三、预览功能修复记录

### DOCX 预览修复
**问题：** `DocxPreviewInline` 组件中，loading 状态时条件渲染导致 container div 不在 DOM 中，`containerRef.current` 为 null，`renderAsync` 无法执行，导致文件永远无法渲染。

**修复：** 重构组件，始终保持 container div 在 DOM 中，使用绝对定位的 overlay 显示 loading/error 状态。

### PPTX 预览
**问题：** 错误信息不够详细，只显示"无法加载 PPTX 文件"。实际的 PPTX 文件可能是空文件(30B)导致解析失败。

**修复：** 增加了详细的错误信息展示和重试按钮。

