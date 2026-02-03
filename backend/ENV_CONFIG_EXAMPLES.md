# 环境变量配置示例

## 模型故障转移配置

### 1. 通过环境变量配置 (推荐)

最灵活的方式，可以根据需求快速调整。

#### 示例 1: 标准 GPT-4 系列 fallback

```bash
export OPENAI_MODEL="gpt-4o"
export MODEL_FALLBACKS="gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo"
```

**效果**: 
- 主模型: `gpt-4o`
- 备用链: `gpt-4o-mini` → `gpt-4-turbo` → `gpt-3.5-turbo`

#### 示例 2: 成本优化配置

```bash
export OPENAI_MODEL="gpt-4o-mini"
export MODEL_FALLBACKS="gpt-3.5-turbo"
```

**效果**: 
- 主模型: `gpt-4o-mini` (更便宜)
- 备用: `gpt-3.5-turbo` (最便宜)

#### 示例 3: 只使用单一模型 (无 fallback)

```bash
export OPENAI_MODEL="gpt-4o"
export ENABLE_MODEL_FAILOVER=false
```

**效果**: 
- 只使用 `gpt-4o`，失败时直接报错，不尝试其他模型

#### 示例 4: 多模型混合

```bash
export OPENAI_MODEL="gpt-4-turbo"
export MODEL_FALLBACKS="gpt-4o,gpt-4o-mini,gpt-3.5-turbo"
```

**效果**: 
- 主模型: `gpt-4-turbo`
- 备用链: `gpt-4o` → `gpt-4o-mini` → `gpt-3.5-turbo`

#### 示例 5: Claude 系列

```bash
export OPENAI_MODEL="claude-3-5-sonnet"
export MODEL_FALLBACKS="claude-3-sonnet,claude-3-opus"
```

**效果**: 
- 主模型: `claude-3-5-sonnet`
- 备用链: `claude-3-sonnet` → `claude-3-opus`

---

### 2. 配置文件方式

编辑 `backend/app/config/model_fallbacks.json`:

```json
{
  "description": "模型故障转移配置",
  "fallbacks": [
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo"
  ]
}
```

**优先级**: 环境变量 > 配置文件 > 代码默认值

---

## 完整环境变量参考

```bash
# ===== 模型配置 =====
# 默认使用的主模型
export OPENAI_MODEL="gpt-4o"

# 模型故障转移链 (逗号分隔,无空格)
export MODEL_FALLBACKS="gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo"

# ===== 认证配置 =====
# 主 API Key
export OPENAI_API_KEY="sk-your-primary-key"

# 备用 API Key (可选)
export OPENAI_API_KEY_BACKUP="sk-your-backup-key"

# 自定义 API 端点 (可选)
# export OPENAI_BASE_URL="https://api.openai.com/v1"

# ===== LLM 配置 =====
# LLM 超时时间 (秒)
export LLM_TIMEOUT=300

# LLM 最大输出 tokens
export LLM_MAX_TOKENS=16384

# ===== 故障转移开关 =====
# 启用认证故障转移
export ENABLE_AUTH_FAILOVER=true

# 启用模型故障转移
export ENABLE_MODEL_FAILOVER=true

# 启用 Thinking Level 降级
export ENABLE_THINKING_FAILOVER=true

# 默认 Thinking Level (high, medium, low, off)
export DEFAULT_THINKING_LEVEL=medium

# ===== 上下文管理 =====
# 启用自动上下文压缩
export CONTEXT_COMPACTION_ENABLED=true

# 压缩时保留最近几条消息
export CONTEXT_KEEP_RECENT=10

# 最少消息数才考虑压缩
export CONTEXT_MIN_MESSAGES_BEFORE_COMPACT=15
```

---

## 配置优先级

```
1. 环境变量 (最高优先级)
   ├─ OPENAI_MODEL
   ├─ MODEL_FALLBACKS
   ├─ OPENAI_API_KEY
   └─ 其他开关配置
   
2. 配置文件
   └─ app/config/model_fallbacks.json
   
3. 代码默认值 (兜底)
   └─ app/config.py 中的 default_fallbacks
```

---

## 使用场景推荐

### 场景 1: 生产环境 - 高可用

```bash
export OPENAI_MODEL="gpt-4o"
export MODEL_FALLBACKS="gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo"
export OPENAI_API_KEY="sk-primary"
export OPENAI_API_KEY_BACKUP="sk-backup"
export ENABLE_AUTH_FAILOVER=true
export ENABLE_MODEL_FAILOVER=true
```

**优点**: 最大化可用性，多层保障

### 场景 2: 开发环境 - 快速调试

```bash
export OPENAI_MODEL="gpt-3.5-turbo"
export ENABLE_MODEL_FAILOVER=false
export CONTEXT_COMPACTION_ENABLED=false
```

**优点**: 响应快速，成本低，日志简洁

### 场景 3: 成本优化 - 降低费用

```bash
export OPENAI_MODEL="gpt-4o-mini"
export MODEL_FALLBACKS="gpt-3.5-turbo"
export CONTEXT_KEEP_RECENT=5  # 减少上下文
```

**优点**: 降低 API 调用成本

### 场景 4: 测试环境 - 稳定性测试

```bash
export OPENAI_MODEL="gpt-4o"
export MODEL_FALLBACKS=""  # 空字符串 = 无 fallback
export ENABLE_MODEL_FAILOVER=false
export ENABLE_AUTH_FAILOVER=false
```

**优点**: 测试单一配置的稳定性

---

## 验证配置

启动服务后，查看日志确认配置是否生效:

```bash
# 启动服务
cd backend
python -m uvicorn app.main:app --reload

# 查看日志输出
# 应该能看到类似：
# [Config] Using model fallbacks from environment: ['gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo']
```

或者运行测试:

```bash
cd backend
python3 test_basic_features.py
```

---

## 常见问题

### Q1: MODEL_FALLBACKS 格式错误会怎样?

**A**: 如果格式错误或为空，系统会自动使用配置文件或代码默认值。

### Q2: 可以混合使用不同厂商的模型吗?

**A**: 理论上可以，但需要确保所有模型都使用兼容的 API 格式。建议同厂商模型混用。

### Q3: 如何完全禁用故障转移?

**A**: 
```bash
export ENABLE_AUTH_FAILOVER=false
export ENABLE_MODEL_FAILOVER=false
export ENABLE_THINKING_FAILOVER=false
```

### Q4: 环境变量和配置文件哪个优先?

**A**: 环境变量优先级最高，会覆盖配置文件和代码默认值。

---

**更新日期**: 2026-02-02  
**版本**: 2.0.0

