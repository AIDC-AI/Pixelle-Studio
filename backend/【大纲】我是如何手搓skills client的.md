# 【大纲】我是如何手搓skills client的

## 引言：为什么要手搓一个 Skills Client

### 1.1 我遇到的问题

*   让agent实现复杂的流程性工作，需要花很长时间调试prompt，且执行不稳定，很难每次都按照按照预期去执行 -》 垂直领域的专家经验确定下来，固定流程用 scripts 代替
    
*   当前的 agent + mcp tools 这套，当 tools 太多，需要按照顺序调用多个 tools，在 prompt 里没法枚举所有场景的 tools 调用顺序，tool 和 tool 之间的传参数据量过大的情况下，都无法实现。把 tool 的调用作为 scripts 里的一个脚本，让 LLM 生成 python 脚本，即可实现调用多个 tool 和传递参数。
    
*   处理复杂任务的时候，很难一把解决到位 -》 ReactAgent，多轮 python 脚本生成运行和根据报错信息/返回参数，进行后续进一步脚本生成；凭借多轮试错降低一次达成复杂任务的难度
    

### 1.2 官方 Agent Skills 解决的三个核心问题

> 引用官方文档：Skills are file-based, reusable resources that give Claude domain-specific expertise.

1.  **专业化 Claude 的能力**：通用模型缺乏"操作性知识"（procedural knowledge）
    
    *   模型知道"Excel 可以做数据分析"，但不知道"这个特定 Excel 模板的公式依赖关系"
        
    *   Skills 把专家经验（代码模板、错误处理、最佳实践）打包成可加载的模块
        
2.  **减少重复性工作**：一次创建，自动复用
    
    *   不必在每次对话中重复解释"怎么用 html2pptx.js"
        
3.  **组合能力**：多个 Skills 协作完成复杂工作流
    
    *   xlsx 处理 + pptx 生成 = 数据报告自动化
        

### 1.3 为什么官方 Skills 不够用

*   只能在 Claude Desktop / Claude Code / Agent SDK 中使用
    
*   无法集成到自己的产品/工作流中
    
*   我决定手搓一个 Skills Client，复刻核心机制，在这个过程中，也更能领会Skills的所有理念，为什么要这么设计，且我的项目与官方实现相比，有一些个人的理解和大胆的尝试。我的项目在：[https://github.com/PixelleLab/mcp-workflow](https://github.com/PixelleLab/mcp-workflow)，对源码感兴趣的同学可以钉钉与我沟通。
    

---

## 端到端案例

手搓的DEMO项目运行起来后，效果如下：

### Excel 处理

*   用户输入 → 多轮执行 → 最终产物
    
*   展示完整的 Agent Loop 流程
    

### PPT 生成

---

## Skills Client 系统设计图

<系统架构图 plantUML语法>

<系统描述>

接下来我们来讲清楚，Skills Client 系统的设计理念。

---

## Skills 的核心理念：把"专家知识"打包成可加载的模块

### 3.1 通用模型缺乏"操作性知识"

通用大模型博学多才，但缺乏具体领域的"操作性知识"。它知道概念，但不知道"怎么做"。

例如：

*   模型知道"可以用 openpyxl 处理 Excel"，但不知道"这个特定模板的公式依赖顺序"
    
*   模型知道"PPT 由幻灯片组成"，但不知道"html2pptx.js 的具体调用方式和参数"
    

Skills 的本质：**把专家的操作性知识固化下来，让模型能够"按图索骥"**。

### 3.2 SKILL 的结构设计

**YAML Frontmatter 的关键作用**：

```yaml
---
name: pptx
description: 生成PowerPoint演示文稿。将HTML幻灯片转换为PPTX格式，支持自定义模板。当用户需要创建PPT、演示文稿或幻灯片时使用。
---

```

*   **name**：64 字符以内，小写字母+数字+连字符
    
*   **description**：技能发现的关键！
    
    *   Claude 用它从可能的 100+ 技能中选择正确的那个
        
    *   必须包含：做什么 + 什么时候用
        
    *   **必须用第三人称**（"生成PPT"而非"我可以帮你生成PPT"）
        

**技能发现机制：**

*   启动时只加载所有技能的 name + description（Level 1）
    
*   Claude 根据用户请求，匹配 description 中的关键词
    
*   匹配成功后才加载完整 SKILL.md（Level 2）
    

**skills/ 目录结构设计：**

```plaintext
skills/
├── pptx/
│   ├── SKILL.md          # 主文档（<500行）
│   ├── html2pptx.md      # 详细文档（按需加载）
│   ├── ooxml.md          # 参考资料（按需加载）
│   └── scripts/
│       └── html2pptx.js  # 辅助脚本
├── xlsx/
│   ├── SKILL.md
│   └── recalc.py

```

### 3.3 skills内容的最优范式

#### 3.3.1 Context Window 是公共资源——简洁是关键

> 官方原话："The context window is a public good. Your Skill shares the context window with everything else Claude needs to know."

**为什么这很重要**：

*   Skills 要和 system prompt、对话历史、其他 Skills 的元数据竞争上下文空间
    
*   一个臃肿的 SKILL.md 会挤压其他信息的空间
    

**我的设计原则**：

1.  **默认假设：Claude 已经很聪明**
    
    *   只添加 Claude 不知道的信息
        
    *   不解释"什么是 PDF"，只告诉"怎么用 pdfplumber"
        
2.  **SKILL.md 控制在 500 行以内**
    
    *   超过就拆分到附加文件
        
    *   用 `[READ_SKILL_FILE: ...]` 按需加载
        
3.  **代码示例 > 文字描述**
    
    *   Bad: "你需要使用 pdfplumber 库来提取文本，首先需要安装它..."（150 tokens）
        
    *   Good: `import pdfplumber; pdf.pages[0].extract_text()`（30 tokens）
        

#### 3.3.2 什么时候用代码，什么时候写文案 -> 设置适当的自由度（Degrees of Freedom）

> 官方类比：想象 Claude 是一个探索道路的机器人

**三种自由度的设计**：

| 自由度 | 适用场景 | 技能内容形式 | 示例 |
| --- | --- | --- | --- |
| **高** | 多种方法都可行 | 文本指令、检查清单 | "分析代码结构，检查潜在bug" |
| **中** | 有推荐模式，允许变化 | 伪代码、带参数的模板 | `def process(data, format="markdown")` |
| **低** | 操作脆弱、易出错 | 特定脚本，无/少参数 | `python scripts/migrate.py --verify` |

**我的实践**：

*   Excel 公式重算 → **低自由度**：必须用 `recalc.py`，不允许自己写
    
*   HTML 转 PPT → **中自由度**：用 `html2pptx.js`，但 HTML 内容自己生成
    
*   代码审查 → **高自由度**：按 SKILL.md 的检查点自行发挥
    

#### 3.3.3 XML 格式优于纯文本

*   对 Claude 的注意力机制更友好
    
*   结构化标签帮助模型定位关键信息
    
*   我的 `build_skills_xml_prompt()` 方法生成 `<available_skills>` XML 块
    

---

## 渐进式加载：让模型"按需拿信息"而非"被信息淹没"

### 4.1 为什么不能一次性加载所有技能文档

*   10 个技能，每个 500 行 → 5000 行涌入上下文
    
*   大部分内容与当前任务无关
    
*   挤占了对话历史和推理空间
    

### 4.2 三层 Progressive Disclosure 设计

| 层级 | 内容 | 加载时机 | Token 消耗 |
| --- | --- | --- | --- |
| Level 1 | name + description | **始终加载** | ~20-50 tokens/skill |
| Level 2 | SKILL.md 主体 | 用户请求匹配时 | ~200-500 tokens |
| Level 3 | 附加文件（md/js/py） | Agent 主动请求时 | 按需 |

### 4.3 我的实现

*   启动时扫描所有 skills/，提取 frontmatter
    
*   构建 `<available_skills>` XML 块注入 system prompt
    
*   只有 Level 1 信息，总计约 200-300 tokens
    

#### 4.3.1 `**parse_skill_links()**` 主动发现关联文档

*   解析 SKILL.md 中的 markdown 链接
    
*   告诉 Agent："这个技能还有 html2pptx.md 可以读"
    
*   Agent 决定是否需要进一步加载
    

---

## Pseudo Tool Call vs Native Tool Call：为什么我选择"伪工具调用"

### 5.1 两种方案的对比

| 维度 | Native Tool Call | Pseudo Tool Call |
| --- | --- | --- |
| 实现方式 | OpenAI function calling 协议 | 文本标记 + 正则解析 |
| 依赖 | 需要支持 tool\_call 的 API | 任何 LLM API 都行 |
| 调试 | 需要解析 JSON | 全是文本，日志可读 |
| 灵活性 | 受限于协议 | 可随意扩展 |

### 5.2 我选择 Pseudo Tool Call 的理由

*   **与渐进式加载配合**：三种"伪工具"对应三层加载
    
    *   `[LOAD_SKILL: name]` → 加载 Level 2
        
    *   `[READ_SKILL_FILE: name, path]` → 加载 Level 3
        
    *   `[LIST_SKILL_TREE: name]` → 发现可用资源
        
*   **实现简单**：不依赖 OpenAI function calling 协议
    
*   **调试友好**：全是文本，日志可读
    

### 5.3 文本标记 + 正则解析的实现

```python
# 检测 skill 加载请求
if "[LOAD_SKILL:" in response_text:
    match = re.search(r'\[LOAD_SKILL:\s*(\w+)\s*\]', response_text)
    if match:
        skill_name = match.group(1)
        return AgentAction(action_type="read_skill", skill_name=skill_name)

# 检测代码块
if "```python" in response_text:
    code_start = response_text.find("```python") + 9
    code_end = response_text.find("```", code_start)
    code = response_text[code_start:code_end].strip()
    return AgentAction(action_type="execute_code", content=code)

```

### 5.4 与官方 MCP 工具的区别

官方文档提到：使用 MCP 工具时要用全限定名 `ServerName:tool_name`

我的选择：

*   **不使用 MCP 协议**：简化实现，避免额外的服务依赖
    
*   **用脚本代替工具**：Skills 指导 LLM 生成代码，而非调用预定义工具
    
*   这是与官方方案的**最大差异**（后面详述）
    

---

## 【重点】一句话触发，多轮 LLM + ToolCall 闭环执行

> 这是整个系统的"心脏"——用户只说一句话，Agent 自动进行多轮决策和执行，直到任务完成。

### 6.1 为什么需要多轮？

*   **单轮无法完成复杂任务**：用户说"帮我做一个 PPT"，这不是一次 LLM 调用就能搞定的
    
    *   第一轮：理解需求，决定需要什么 skill
        
    *   第二轮：加载 skill 文档，获取操作指南
        
    *   第三轮：读取细节文档（如 html2pptx.md）
        
    *   第四轮：生成代码
        
    *   第五轮：看到执行结果，判断是否成功
        
    *   第六轮（如果失败）：分析错误，生成修复代码
        
    *   ...
        
*   **每一轮都是"LLM 决策 + 可能的 ToolCall"**：
    
    *   LLM 决定下一步做什么（回答/加载skill/读文件/执行代码）
        
    *   如果是 ToolCall（加载skill、读文件、执行代码），执行后把结果喂回 LLM
        
    *   LLM 基于新信息继续决策
        

### 6.2 Agent Loop 的状态机设计

*   **循环结构**：`while tool_call_count < max_tool_calls`
    
*   **每轮的三个阶段**：
    
    1.  **构建上下文**：system prompt（含已加载的 skills）+ 历史 messages
        
    2.  **调用 LLM**：获取 assistant 回复
        
    3.  **解析 action**：判断是终止（直接回复）还是继续（执行 toolcall）
        
*   **四种 action 类型**：
    
    *   `respond`：直接回复用户，循环结束
        
    *   `read_skill`：加载 SKILL.md，结果注入上下文，继续循环
        
    *   `read_skill_file`：读取细节文件，结果注入上下文，继续循环
        
    *   `execute_code`：执行代码，结果注入上下文，继续循环
        

### 6.3 关键机制：执行结果如何回灌给 LLM

*   **问题**：LLM 生成了代码，执行后的 stdout/stderr 怎么让 LLM 看到？
    
*   **设计**：把执行结果作为"下一轮的 user message"
    

```plaintext
[Execution Result]
Status: success/error
Stdout: ...
Stderr: ...

Based on this result, either:
1. If the task is complete, provide a final response
2. If there was an error, generate corrected code

```

*   **为什么用 user role**：兼容 OpenAI 协议，避免奇怪的 role 问题
    
*   **这使得 LLM 能够**：
    
    *   看到真实执行结果
        
    *   判断任务是否完成
        
    *   如果出错，分析错误原因并修复
        
*   **【重要】history messages存储机制：**
    
    *   **如果把所有执行细节都存储到history messages里，一个是不符合事实情况，用户只说了一句话，一个是把太多中间结果也保留到了后续的上下文里，占用过多空间。**
        
    *   **因此，history messages里，只存储真实用户说的那一句话，以及执行完所有内容后最终的ai message**
        

### 6.4 Plan-Validate-Execute 模式

> 官方推荐：对于复杂任务，让 Claude 先输出计划文件，验证后再执行

**我的实现**：

1.  Agent 生成代码 → 执行
    
2.  执行后检查 JSON 结果的 `status` 字段
    
3.  如果失败，错误信息 + SKILL.md 中的错误处理指南 → 再次生成
    

**为什么这很重要**：

*   单次生成可能出错（幻觉、理解偏差）
    
*   多轮验证形成**闭环反馈**
    
*   错误信息是最好的"教材"
    

### 6.5 一个完整的多轮执行示例

```plaintext
用户: "帮我分析这个 Excel 文件，生成一个汇总表"

第1轮 LLM: 看到 skills 索引，决定需要 xlsx skill
       → [LOAD_SKILL: xlsx]
       → 执行: 加载 xlsx/SKILL.md
       → 结果注入上下文

第2轮 LLM: 看到 SKILL.md 内容，了解了 pandas/openpyxl 用法
       → 生成 Python 代码（读取文件、分析、生成汇总表）
       → 执行: 运行脚本
       → 结果: 成功，输出了 summary.xlsx

第3轮 LLM: 看到执行成功
       → 直接回复: "我已经帮你生成了汇总表，下载链接是..."
       → 循环结束

```
---

## 【重点】为什么用脚本生成和执行，而不是直接调用工具

> 这是另一个核心设计决策——Agent 的"做事能力"通过生成和执行 Python 脚本来实现。

### 7.1 为什么不是"直接调用工具/API"

*   **对比：传统 Tool Call 方式**
    
    *   预定义一组工具（如 `read_excel(path)`、`write_excel(data, path)`）
        
    *   LLM 选择调用哪个工具，传什么参数
        
    *   平台执行工具，返回结果
        
*   **问题：工具粒度与灵活性的矛盾**
    
    *   粒度太粗（一个工具做一件大事）→ 无法处理复杂/定制需求
        
    *   粒度太细（每个操作一个工具）→ 工具数量爆炸，LLM 选择困难
        
*   **脚本的优势：无限灵活性**
    
    *   LLM 可以生成任意逻辑的代码
        
    *   可以组合任何库（pandas、openpyxl、subprocess...）
        
    *   可以处理任意复杂的业务需求
        

### 7.2 脚本生成的独特优势

*   **可追溯**：
    
    *   每个脚本落盘保存（`scripts/{session}_{count}_{uuid}.py`）
        
    *   出问题可以直接查看生成了什么代码
        
    *   可以单独重跑脚本复现问题
        
*   **可组合**：
    
    *   一个脚本可以调用多个库、多个 skill 资源
        
    *   复杂任务可以在一个脚本中完成，而不是拆成 N 个工具调用
        
*   **利用 skill 资源**：
    
    *   脚本可以调用 skill 目录下的辅助工具（如 `html2pptx.js`、`recalc.py`）
        
    *   这是预定义工具无法做到的
        
*   **与 Skills 体系天然契合**：
    
    *   SKILL.md 里有代码模板和最佳实践
        
    *   LLM 按照指南生成代码，而不是选择预定义工具
        

### 7.3 技术实现：从代码检测到结果回收

**Step 1：代码块检测**

*   从 LLM 回复中检测 ````python ```` 标记
    
*   提取代码内容
    

**Step 2：skill\_helpers 注入**

为什么需要 skill\_helpers？

*   **官方方案**：Claude Code 有完整的文件系统访问，可以直接 `cat skills/pptx/...`
    
*   **我的限制**：脚本在隔离环境执行，需要知道资源路径
    

我的设计：自动注入两个辅助函数

```python
# 自动注入到每个执行脚本头部
def skill_path(skill_name: str, *parts) -> str:
    """获取技能资源路径：skills/<skill_name>/[parts...]"""
    return os.path.join("skills", skill_name, *parts)

def script_path(*parts) -> str:
    """获取脚本目录路径：scripts/[parts...]"""
    return os.path.join("scripts", *parts)

```

这样 LLM 生成的代码可以：

*   `skill_path("pptx", "scripts", "html2pptx.js")` → 调用辅助脚本
    
*   `script_path("output.pptx")` → 输出到正确位置
    

**Step 3：脚本落盘**

*   保存到 `scripts/` 目录
    
*   命名规则：`{session_id}_{execution_count}_{random}.py`
    
*   便于追溯和调试
    

**Step 4：子进程执行**

*   使用 `asyncio.create_subprocess_exec` 启动子进程
    
*   与主服务隔离，脚本崩溃不影响主进程
    

**Step 5：stdout/stderr 并发采集**

*   用 asyncio Queue 并发收集两个流
    
*   实时 yield 日志给前端（用户可以看到执行过程）
    

**Step 6：JSON 结果解析**

*   约定脚本最后 print 一个 JSON（`{"status": "success", "result": "...", "output_file_names": [...]}`)
    
*   从 stdout 中检测并解析 JSON
    

**Step 7：输出文件处理**

*   如果有 `output_file_names`，检查文件是否生成
    
*   生成下载 URL（`http://{ip}:{port}/f/{filename}`）
    
*   返回给用户
    

### 7.4 脚本执行的工作目录设计

*   **执行目录 = backend/**：脚本以 backend 为根目录运行
    
*   **用户上传的文件在 scripts/**：脚本可以直接 `pd.read_excel(script_path("9120.xlsx"))`
    
*   **输出文件也在 scripts/**：统一管理，便于清理和服务
    
*   **技能资源在 skills/**：通过 `skill_path()` 访问
    

### 7.5 脚本方案 vs Tool Call 方案的对比总结

| 维度 | 预定义 Tool Call | 脚本生成执行 |
| --- | --- | --- |
| 灵活性 | 受限于预定义工具 | 无限灵活 |
| 复杂任务 | 需要多次工具调用 | 一个脚本搞定 |
| 可追溯 | 只有调用记录 | 完整代码可查 |
| 利用 skill 资源 | 难 | 天然支持 |
| 安全性 | 受控 | 需要额外防护 |

---

## 与官方 Agent Skills 的设计对比

### 8.1 借鉴了什么

| 官方理念 | 我的实现 |
| --- | --- |
| Context Window 是公共资源 | SKILL.md < 500 行，XML 格式 |
| 三层渐进式加载 | `[LOAD_SKILL]` / `[READ_SKILL_FILE]` / `[LIST_SKILL_TREE]` |
| 自由度设计 | 低自由度用固定脚本，高自由度给指令 |
| YAML Frontmatter | name + description 用于技能发现 |
| 脚本解决问题而非转嫁给 Claude | `recalc.py` / `html2pptx.js` 封装复杂逻辑 |

### 8.2 舍弃了什么

| 官方能力 | 我的取舍 | 原因 |
| --- | --- | --- |
| MCP 工具协议 | 不使用 | 简化架构，避免服务依赖 |
| Native Tool Call | 用 Pseudo Tool Call | 不依赖 function calling，实现简单 |
| Claude Code 的文件系统完整访问 | 通过 skill\_helpers 抽象 | 脚本在隔离环境执行 |

---

## 未来展望

*   自动生成 skills/ 目录结构和 SKILL.md 文件，包括 name、description、依赖的脚本、资源文件等。