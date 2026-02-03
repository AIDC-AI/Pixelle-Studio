# 模型故障转移配置更新说明

## 📋 更新内容

### 新增功能：通过环境变量配置模型 fallback 链

现在可以通过环境变量 `MODEL_FALLBACKS` 自定义模型故障转移顺序，无需修改代码或配置文件。

---

## 🎯 使用方法

### 方式 1: 环境变量配置 (推荐)

```bash
# 设置默认模型
export OPENAI_MODEL="gpt-4o"

# 设置 fallback 链 (逗号分隔,无空格)
export MODEL_FALLBACKS="gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo"

# 启动服务
cd backend
python -m uvicorn app.main:app --reload
```

**效果**:
```
模型调用链: gpt-4o → gpt-4o-mini → gpt-4-turbo → gpt-3.5-turbo
```

---

## 📝 配置示例

### 示例 1: 标准配置 (默认)

```bash
export OPENAI_MODEL="gpt-4o"
export MODEL_FALLBACKS="gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo"
```

**调用链**: gpt-4o → gpt-4o-mini → gpt-4-turbo → gpt-3.5-turbo

**适用场景**: 通用场景，平衡性能和成本

---

### 示例 2: 成本优化

```bash
export OPENAI_MODEL="gpt-4o-mini"
export MODEL_FALLBACKS="gpt-3.5-turbo"
```

**调用链**: gpt-4o-mini → gpt-3.5-turbo

**适用场景**: 降低成本，适合简单任务

---

### 示例 3: 高性能优先

```bash
export OPENAI_MODEL="gpt-4o"
export MODEL_FALLBACKS="gpt-4-turbo"
```

**调用链**: gpt-4o → gpt-4-turbo

**适用场景**: 需要高质量输出，成本不敏感

---

### 示例 4: 单一模型 (无 fallback)

```bash
export OPENAI_MODEL="gpt-4o"
export ENABLE_MODEL_FAILOVER=false
```

**调用链**: gpt-4o (失败直接报错)

**适用场景**: 测试环境，验证单一模型稳定性

---

## 🔧 配置优先级

系统按以下优先级加载配置：

```
1️⃣ 环境变量 MODEL_FALLBACKS (最高优先级)
   ↓ (如果未设置)
2️⃣ 配置文件 app/config/model_fallbacks.json
   ↓ (如果不存在)
3️⃣ 代码默认值 (app/config.py)
```

**日志输出**:
```
[Config] Using model fallbacks from environment: ['gpt-4o-mini', 'gpt-3.5-turbo']
[Config] Using model fallbacks from config file: [...]
[Config] Using default model fallbacks for gpt-4o: [...]
```

---

## ✅ 验证配置

### 方法 1: 运行测试脚本

```bash
cd backend
python3 test_model_config.py
```

**输出示例**:
```
============================================================
测试模型配置
============================================================

【环境变量】
OPENAI_MODEL = gpt-4o
MODEL_FALLBACKS = gpt-4o-mini,gpt-3.5-turbo

【加载的配置】
✓ 默认模型: gpt-4o
✓ 模型 fallback 链: ['gpt-4o-mini', 'gpt-3.5-turbo']
✓ 完整模型调用链: gpt-4o → gpt-4o-mini → gpt-3.5-turbo

【配置来源】
✓ 使用环境变量 MODEL_FALLBACKS

✅ 配置测试完成
```

### 方法 2: 查看启动日志

```bash
cd backend
python -m uvicorn app.main:app --reload
```

日志中会显示:
```
[Config] Using model fallbacks from environment: ['gpt-4o-mini', 'gpt-3.5-turbo']
```

---

## 📚 相关文档

- **完整配置示例**: [ENV_CONFIG_EXAMPLES.md](ENV_CONFIG_EXAMPLES.md)
- **快速入门**: [dev_docs/QUICK_START_STABILITY.md](dev_docs/QUICK_START_STABILITY.md)
- **详细文档**: [dev_docs/STABILITY_OPTIMIZATION.md](dev_docs/STABILITY_OPTIMIZATION.md)

---

## 🔍 技术细节

### 代码变更

**文件**: `backend/app/config.py`

**修改位置**: `_load_model_fallbacks()` 方法

**关键逻辑**:
```python
def _load_model_fallbacks(self) -> List[str]:
    # 1. 优先从环境变量读取
    env_fallbacks = os.getenv("MODEL_FALLBACKS")
    if env_fallbacks:
        models = [m.strip() for m in env_fallbacks.split(",") if m.strip()]
        if models:
            return models
    
    # 2. 从配置文件读取
    # ...
    
    # 3. 使用代码默认值
    # ...
```

---

## 🎨 使用场景对比

| 场景 | 环境变量配置 | 模型链 | 特点 |
|------|-------------|--------|------|
| **生产环境** | `MODEL_FALLBACKS="gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo"` | 4层保障 | 高可用 |
| **开发环境** | `MODEL_FALLBACKS="gpt-3.5-turbo"` | 2层 | 快速+便宜 |
| **测试环境** | `ENABLE_MODEL_FAILOVER=false` | 1层 | 验证单一模型 |
| **成本优化** | `MODEL_FALLBACKS="gpt-3.5-turbo"` | 2层 | 最低成本 |
| **高质量** | `MODEL_FALLBACKS="gpt-4-turbo"` | 2层 | 性能优先 |

---

## 💡 最佳实践

### ✅ 推荐

1. **生产环境**: 设置至少 2-3 个 fallback 模型
   ```bash
   export MODEL_FALLBACKS="gpt-4o-mini,gpt-4-turbo,gpt-3.5-turbo"
   ```

2. **使用环境变量**: 比配置文件更灵活
   ```bash
   # 在 .env 文件或启动脚本中设置
   export MODEL_FALLBACKS="..."
   ```

3. **定期检查日志**: 确认配置是否生效
   ```bash
   grep "Using model fallbacks" logs/app.log
   ```

### ❌ 不推荐

1. **不设置任何 fallback**: 降低系统可用性
2. **fallback 太多**: 增加失败重试时间
3. **混用不兼容的模型**: 如 OpenAI + Claude (需要不同的 API 格式)

---

## 🐛 常见问题

### Q1: 设置了环境变量但没生效?

**检查步骤**:
```bash
# 1. 确认环境变量已设置
echo $MODEL_FALLBACKS

# 2. 重启服务
pkill -f uvicorn
python -m uvicorn app.main:app --reload

# 3. 查看日志
grep "Using model fallbacks" logs/app.log
```

### Q2: 格式错误会怎样?

如果格式错误（如有多余空格），系统会自动过滤。

**示例**:
```bash
# 带空格 (会自动去除)
export MODEL_FALLBACKS="gpt-4o-mini, gpt-3.5-turbo"
# 结果: ['gpt-4o-mini', 'gpt-3.5-turbo']
```

### Q3: 可以设置空值吗?

```bash
export MODEL_FALLBACKS=""
```
空值会被忽略，系统会使用配置文件或默认值。

### Q4: 如何禁用所有 fallback?

```bash
export ENABLE_MODEL_FAILOVER=false
```

---

## 📊 测试结果

运行 `python3 test_model_config.py` 的测试结果:

```
✅ 环境变量优先级测试 - 通过
✅ 配置文件回退测试 - 通过  
✅ 默认值回退测试 - 通过
✅ 自定义模型链测试 - 通过
✅ 空值处理测试 - 通过
```

---

## 📅 更新日期

- **版本**: 2.0.1
- **日期**: 2026-02-02
- **作者**: Cursor AI Assistant

---

## 🔗 相关链接

- 主文档: [STABILITY_OPTIMIZATION.md](dev_docs/STABILITY_OPTIMIZATION.md)
- 配置示例: [ENV_CONFIG_EXAMPLES.md](ENV_CONFIG_EXAMPLES.md)
- 快速入门: [QUICK_START_STABILITY.md](dev_docs/QUICK_START_STABILITY.md)

