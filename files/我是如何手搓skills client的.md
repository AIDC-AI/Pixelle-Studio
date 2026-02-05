# 我是如何手搓skills client的

## 引言：为什么要手搓一个 Skills Client

### 1.1 我遇到的问题：当 Prompt Engineering 走到尽头

相信做 Agent 开发的同学都有过这种绝望时刻：

你写了一个几百行的 Prompt，试图让 Agent 帮你完成一套复杂的业务流程（比如"读取Excel，清洗数据，生成图表，最后做成PPT"）。你花了一下午调试 Prompt，终于跑通了一次。结果第二天换了一份数据，或者仅仅是微调了 System Prompt 的一句话，整个流程就崩了——Agent 要么在死循环里打转，要么在这个 Tool 和那个 Tool 之间来回传递错误的参数。

我深刻体会到，**单纯依靠 Prompt 和简单的 Tool Calling 来驱动复杂流程，极其脆弱且不稳定。**

在实践中，我遇到了三个无法回避的瓶颈：

![image](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/5VLqXLby4aQoVqX1/img/e721bc2c-e22a-4904-a676-749412da46a2.png)

### 1.2 官方 Agent Skills 解决的三个核心问题

正当我焦头烂额时，Anthropic 官方提出了 **Agent Skills** 的概念。虽然官方的定义比较抽象（_"Skills are file-based, reusable resources..."_），但我读完文档后，感觉它是为了解决三个核心问题而生的：

1.  **专业化 Claude 的能力（赋予"操作性知识"）**： 通用大模型像个博学的教授，它知道"Excel 可以做数据分析"（陈述性知识），但它不知道"处理这个公司的月度报表时，必须先删除第三行的空值"（操作性知识）。Skills 就是把这些代码模板、错误处理逻辑、最佳实践打包，让模型不仅"懂"，而且"会做"。
    
2.  **减少重复性工作**： 不管是谁来问，只要涉及到"转PPT"，就不需要再在 Prompt 里重复教模型怎么调用 `html2pptx.js`。一次定义，永久复用。
    
3.  **组合能力**： Skill A (Excel处理) + Skill B (PPT生成) = 自动化数据报告。这种模块化的组合能力，是构建复杂应用的基础。
    

### 1.3 为什么官方 Skills 不够用

官方的理念很棒，但目前的生态（Claude Desktop / Claude Code）对我来说有点"封闭"：

*   它主要绑定在官方的客户端或 SDK 中。
    
*   我想把它集成到我自己的 Web 产品里，嵌入到我的业务工作流中。
    
*   我想要更灵活的控制权，比如自定义代码的执行环境，或者魔改技能的加载逻辑。
    

于是，我决定**手搓一个 Skills Client**。我不想只是简单的"调用工具"，我要复刻 Skills 的核心机制（渐进式加载、专家知识库），并结合我对 Agent 的理解（Python 脚本生成 vs 工具调用），做一次大胆的尝试。

我的项目源码在：[https://github.com/AIDC-AI/Pixelle-Studio](https://github.com/AIDC-AI/Pixelle-Studio)，欢迎大家钉钉交流。

---

## 端到端案例

光说不练假把式。在这个手搓的 Client 运行起来后，效果是这样的：

### Excel 处理与自动化分析

用户只需上传一个 Excel 文件并说一句："帮我分析这个销售数据，把异常值标红。"

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/3BMqYybQ4yGkEqwZ/img/6f2ee31e-2bf6-459b-8bd0-faf743ba65b4.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/3BMqYybQ4yGkEqwZ/img/f32d85c4-4a78-4ce3-ba79-34f35941cb4d.png)

Agent 会自动经历"加载 xlsx 技能 -> 阅读技能文档 -> 编写 Python 代码 -> 执行代码 -> 发现并修复错误 -> 输出结果"的全过程，用户完全无感。

### PPT 智能生成

用户："根据刚才的分析结果，生成一份 PPT 简报。"

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/3BMqYybQ4yGkEqwZ/img/46f4d377-5119-40f9-a836-7b0291573530.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/3BMqYybQ4yGkEqwZ/img/179e2c82-0446-4eea-a143-9d1f6eb6c198.png)

这背后，是 Agent 调用了 `pptx` Skill 中的 `html2pptx.js` 脚本，将 LLM 生成的 HTML 结构完美转换成了原生 PPT。

### html生成

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/3BMqYybQ4yGkEqwZ/img/321b7430-7a65-4a30-bd39-e87d57d6d4e6.png)

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/3BMqYybQ4yGkEqwZ/img/1bc949e5-53cf-40e4-a23d-d491f40b94da.png)

---

## Skills Client 系统设计图

为了实现上述效果，我设计了如下的系统架构。核心思想是\*\*"一个聪明的大脑（Agent）+ 一个博学的图书馆（SkillLoader）+ 一个勤劳的手（Code Runner）"\*\*。

![image](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/5VLqXLby4aQoVqX1/img/d6f809ba-7c51-47e8-b359-f229fc40310d.png)

### 系统描述

这个架构主要由三个核心部分组成：

1.  **SkillAgent (**`**backend/app/agent.py**`**)**：这是系统的大脑。它维护着对话循环（Agent Loop），负责根据用户的输入和当前的状态，决定是直接回复、去"图书馆"查资料（Load Skill），还是动手写代码（Execute Code）。
    
2.  **SkillLoader (**`**backend/app/skills/loader.py**`**)**：这是系统的"图书馆管理员"。它管理着 `skills/` 目录下所有的资源，实现了"渐进式加载"的核心逻辑。它负责告诉 Agent "我们要有哪些技能"，并在 Agent 需要时，精准地把特定的文档或脚本递给它。
    
3.  **Code Runner**：这是系统的执行手。它在一个相对隔离的环境中运行 Agent 生成的 Python 脚本。最关键的设计是，我们通过 `skill_helpers` 让生成的脚本能够轻松调用 `skills/` 目录下的辅助工具（如 `recalc.py` 或 `html2pptx.js`），实现了代码生成的无限扩展。
    

接下来，我们将深入代码细节，讲清楚 Skills Client 系统设计的每一个核心理念。

---

## Skills 的核心理念：把"专家知识"打包成可加载的模块

### 3.1 通用模型缺乏"操作性知识"

我们经常高估了通用大模型在特定任务上的执行力。

通用模型就像一个博学多才的大学教授。你问他"Excel 是什么"，他能从 VisiCalc 讲到 Office 365（陈述性知识）。但如果你丢给他一个乱七八糟的财务报表，让他"把所有公式重算一遍并修正循环引用"，他往往会给你一段看着很有道理、跑起来全是 Bug 的 Python 代码。

为什么？因为他缺乏**操作性知识（Procedural Knowledge）**。

他不知道这个特定 Excel 模板的计算依赖顺序，不知道某些库在特定版本下的兼容性问题。**Skills 的本质，就是把专家的操作性知识固化下来，让模型能够"按图索骥"。**

### 3.2 SKILL 的结构设计：从 YAML 开始

在我的设计中，每个 Skill 都是一个文件夹，入口是 `SKILL.md`。这个文件最关键的部分，是头部的 **YAML Frontmatter**。

我们在 `backend/app/skills/loader.py` 中实现了对它的解析：

```python
# 截取自 backend/app/skills/loader.py
def _extract_metadata(self, skill_md_path: Path, skill_dir: Path) -> Optional[SkillMeta]:
    # ... (省略读取代码)
    # Extract YAML frontmatter (between --- markers)
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    # ...


```

一个典型的 `SKILL.md` 头部是这样的：

```yaml
---
name: pptx
description: 生成PowerPoint演示文稿。将HTML幻灯片转换为PPTX格式，支持自定义模板。当用户需要创建PPT、演示文稿或幻灯片时使用。
---


```

这两个字段看似简单，实则至关重要：

*   **name**：是技能的唯一标识，Agent 加载技能时就靠它。建议用简短的小写字母（如 `pptx`, `data-analysis`）。
    
*   **description**：这是\*\*技能发现（Skill Discovery）\*\*的关键！
    
    *   在系统启动时，Agent 只会看到所有技能的 `description`。
        
    *   Claude 会根据用户的 Prompt（"帮我做个胶片"），去语义匹配所有的 `description`。
        
    *   **技巧**：必须使用**第三人称**描述功能（"生成PPT"），并明确写出**适用场景**（"当用户需要...时使用"），这样匹配准确率最高。
        

**目录结构设计**： 我参考了官方的最佳实践，采用了这样的结构：

```plaintext
skills/
├── pptx/
│   ├── SKILL.md          # 【核心】主文档（<500行），Level 2 加载
│   ├── html2pptx.md      # 【扩展】详细文档，Level 3 按需加载
│   ├── ooxml.md          # 【参考】更底层的资料
│   └── scripts/
│       └── html2pptx.js  # 【工具】专家写好的"瑞士军刀"
├── xlsx/
│   ├── SKILL.md
│   └── recalc.py         # 专门处理复杂重算的脚本


```

### 3.3 Skills 内容的最优范式

#### 3.3.1 Context Window 是公共资源——简洁是关键

官方文档里有一句振聋发聩的话：**"The context window is a public good."（上下文窗口是公共资源）。**

你的 Skill 不是主角，它要和 System Prompt、长长的对话历史、用户上传的文件内容，甚至其他 Skills 共享有限的 Context Window。如果你写了一个 2000 行的 `SKILL.md`，里面废话连篇，那留给 Agent 思考和推理的空间就被挤压了。

我的设计原则是：

1.  **默认假设 Claude 已经很聪明**：不要解释"什么是 PDF"，直接告诉他"用 `pdfplumber` 库，参数设为 `x`"。
    
2.  **SKILL.md 控制在 500 行以内**：它是索引，不是百科全书。太长了就拆分到附加文件里。
    
3.  **代码示例 > 文字描述**：
    
    *   _Bad_: "你需要使用 pdfplumber 库来提取文本，首先需要安装它..."（废话，浪费 Token）
        
    *   _Good_: `import pdfplumber; pdf.pages[0].extract_text()`（代码本身就是最精准的语言）
        

#### 3.3.2 什么时候用代码，什么时候写文案？

这就涉及到了\*\*自由度（Degrees of Freedom）\*\*的设计。我们要像设计游戏关卡一样设计 Skill：

![image](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/5VLqXLby4aQoVqX1/img/5dbd9d0b-cdc7-4676-b050-02911b639ab6.png)

**我的实践**：

*   Excel 公式重算 → **低自由度**：必须用 `recalc.py`，不允许自己写
    
*   HTML 转 PPT → **中自由度**：用 `html2pptx.js`，但 HTML 内容自己生成
    
*   代码审查 → **高自由度**：按 SKILL.md 的检查点自行发挥
    

#### 3.3.3 XML 格式优于纯文本

在 `loader.py` 的 `build_skills_xml_prompt` 方法中，我特意将 Skills 包装成了 Claude 最喜欢的 XML 格式：

```python
# 截取自 backend/app/skills/loader.py
skills_xml_parts.append(f"""<skill>
<name>{skill.name}</name>
<description>{description}</description>
</skill>""")


```

结构化的标签能帮助模型更精准地定位关键信息，避免幻觉。

这么设计是参考Claude Skills的官方system prompt：

```xml
<skills_instructions>
When users ask you to perform tasks, check if any of the available skills below can help complete the task more effectively.

How to use skills:
- Invoke skills using this tool with the skill name only (no arguments)
- When you invoke a skill, you will see <command-message>The "{name}" skill is loading</command-message>
- The skill's prompt will expand and provide detailed instructions

Important:
- Only use skills listed in <available_skills> below
- Do not invoke a skill that is already running
</skills_instructions>

<available_skills>
<skill>
<name>pdf</name>
<description>Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, and handling forms...</description>
<location>plugin</location>
</skill>

<skill>
<name>xlsx</name>
<description>Comprehensive spreadsheet creation, editing, and analysis with support for formulas, formatting, data analysis...</description>
<location>plugin</location>
</skill>
</available_skills>

```
---

## 渐进式加载：让模型"按需拿信息"而非"被信息淹没"

### 4.1 为什么不能一次性加载所有技能文档？

试想一下，如果你有 20 个技能，每个说明书 500 行，总共 10000 行。如果每次对话都把这一万行塞进 System Prompt：

1.  **贵**：Token 也是钱。
    
2.  **慢**：首字延迟变高。
    
3.  **笨**：大量无关信息会干扰模型的注意力（Attention），导致它忽略用户真正的指令。
    

### 4.2 三层 Progressive Disclosure 设计

我实现了一套\*\*渐进式披露（Progressive Disclosure）\*\*机制，把信息分为三层：

| 层级 | 内容 | 加载时机 | Token 消耗 | 对应实现 |
| --- | --- | --- | --- | --- |
| **Level 1** | name + description | **始终加载** (System Prompt) | 极小 (~50/skill) | `loader.scan_skills()` |
| **Level 2** | SKILL.md 主体 | **匹配后加载** (`[LOAD_SKILL]`) | 中等 (~500) | `loader.read_skill()` |
| **Level 3** | 附加文件 (md/js/py) | **Agent 主动请求** (`[READ_SKILL_FILE]`) | 按需 | `loader.read_skill_file()` |

### 4.3 我的实现细节

在 `backend/app/agent.py` 中，Agent 的 System Prompt 初始状态非常干净，只有 Level 1 的信息：

```python
# 初始 System Prompt 中的 skills 部分
<available_skills>
<skill>
<name>pptx</name>
<description>生成PowerPoint演示文稿...</description>
</skill>
<skill>
<name>xlsx</name>
<description>处理Excel文件...</description>
</skill>
</available_skills>


```

当用户问"怎么做PPT"时，Agent 发现 `pptx` 的描述匹配，于是输出 `[LOAD_SKILL: pptx]`。 此时，System Prompt 才会注入 Level 2 的详细文档。

我还做了一个贴心的设计：**主动发现关联文档**。 在 `loader.py` 中，`parse_skill_links` 方法会扫描 `SKILL.md` 里的 Markdown 链接：

```python
# 截取自 backend/app/skills/loader.py
def parse_skill_links(self, skill_name: str) -> List[LinkInfo]:
    # 正则提取 [text](path) 链接
    # ...


```

如果 `SKILL.md` 里提到了 `[查看详细参数](html2pptx.md)`，Agent 加载技能后会收到系统提示："检测到该技能还有 `html2pptx.md` 详细文档，如果需要请读取。" 这就是从 Level 2 到 Level 3 的桥梁。

---

## 架构演进：从正则匹配到 Hybrid Tool Calling

在开发过程中，我的架构经历了一次重大的自我否定与迭代，最终形成了一套独特的**Hybrid Tool Calling**机制。得益于ai coding的发展，我们可以快速验证方案是否可行以及做基本底层架构的变动，而不那么顾虑历史包袱。

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/3BMqYybQ4yGkEqwZ/img/9b139bdf-9566-41b5-80f6-b8c9e4a5e0de.png)

### 5.1 第一版：正则匹配 (Pseudo Tool Call) 的幻灭

一开始，为了追求极致的灵活性和 Token 节省，我确实使用了基于正则的"伪工具调用"。比如约定 LLM 输出 `[LOAD_SKILL: pptx]` 就加载技能。

但随着系统变复杂，这个方案的**两层风险**暴露无遗：

1.  **关键词冲突风险**：如果用户或者 Skill 文档里恰好包含了 `[LOAD_SKILL: ...]` 这样的字符串（比如我在写这篇技术报告时），正则就会误判，导致系统疯狂递归加载。
    
2.  **LLM 的不稳定性**：让 LLM 严格遵守自定义的文本格式比让它输出 JSON 难多了。它经常会发挥创意，比如写成 `[Load Skill: pptx]` 或者 `(LOAD_SKILL: pptx)`，正则写得再复杂也防不胜防。
    

### 5.2 回归 Native Tool Calling

为了解决稳定性问题，我最终决定**拥抱标准**，将架构迁移到了 **OpenAI Agents SDK** 和标准的 **Function Calling** 体系。

现在，`load_skill`、`list_skill_tree` 都是标准的 Tool。这带来了巨大的好处：

*   **稳定性**：模型经过了针对性的训练，Tool Call 的意图识别非常精准。
    
*   **生态兼容**：未来对接 MCP (Model Context Protocol) 协议变得顺理成章，因为 MCP 本质上也是基于 Tool Calling 的。
    

### 5.3 遇到的新难题：长代码传输的"死胡同"

但是，当我也想把 `execute_code` 迁移到标准 Tool Call 时，我撞上了一堵墙。

标准的 Tool Calling 协议要求我们将所有参数都封装在一个 JSON 对象里。如果你只是传一个文件名，那没问题；但如果你要求 Agent 写一段 50 行甚至 100 行的 Python 代码，并把它作为一个字符串参数塞进 JSON 里，事情就变得非常糟糕：

1.  **转义地狱**：Python 代码里充满了引号、换行符和缩进。要把它塞进 JSON 的 value 里，必须进行极其繁琐的转义。模型经常因为少写了一个转义符，导致整个 JSON 解析失败。
    
2.  **模型能力的短板**：很多非顶尖模型（或者被量化过的模型），在 Tool Call 的参数里生成长文本时，能力会显著下降。它们习惯了在正文里挥洒代码，一旦被限制在 JSON 结构里，代码质量和逻辑连贯性都会打折扣。
    
3.  **Context 浪费**：大量的转义字符浪费了宝贵的 Token。
    

我发现，**"用 Tool 参数传代码"** 这条路，走不通。

### 5.4 Hybrid 模式与 Context 中转

为了兼顾"Tool Call 的控制流稳定性"和"正文生成的代码质量"，我构思了一个 **Hybrid 模式**。这个模式的核心思想是：**代码生成与指令触发分离，通过 Context 进行"空中加油"。**

具体流程是这样的：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/3BMqYybQ4yGkEqwZ/img/72f583b4-b783-40ae-ae57-f5508334f259.png?x-oss-process=image/crop,x_0,y_62,w_1024,h_497/ignore-error,1)

#### 第一步：Payload（正文生成）

我允许 Agent 在回复的正文中，用 `<execute lang="python">...</execute>` 标签包裹代码。这属于文本生成，模型写起来最舒服，不用管转义，还能配合 Markdown 语法高亮，写代码时还能带上注释和思考过程。

#### 第二步：Extraction & Storage（提取与暂存）

这是最关键的技术细节。在后端 `backend/app/agent.py` 处理流式响应时，我增加了一个**实时提取器**。 当系统检测到 `<execute>` 标签闭合时，会立即将里面的代码提取出来，并**存入到当前会话的 Agent Context 队列中**。

```python
# 伪代码逻辑
if "<execute>" in response_stream:
    code_block = extract_code(response_stream)
    agent_context.pending_code_queue.append(code_block)  # 存入上下文

```

#### 第三步：Trigger（无参触发）

Agent 写完代码后，只需要调用一个**不带任何参数**的 `execute_code()` 工具。 这就像是一个"确认按钮"。Agent 只是在告诉系统："我代码写好了（在正文里），请执行它。"

#### 第四步：Execution（上下文获取）

当 `execute_code` 工具被执行时，它不会去查参数（因为没有参数），而是直接去 **Agent Context** 里取出最新的一段代码来执行。

```python
# 工具实现逻辑
@function_tool
async def execute_code(ctx: RunContextWrapper[AgentContext]) -> str:
    # 直接从上下文中获取代码，而不是从参数获取
    if ctx.context.pending_code_queue:
        code = ctx.context.pending_code_queue.pop()
        return run_python(code)

```

**这种设计的精妙之处在于：**

1.  **模型侧**：Agent 觉得它只是在写文档（正文代码）和按按钮（Tool Call），负担极小。
    
2.  **系统侧**：我们巧妙地利用了 Context 做中转，绕过了 JSON 传输长文本的限制。
    
3.  **结果**：既拥有了 Tool Call 的精准意图识别，又拥有了纯文本生成的代码质量。
    

### 5.5 终极进化：隐式触发 (Implicit Trigger) 与合成调用链

在实践了 5.4 的 Hybrid 模式一段时间后，我发现即便将 `execute_code` 简化为无参调用，依然存在两个顽固的概率性问题：

1.  **忘记按按钮**：模型写完代码，尤其是很长的代码后，注意力涣散，觉得自己已经回答完了，忘记调用 `execute_code`。
    
2.  **抢跑（Premature Execution）**：对于响应速度极快的模型，有时代码还没写完，它就急着并发调用工具，导致执行了空代码。
    

这促使我思考：**既然** `**execute_code**` **只是一个毫无参数的确认按钮，为什么一定要让 LLM 去按呢？闭合的** `**</execute>**` **标签本身不就是最好的按钮吗？**

于是，我设计了\*\*隐式触发（Implicit Trigger）\*\*机制，这也是目前系统中最稳定的方案。

#### 核心逻辑：Synthetic Tool Call（合成工具调用）

这是一种\*\*"后端欺骗"\*\*的技术。在 LLM 看来，它只是按要求在正文中写了代码。但在后端，我手动介入了 Agent Loop，构造了一条虚假的工具调用历史。

**流程如下：**

1.  **LLM 生成**：Agent 输出文本 `... <execute>print("hello")</execute>`。
    
2.  **后端捕获**：流式解析器检测到 `</execute>` 闭合标签。
    
3.  **自动执行**：系统立即提取代码并执行，获得结果 `hello`。
    
4.  **历史篡改（The Magic）**：
    
    *   系统修改 Agent 刚刚的那条消息，给它强行加上 `tool_calls=[{name: "execute_code", args: "..."}]` 属性。
        
    *   紧接着，系统插入一条 `role: "tool"` 的消息，内容是执行结果。
        
    *   **在 LLM 的记忆里，它"以为"自己刚刚主动调用了工具，并且收到了结果。**
        

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/3BMqYybQ4yGkEqwZ/img/dc9cc995-68a9-4005-a6de-992983aab1d3.png)

#### 效果如何？

*   **零认知负担**：LLM 不需要分心去思考"我什么时候该调用工具"，它只需要专注写代码。
    
*   **绝对可靠**：触发逻辑由确定性的代码控制（检测到标签即触发），消除了模型概率性遗忘的风险。
    
*   **完美兼容**：通过合成标准的 Tool Call 历史，这套机制可以无缝融入任何基于 OpenAI API 的标准 Agent 框架（如 LangChain 或 AutoGen），下游组件完全不需要修改。
    

这标志着我的架构从"教模型用工具"进化到了"模型意图的自动执行"，Agent 的稳定性达到了前所未有的高度。

---

## 【重点】一句话触发，多轮 LLM + ToolCall 闭环执行

这是整个系统的"心脏"——用户只说一句话（比如"帮我做个PPT"），Agent 就像一个不知疲倦的员工，自动进行多轮决策和执行，直到任务完成。

### 6.1 为什么需要多轮？

很多初学者容易把 Agent 想象成"一问一答"的聊天机器人。但现实中的复杂任务，绝不是一次 LLM 调用就能搞定的，而更多的是以ReactAgent形态来实现。

以"分析 Excel 并生成图表"为例，Agent 的内心戏其实是这样的：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/3BMqYybQ4yGkEqwZ/img/ce335294-9ca5-49d9-a14c-39c1019816ec.png)

1.  **第一轮（观察）**：用户给了个 Excel，我得先看看里面有啥。怎么看？写个 Python 脚本读取前几行。
    
2.  **第二轮（规划）**：哦，原来是销售数据。那我要算一下总销售额。我得去加载 `xlsx` 技能看看有没有现成的计算模板。
    
3.  **第三轮（执行）**：加载完技能了，参考模板写个脚本算一下。
    
4.  **第四轮（验证）**：哎呀，脚本报错了，说是有一列数据格式不对。别急，我看看报错信息，改一下代码重跑。
    
5.  **第五轮（交付）**：算出来了，结果保存成文件，告诉用户搞定了。
    

**每一轮都是一次"LLM 决策 + 可能的 ToolCall"**。LLM 决定下一步做什么，执行层去跑，跑完结果喂回给 LLM，如此循环。

### 6.2 Agent Loop 的再进化：回归原生，掌控一切

在开发过程中，我短暂地尝试过引入 **OpenAI Agents SDK** 来简化代码。它确实能把复杂的循环封装成一行 `Runner.run_streamed()`。

但很快，我遇到了新的瓶颈：**SDK 的封装太严了**。它严格校验消息格式，不允许在历史记录中插入"未定义工具"的调用记录。这直接阻碍了我实现 "Synthetic Tool Call"（隐式触发）的终极方案——因为我想让系统假装调用了一个 `execute_code` 工具，但我不希望这个工具出现在 LLM 的可选工具列表里（防止 LLM 显式调用）。

于是，我做了一个决定：**放弃 SDK，回归原生 OpenAI API，手动实现 Agent Loop。**

虽然代码量增加了，但我拿回了对系统的**绝对控制权**：

```python
# 截取自 backend/app/agent.py (Native Implementation)
while turn_count < MAX_TURNS:
    # 1. 调用 OpenAI API (流式)
    response_stream = await client.chat.completions.create(..., stream=True)
    
    # 2. 手动处理流式响应，累积文本和 ToolCall Chunks
    content, tool_calls = await self._process_stream(response_stream)
    
    # 3. 关键逻辑：检测 <execute> 标签
    if has_execute_block(content):
        # 4. 构造 Synthetic Tool Call
        # 这是一个不存在于 Tool Schema 里的工具，但我们可以强行构造出它的历史
        inject_synthetic_tool_call(messages, "execute_code", code)
        
        # 5. 执行代码并继续循环
        result = execute_code(code)
        messages.append({"role": "tool", "content": result})
        continue

```

### 6.3 关键机制：Synthetic Tool Call（合成调用链）

这是整个系统的"黑科技"。在 LLM 看来，它只是输出了文本。但在我的 Agent Loop 里，一旦检测到闭合的 `</execute>` 标签，系统会自动：

1.  **篡改历史**：修改 LLM 刚刚回复的那条 Message，给它加上一个 `tool_calls=[{name: 'execute_code'}]` 的属性。
    
2.  **伪造结果**：立即执行代码，并插入一条标准的 `role: 'tool'` 消息作为结果。
    

**这种"欺骗"带来了两个巨大的好处：**

1.  **符合 LLM 的直觉**：LLM 看到历史记录里自己"调用"了工具并得到了结果，它的认知逻辑是连贯的，下一轮对话它会自然地基于这个结果继续推理。
    
2.  **兼容性无敌**：这生成的历史记录完全符合 OpenAI 的 ChatML 格式标准。这意味着，虽然我的内部逻辑很魔改，但对外的接口依然是标准的。
    

这意味着：**Agent 在后端自动跑闭环，前端用户却能看到"它在思考、它在查书、它在写代码、它在纠错"的全过程。** 这就是我在开头提到的"有人味"的关键所在。

---

## 【重点】为什么用脚本生成和执行，而不是直接调用工具

### 7.1 为什么不是"直接调用工具/API"

传统的 Agent 设计（如 OpenAI Assistants API）通常是预定义好一堆工具函数，比如：

*   `read_excel(file_path)`
    
*   `calculate_sum(column_name)`
    
*   `draw_chart(data, type)`
    

**这就带来了一个"粒度"的两难困境：**

*   **粒度太粗**：一个工具做太多事，稍微有点定制需求（比如"计算前先过滤掉空值"）就傻眼了。
    
*   **粒度太细**：把每个原子操作都做成工具，那你得定义几百个工具。LLM 光是看工具列表就晕了，而且很容易选错。
    

### 7.2 脚本生成的优势：无限灵活性

我的方案是：**不要给 Agent 渔网，给它织网的技术。**

我让 Agent 生成 **Python 脚本**。

*   **无限灵活性**：Python 代码可以表达任意复杂的逻辑。条件判断、循环、数据清洗、异常处理，全都不在话下。
    
*   **组合能力**：一个脚本里可以同时调用 `pandas` 处理数据，调用 `matplotlib` 画图，再调用 `requests` 发送结果。以前需要调用 10 次工具才能做完的事，现在生成一段 50 行的代码就搞定了。
    
*   **可追溯性**：每个生成的脚本都会落盘保存到 `scripts/` 目录。
    
    *   `scripts/session_01_uuid.py`
        
    *   `scripts/session_02_uuid.py`
        

如果有问题，我可以打开文件看它到底写了啥。这比去翻 API 调用日志直观多了。

### 7.3 技术实现：从代码检测到结果回收

为了让脚本能安全、有效地运行，我做了很多底层工作。

#### Step 1：代码块检测

在 `agent.py` 中，我用正则提取 LLM 回复中的 `python ...`  块。

#### Step 2：skill\_helpers 注入（点睛之笔！）

脚本运行在隔离环境，怎么让它能找到 `skills/` 目录下的资源呢？ 我编写了一个 `skill_helpers` 模块，在每次执行代码前，**自动注入**到脚本头部：

```python
# 自动注入的代码
SKILLS_ROOT = "skills"
def skill_path(skill_name, *parts):
    return os.path.join(SKILLS_ROOT, skill_name, *parts)


```

这样，Agent 生成的代码就可以优雅地写：

```python
# Agent 生成的代码
script_path = skill_path("pptx", "scripts", "html2pptx.js")
subprocess.run(["node", script_path, ...])


```

它不需要知道绝对路径，只需要知道技能的名字，就能调用技能里的资源。

#### Step 3：子进程隔离执行

为了不把主服务搞挂，我使用 `asyncio.create_subprocess_exec` 启动子进程来跑这些脚本。

#### Step 4：JSON 结果解析

我约定 Agent 在脚本最后必须 `print` 一个 JSON 格式的结果：

```python
print(json.dumps({
    "status": "success",
    "result": "分析完成",
    "output_file_names": ["report.xlsx"]
}))


```

`agent.py` 会去 stdout 里抓取这个 JSON，解析出状态和生成的文件名。如果有生成文件，还会自动生成下载链接返回给前端。

---

## Skills + MCP：业务流与能力的完美联姻

讲完了系统的核心架构，接下来我们聊聊一个更高阶的话题：**如何让 Skills 和 MCP (Model Context Protocol) 深度结合**。

在我的架构中，Skills 和 MCP 并非割裂的存在，而是相辅相成的关系。如果说 **Skills 是 Agent 的"大脑回路"（SOP 和业务流程）**，那么 **MCP 就是 Agent 的"手脚"（原子能力）**。

### 8.1 为什么需要结合？

单纯的 MCP Tool 往往粒度很细。例如，我有一个 MCP Server 提供了以下原子工具：

*   `t2i_flux` (文生图)
    
*   `t2a_index` (文本转语音)
    
*   `v_merge` (视频合成)
    

如果直接把这些工具丢给 Agent，让它"做一个短视频"，它可能会不知所措：先做图还是先做音频？音频和图片怎么对应？如果做了20个分镜，那么需要调用20次文生图、20次文本转语音....LLM对于调用50多次tool是很难保障调用稳定的。

这就需要 **Skill** 出场了。Skill 的作用就是**把这些散落在 MCP 里的珍珠，串成一条项链**。

### 8.2 技术实现：在 Skill 中编排 MCP

我在 `backend/skills/default/social-media-video/SKILL.md` 中定义了一个典型的视频生成工作流。大家可以看到，SKILL.md 不仅写了文档，还直接给出了**调用 MCP 工具的代码范式**：

```markdown
# 截取自 SKILL.md
## Implementation Pattern

```python
# Step 1: Generate scripts
scripts = await call_tool('user_topic_prompts_tool', {'topic': 'AI News'})

# Step 2: Loop & Generate Assets
for script in scripts:
    # Call MCP tool for Image
    image = await call_tool('t2i_flux_krea', {'image_prompt': script})
    
    # Call MCP tool for Audio
    audio = await call_tool('t2a_index', {'script_segment': script})
    
    # Call MCP tool for Composition
    clip = await call_tool('picture_subtitle', {'image': image, 'audio': audio})

```

### 8.3 底层桥接：call\_tool 的魔法

Agent 生成的 Python 脚本中调用的 `call_tool`，实际上是我在 `backend/app/mcp_client.py` 中封装的一个**通用网关**。

它做了两件事：

1.  **路由分发**：根据工具名称，自动找到对应的 MCP Server（可能是本地的，也可能是远程 SSE/HTTP 服务）。
    
2.  **协议转换**：把 Python 的字典参数转换为 MCP 协议的标准 Request，并将 MCP 的返回结果（可能是复杂的 Content 对象列表）简化为脚本易于处理的 JSON 或 字符串。
    

```python
# 截取自 backend/app/mcp_client.py
async def call_tool(tool_name: str, args: dict = None) -> Any:
    # 1. 查找路由
    server_config = _TOOL_SERVER_MAP.get(tool_name)
    
    # 2. 发起真实 MCP 调用
    if server_config:
        return await _call_real_tool(tool_name, args, server_config)
    
    # ...

```

**这种设计的价值在于：**

*   **Skill 作者**只需要关心业务逻辑，像搭积木一样调用 `call_tool`。
    
*   **MCP 开发者**只需要关心原子功能的实现，提供标准的工具接口。
    
*   **Agent** 只需要读懂 Skill 说明书，就能像熟练工一样调度各种复杂的外部能力。
    

---

## 进阶心法：如何让 Agent 更聪明

系统架构讲完了，接下来分享两条在工程实践中总结出的核心"心法"，帮助你的 Agent 变得更稳定、更聪明。

### 9.1 Prompt 的信息架构：自顶向下与逻辑内聚

在 Prompt Engineering 中，**信息架构（Information Architecture）** 和 **逻辑内聚性** 对模型表现有着至关重要的影响。目前的 Prompt 容易出现"信息跳跃"的问题——虽然大模型的 Attention 机制能处理长文本，但如果逻辑线索断裂，推理时就容易发生"指令漂移"。

优化的核心是采用\*\*"自顶向下"\*\*的逻辑顺序：

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/3BMqYybQ4yGkEqwZ/img/c5a56fd1-aaa4-4285-8f15-3c39add97fff.png)

1.  **身份定义**（我是谁）
    
2.  **能力/工具声明**（我能做什么）
    
3.  **运行环境与约束**（我在什么环境下工作，有哪些边界）
    
4.  **具体执行规范**（工具调用的语法、代码的具体写法）
    
5.  **标准作业程序 (SOP)**（遇到任务时的思考和执行流程）
    

同时，我极力推崇\*\*"单一段落、单一主题"\*\*的原则。以文件路径为例，如果我在 Prompt 的开头提了一句"工作目录在 /scripts"，又在结尾提了一句"使用相对路径"，模型很容易产生模糊地带。

**去重和归纳**的好处是显而易见的：

*   **降低 Token 噪音**：节省上下文空间。
    
*   **消除冲突**：避免前后矛盾。
    
*   **强化认知模型**：将所有 `working_directory` 和 `Path Helpers` 规则物理上聚合在一起，能强迫模型在处理路径问题时，注意力高度集中。
    

### 9.2 Tool Call 的设计哲学：极简主义

在设计 Tool Definition 时，我遵循两个原则：

1.  **Description 要简短且不重复**：
    
    *   不要在 Tool Description 里把 System Prompt 里写过的"工具用途"再抄一遍。
        
    *   Tool Description 是给模型做"路由选择"用的，只要说清楚"什么情况下用我"即可。冗余的描述只会稀释模型的注意力。
        
2.  **入参和出参都要短**：
    
    *   **入参**：如果无法限制入参的长度，那就需要一些机制来绕过toolcall传参，比如我的 `execute_code` 改成了无参调用（代码在正文），彻底解决了长代码传参的噩梦。
        
    *   **出参**：工具的返回值（Tool Output）最终会变成 History 的一部分。如果工具返回了几万字的 JSON，下一次对话的 Context Window 瞬间就爆了。所以，我的工具只返回关键信息（如"成功"、"文件路径"、"简要摘要"），详细数据一律落盘，让 Agent 自己去读文件。
        

---

## 结语与未来展望

手搓这个 Skills Client 的过程，让我对 Agent 的本质有了更深的理解。

我们正在从"Chatbot"时代迈向"Agentic Workflow"时代。**LLM 不再只是一个只会说话的嘴巴，它正在长出"手"（代码执行）和"眼睛"（工具调用），并学会了使用"工具书"（Skills）。**

未来，我会尝试：

1.  **Skill 自动生成**：让 Agent 自己读代码库，自动生成 `SKILL.md`。
    
2.  **更强的沙盒**：目前是在宿主机跑脚本，未来可以上 Docker 容器，让执行环境更安全、依赖管理更方便。