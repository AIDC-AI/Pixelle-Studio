# Tool Calling 问题修复说明

## 问题描述

Agent 在生成 HTML 文件等任务时，不会主动调用 `execute_code()` tool 来执行代码，导致：
- 只显示代码，不生成实际文件
- 用户无法下载生成的文件
- 任务看起来"完成"了，但实际上什么都没做

## 问题根源

### 1. 模型兼容性问题

当前使用的模型：
```
us.anthropic.claude-sonnet-4-20250514-v1:0
```

**核心问题**：
- **OpenAI Agents SDK** 是为 OpenAI 的 GPT 模型设计的
- **Claude Sonnet 4** 虽然支持 OpenAI 兼容的 API，但在 **tool calling 行为** 上存在差异：
  - **GPT 模型**：看到任务需要执行代码时，会主动调用工具
  - **Claude 模型**：倾向于先解释、展示代码，但不会主动执行（除非有非常明确的指示）

### 2. System Prompt 不够明确

之前的 prompt 说"Then call: execute_code()"，但对于 Claude 模型来说：
- 这个指示不够强烈
- Claude 可能理解为"可以调用"而不是"必须调用"
- Claude 可能认为写完代码就算完成任务了

## 已实施的修复

### 修复 1: 增强 System Prompt（✅ 已完成）

**文件**: `backend/app/agent.py`

**改进点**：
1. ✅ 添加了 `**CRITICAL WORKFLOW - MUST FOLLOW EXACTLY**` 标题
2. ✅ 使用 `⚠️` 符号和粗体强调必须调用工具
3. ✅ 明确说明"Just writing the code block is NOT enough"
4. ✅ 在 decision_flow 中添加详细的"WRONG vs CORRECT"示例
5. ✅ 强调用户需要"ACTUAL FILES"而不是代码

**关键改动**：
```python
<code_execution_rules>
**CRITICAL WORKFLOW - MUST FOLLOW EXACTLY**:

When you need to execute Python code, you MUST do BOTH steps:

**Step 1**: Write code in `<execute lang="python">...</execute>` tags in your response
**Step 2**: IMMEDIATELY call the `execute_code()` tool (no parameters needed)

⚠️ **YOU MUST ACTUALLY CALL THE TOOL** - Just writing the code block is NOT enough!
```

### 修复 2: 强化工具描述（✅ 已完成）

**文件**: `backend/app/tools.py`

**改进点**：
1. ✅ 在 `execute_code` 工具的 docstring 开头添加 `⚠️ CRITICAL TOOL`
2. ✅ 使用 `MANDATORY WORKFLOW` 替代 `WORKFLOW`
3. ✅ 明确警告"Just writing the code block without calling this tool does NOTHING"

## 如何验证修复

### 1. 重启后端服务

```bash
# Terminal 1（后端）
cd /Users/shali.yx/Desktop/code/mcp-workflow/backend
./start_server.sh
```

等待看到：
```
INFO: Application startup complete.
INFO:root:DEFAULT_MODEL: us.anthropic.claude-sonnet-4-20250514-v1:0
```

### 2. 测试场景

在前端发送以下消息：
```
请帮我生成一个简单的HTML页面，包含一个标题"Hello World"和一段文字"这是我的第一个页面"。请执行代码生成文件。
```

### 3. 预期行为

✅ **正确行为**：
1. Agent 回复说明任务
2. 显示 `<execute lang="python">` 代码块
3. **立即看到** "Tool Call: execute_code" 消息
4. 看到执行结果和输出文件
5. 可以点击"预览"或"下载"按钮

❌ **错误行为**（修复前）：
1. Agent 回复说明任务
2. 显示代码块
3. 说"代码已经准备好了"就结束了
4. **没有** "Tool Call: execute_code" 消息
5. **没有** 生成文件

## 如果问题仍然存在

如果修复后问题仍然存在，可以尝试以下方案：

### 方案 A: 切换到 GPT 模型（推荐）

编辑 `backend/.env`：
```bash
# 使用 GPT-4o（推荐）
OPENAI_MODEL=gpt-4o

# 或使用 GPT-4
OPENAI_MODEL=gpt-4
```

**优势**：
- OpenAI Agents SDK 与 GPT 模型配合最好
- Tool calling 行为更可预测
- 无需担心兼容性问题

### 方案 B: 简化工作流程（备选）

如果必须使用 Claude 模型，可以考虑：
1. 移除 `<execute>` 代码块模式
2. 让 `execute_code` 工具接受 `code` 参数
3. Agent 直接调用工具并传递代码

**需要修改**：
- `tools.py` 中的 `execute_code` 函数签名
- `agent.py` 中的 system prompt
- 移除代码提取逻辑

### 方案 C: 增加工具调用强制机制

在 agent 循环中检测：
- 如果检测到 `<execute>` 代码块但没有调用 `execute_code`
- 自动触发工具调用

**需要修改**：
- `agent.py` 中的事件处理逻辑
- 添加代码块检测和自动触发机制

## 调试信息

### 查看后端日志

```bash
# 查看 agent.py 的日志
tail -f /Users/shali.yx/.cursor/projects/Users-shali-yx-Desktop-code-mcp-workflow/terminals/1.txt
```

关键日志：
- `[Tool] Loading skill:` - 加载技能
- `[Tool] Executing LAST code from queue` - 执行代码
- `Tool call: execute_code` - 工具调用
- `Execution Result` - 执行结果

### 前端 Console 日志

打开浏览器开发者工具，查看：
```
[WebSocket] Received message: {"type":"tool_call","name":"execute_code",...}
```

如果没有看到这条消息，说明 agent 没有调用工具。

## 技术细节

### OpenAI Agents SDK 工作原理

```python
# 1. 创建 Agent
agent = Agent(
    name="SkillAgent",
    instructions=system_prompt,    # System prompt
    tools=SKILL_TOOLS,              # 可用工具列表
    model=DEFAULT_MODEL,            # 使用的模型
)

# 2. 运行 Agent（流式）
result = Runner.run_streamed(
    agent,
    input=input_messages,           # 用户消息
    context=agent_context,          # 上下文（传递给工具）
    max_turns=max_tool_calls,       # 最大轮次
)

# 3. 处理事件流
async for event in result.stream_events():
    if isinstance(event, ToolCallItem):
        # Agent 决定调用工具
        tool_name = event.raw_item.name
        # ...
```

**关键点**：
- Agent 根据 **system prompt** 和 **tool descriptions** 决定是否调用工具
- Model 的 tool calling 能力直接影响行为
- GPT 模型在这方面表现更好

### Claude vs GPT 在 Tool Calling 上的差异

| 特性 | GPT-4 / GPT-4o | Claude Sonnet 4 |
|------|----------------|-----------------|
| Tool Calling 支持 | ✅ 原生支持 | ✅ 兼容但不完全一致 |
| 主动性 | 更主动调用工具 | 更保守，倾向于解释 |
| System Prompt 敏感度 | 中等 | 需要非常明确的指示 |
| 推荐用于 Agents SDK | ✅ 是 | ⚠️ 需要额外调整 |

## 总结

1. ✅ **已实施修复**：增强 system prompt 和工具描述，让 Claude 模型更明确地知道必须调用工具
2. 🔄 **需要重启**：修改后需要重启后端服务
3. 🧪 **需要测试**：用生成 HTML 文件的任务验证修复效果
4. 🔧 **备选方案**：如果问题仍存在，建议切换到 GPT-4o 模型

## 联系与反馈

如果修复后仍有问题，请提供：
1. 后端日志（Terminal 1 的输出）
2. 前端 Console 日志
3. 具体的测试消息和预期行为

这将帮助进一步诊断问题。




