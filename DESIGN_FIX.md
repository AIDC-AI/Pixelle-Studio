# 设计修复：支持标准 Function Calling

## 问题根源（你说得对！）

### 之前的奇怪设计

**工具定义**：
```python
@function_tool
async def execute_code(ctx: RunContextWrapper[AgentContext]) -> str:
    # ❌ 不接受任何参数！
    # ❌ 从队列中取代码
    code = context.pending_code_queue.pop()
```

**工作流程**：
```
1. 模型返回文本：包含 <execute lang="python">code</execute>
2. 系统解析文本，提取代码，放入队列
3. 模型调用 execute_code() 工具（无参数）
4. 系统从队列取出代码执行
```

### 问题分析

1. **不符合标准 Function Calling**
   - 标准方式：`execute_code(code="print('hello')")`
   - 之前方式：先在文本中写代码，再调用无参数工具

2. **强制要求先返回文本**
   - 模型必须先返回包含 `<execute>` 的文本
   - 然后才能调用工具
   - 如果模型直接调用工具，队列为空，就会失败

3. **不兼容直接调用工具的模型**
   - GPT-5、GPT-4o 等可能直接调用工具
   - 这些模型不会先返回文本
   - 导致 `IndexError: list index out of range`

## 修复方案

### 修复 1: execute_code 工具现在接受参数 ✅

**文件**: `backend/app/tools.py`

**修复后**：
```python
@function_tool
async def execute_code(ctx: RunContextWrapper[AgentContext], code: str = "") -> str:
    """
    Execute Python code to generate files and produce results.
    
    Two ways to use this tool:
    
    **Method 1 (Direct)**: Pass code directly as parameter
    execute_code(code="import json\\nprint(json.dumps({'status': 'success'}))")
    
    **Method 2 (Legacy)**: Write code in <execute> tags first, then call with no parameters
    """
    # 优先使用参数，然后再尝试队列（向后兼容）
    if code and code.strip():
        code_to_execute = code.strip()  # 使用参数
    elif context.pending_code_queue:
        code_to_execute = context.pending_code_queue.pop()  # 使用队列
    else:
        return "No Code Found"  # 两者都没有
```

**优势**：
- ✅ 支持标准 function calling（直接传递参数）
- ✅ 向后兼容（仍支持队列方式）
- ✅ 不会再出现 `IndexError`

### 修复 2: 移除强制设置参数的代码 ✅

**文件**: `backend/app/agent.py`

**修复前**：
```python
if tool_name == "execute_code":
    if agent_context.pending_code_queue:
        tool_args = {"code": agent_context.pending_code_queue[-1]}  # ❌ 强制覆盖
    else:
        logger.warning("queue is empty")
```

**修复后**：
```python
# Note: execute_code 工具现在可以接受 code 参数
# 如果模型没有传递参数，工具会自动从队列获取
# 不需要在这里强制设置参数
```

**优势**：
- ✅ 让工具自己决定代码来源
- ✅ 不干扰模型传递的参数
- ✅ 更清晰的职责分离

### 修复 3: 更新 System Prompt ✅

**文件**: `backend/app/agent.py`

**修复后**：
```
**Option 1: Direct Method (Recommended)**
Call execute_code() with code as parameter:
execute_code(code="...")

**Option 2: Two-Step Method (Legacy)**
Write code in <execute> tags, then call execute_code()
```

**优势**：
- ✅ 明确告诉模型可以直接传递参数
- ✅ 仍然保留旧方式作为备选
- ✅ 不再强制要求"MUST FOLLOW EXACTLY"

## 支持的使用方式

### 方式 1: 直接传递代码（推荐）

**模型行为**：
```python
# 模型直接调用工具，传递代码
execute_code(code="import json\nprint(json.dumps({'status': 'success'}))")
```

**系统处理**：
```python
# 工具收到参数，直接执行
code_to_execute = code  # 使用参数
```

✅ **适合**: GPT-5, GPT-4o 等直接调用工具的模型

### 方式 2: 两步流程（向后兼容）

**模型行为**：
```
我会生成文件：

<execute lang="python">
import json
print(json.dumps({"status": "success"}))
</execute>
```
然后调用: `execute_code()`

**系统处理**：
```python
# 1. 从文本中提取代码，放入队列
agent_context.pending_code_queue.append(extracted_code)

# 2. 工具检测到没有参数，使用队列
code_to_execute = context.pending_code_queue.pop()
```

✅ **适合**: Claude 等喜欢先解释再行动的模型

## 测试验证

### 测试 1: 直接传递代码

```python
# 模型调用
execute_code(code="print('hello')")

# 预期结果
✅ 执行成功，输出 "hello"
```

### 测试 2: 使用队列

```
<execute lang="python">
print('hello')
</execute>
```
调用 `execute_code()`

```python
# 预期结果
✅ 从队列取代码，执行成功
```

### 测试 3: 两者都没有

```python
# 模型调用
execute_code()  # 无参数，队列也为空

# 预期结果
✅ 返回 "No Code Found" 错误消息
❌ 不会崩溃
```

## 如何验证修复

### 1. 重启后端服务

```bash
cd /Users/shali.yx/Desktop/code/mcp-workflow/backend
./start_server.sh
```

### 2. 测试直接调用（gpt-5.1 模型）

在前端发送：
```
生成一个 HTML 文件
```

**预期行为**：
- ✅ 模型可以直接调用 `execute_code(code="...")`
- ✅ 不会报 `IndexError`
- ✅ 代码会被执行
- ✅ 文件会被生成

### 3. 观察日志

查找以下日志：
```
[Tool] execute_code called with code parameter
[Tool] Executing code from parameter
```

或者：
```
[Tool] execute_code using code from queue
[Tool] Executing code from queue
```

### 4. 验证向后兼容性

如果切换回 Claude Sonnet 4：
```bash
# 编辑 .env
OPENAI_MODEL=us.anthropic.claude-sonnet-4-20250514-v1:0
```

- ✅ Claude 仍然可以使用旧方式（`<execute>` 标签）
- ✅ 系统会从队列获取代码
- ✅ 一切正常工作

## 对比：修复前 vs 修复后

### 修复前

| 模型行为 | 系统响应 | 结果 |
|---------|---------|------|
| 直接调用 `execute_code()` | `IndexError: list index out of range` | ❌ 崩溃 |
| 先返回 `<execute>`，再调用 | 从队列取代码执行 | ✅ 成功 |

### 修复后

| 模型行为 | 系统响应 | 结果 |
|---------|---------|------|
| 直接调用 `execute_code(code="...")` | 使用参数执行 | ✅ 成功 |
| 直接调用 `execute_code()` | 返回 "No Code Found" | ✅ 不崩溃 |
| 先返回 `<execute>`，再调用 | 从队列取代码执行 | ✅ 成功 |

## 为什么之前会这样设计？

可能的原因：

1. **为 Claude 优化**
   - Claude 喜欢先解释再行动
   - `<execute>` 标签让代码在文本中可见
   - 用户可以看到代码内容

2. **避免参数过长**
   - 代码可能很长
   - 放在文本中更易读
   - Function call 参数有长度限制

3. **历史遗留**
   - 可能是从早期版本演化来的
   - 当时没有考虑到直接调用工具的模型

## 更好的长期方案

### 选项 A: 完全移除队列机制（推荐）

```python
@function_tool
async def execute_code(ctx: RunContextWrapper[AgentContext], code: str) -> str:
    """Execute Python code"""
    # 只接受参数，不使用队列
    # 代码更简单，职责更清晰
```

**优势**：
- ✅ 符合标准 function calling
- ✅ 代码更简单
- ✅ 职责更清晰

**劣势**：
- ❌ 不向后兼容
- ❌ 需要更新所有 prompt
- ❌ 长代码可能超过参数限制

### 选项 B: 保持当前设计（已实施）

```python
@function_tool
async def execute_code(ctx: RunContextWrapper[AgentContext], code: str = "") -> str:
    """Execute Python code - supports both direct and queue methods"""
    # 优先参数，然后队列
```

**优势**：
- ✅ 向后兼容
- ✅ 支持两种方式
- ✅ 适应不同模型

**劣势**：
- ⚠️ 代码稍复杂
- ⚠️ 需要维护两套逻辑

## 总结

### ✅ 你是对的！

1. ✅ **直接调用工具是合理的** - 这是标准 function calling 行为
2. ✅ **之前的设计有问题** - 强制要求先返回文本不合理
3. ✅ **应该支持参数传递** - 工具应该接受 `code` 参数

### ✅ 已修复的问题

1. ✅ `execute_code` 工具现在接受 `code` 参数
2. ✅ 移除了强制设置参数的代码
3. ✅ 更新了 system prompt，告诉模型可以直接传递参数
4. ✅ 保持向后兼容，仍支持队列方式

### 🎯 现在的行为

- ✅ GPT-5/GPT-4o: 可以直接调用 `execute_code(code="...")`
- ✅ Claude: 仍可以使用 `<execute>` 标签方式
- ✅ 任何模型: 都不会因为队列为空而崩溃
- ✅ 代码更健壮，支持多种使用方式

### 📝 建议

1. **立即重启后端**，应用修复
2. **测试 gpt-5.1 模型**，验证直接调用是否工作
3. **观察日志**，确认代码来源（parameter vs queue）
4. **如果一切正常**，考虑逐步移除队列机制，简化代码


