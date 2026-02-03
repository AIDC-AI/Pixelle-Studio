# 网络连接问题排查指南

## 🔴 错误症状

```
httpcore.ConnectTimeout
start_tls.failed exception=ConnectTimeout(TimeoutError())
```

连接超时发生在 TLS 握手阶段，通常是网络无法访问 OpenAI API。

---

## 🔧 解决方案

### 方案 1: 配置代理 (推荐 - 国内用户)

在 `.env` 文件中添加代理配置:

```bash
# HTTP/HTTPS 代理 (支持多种格式)
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

# 或使用 socks5 代理
# HTTP_PROXY=socks5://127.0.0.1:7890
# HTTPS_PROXY=socks5://127.0.0.1:7890

# 或使用认证代理
# HTTP_PROXY=http://username:password@proxy.example.com:8080
# HTTPS_PROXY=http://username:password@proxy.example.com:8080
```

**常见代理端口**:
- Clash: `7890`
- V2Ray: `10809` 或 `1080`
- Shadowsocks: `1080`

### 方案 2: 使用国内可访问的 API 端点

如果使用兼容 OpenAI API 的服务 (如阿里云、智谱等):

```bash
# .env 文件
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://your-proxy-endpoint.com/v1

# 例如使用 OpenAI 代理服务
# OPENAI_BASE_URL=https://api.openai-proxy.com/v1
```

### 方案 3: 增加超时时间

在 `.env` 文件中:

```bash
# 默认 300 秒，可以增加到 600 秒
LLM_TIMEOUT=600
```

### 方案 4: 使用系统代理

如果已经配置了系统代理，可以在终端中设置:

```bash
# macOS/Linux
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export ALL_PROXY=socks5://127.0.0.1:7890

# 然后运行服务
cd backend
python -m uvicorn app.main:app --reload
```

---

## 🧪 测试网络连接

### 测试 1: 检查代理是否工作

```bash
# 使用 curl 测试
curl -x http://127.0.0.1:7890 https://api.openai.com/v1/models

# 或者
curl --proxy socks5://127.0.0.1:7890 https://api.openai.com/v1/models
```

### 测试 2: 检查 DNS 解析

```bash
# 检查是否能解析 OpenAI 域名
nslookup api.openai.com

# 或
dig api.openai.com
```

### 测试 3: 使用 Python 测试连接

创建测试脚本 `test_connection.py`:

```python
import asyncio
import os
from openai import AsyncOpenAI
import httpx

async def test_connection():
    """测试 OpenAI API 连接"""
    
    # 配置代理
    proxy = os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")
    
    if proxy:
        print(f"✅ 使用代理: {proxy}")
        http_client = httpx.AsyncClient(proxies={
            "http://": proxy,
            "https://": proxy,
        })
    else:
        print("⚠️  未配置代理")
        http_client = None
    
    try:
        # 创建客户端
        client = AsyncOpenAI(
            timeout=60.0,
            http_client=http_client
        )
        
        print("🔄 测试连接到 OpenAI API...")
        
        # 列出模型 (最简单的 API 调用)
        models = await client.models.list()
        
        print(f"✅ 连接成功! 可用模型数量: {len(models.data)}")
        print(f"   示例模型: {models.data[0].id if models.data else 'N/A'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}")
        print(f"   错误信息: {e}")
        return False
    
    finally:
        if http_client:
            await http_client.aclose()

if __name__ == "__main__":
    asyncio.run(test_connection())
```

运行测试:

```bash
cd backend
python test_connection.py
```

---

## 📋 完整的 .env 配置示例

```bash
# ===================================
# OpenAI API 配置
# ===================================

# API Key (必填)
OPENAI_API_KEY=sk-your-api-key-here

# API 端点 (可选，默认为 OpenAI 官方)
# OPENAI_BASE_URL=https://api.openai.com/v1

# 模型选择
OPENAI_MODEL=gpt-4o-mini

# ===================================
# 网络代理配置
# ===================================

# HTTP/HTTPS 代理 (国内用户必填)
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

# 或使用 SOCKS5
# HTTP_PROXY=socks5://127.0.0.1:7890
# HTTPS_PROXY=socks5://127.0.0.1:7890

# ===================================
# 超时和重试配置
# ===================================

# LLM 请求超时 (秒)
LLM_TIMEOUT=600

# 最大 token 数
LLM_MAX_TOKENS=16384

# ===================================
# 故障转移配置
# ===================================

# 启用认证故障转移
ENABLE_AUTH_FAILOVER=true

# 启用模型故障转移
ENABLE_MODEL_FAILOVER=true

# 模型 fallback 链 (逗号分隔)
MODEL_FALLBACKS=gpt-4o,gpt-3.5-turbo
```

---

## 🔍 常见问题排查

### Q1: 提示 "Connection timeout" 或 "Connection refused"

**原因**: 无法连接到 OpenAI API

**解决**:
1. 确认代理正在运行 (Clash/V2Ray/Shadowsocks)
2. 检查代理端口是否正确
3. 测试代理: `curl -x http://127.0.0.1:7890 https://www.google.com`

### Q2: 提示 "Invalid API key"

**原因**: API Key 不正确或未设置

**解决**:
1. 检查 `.env` 文件中的 `OPENAI_API_KEY`
2. 确认 API Key 没有多余的空格或引号
3. 在 OpenAI 官网验证 API Key 是否有效

### Q3: 提示 "Rate limit exceeded"

**原因**: API 调用频率超限

**解决**:
1. 等待几分钟后重试
2. 升级 OpenAI 账户额度
3. 启用模型故障转移，自动切换到其他模型

### Q4: 使用了代理但仍然超时

**可能原因**:
1. 代理配置格式错误
2. 防火墙阻止了代理连接
3. DNS 污染

**解决**:
```bash
# 检查代理格式
echo $HTTP_PROXY
echo $HTTPS_PROXY

# 测试代理
curl -v -x $HTTP_PROXY https://api.openai.com/v1/models

# 如果代理支持，可以添加 --resolve 强制使用特定 IP
curl --resolve api.openai.com:443:104.18.7.192 https://api.openai.com/v1/models
```

---

## 🚀 快速验证

运行以下命令验证配置:

```bash
cd /Users/shali.yx/Desktop/code/mcp-workflow/backend

# 1. 检查 .env 文件
cat ../.env | grep -E "PROXY|OPENAI"

# 2. 测试连接
python test_connection.py

# 3. 运行服务
python -m uvicorn app.main:app --reload
```

---

## 📞 进一步帮助

如果问题仍未解决:

1. **检查日志**: 查看 `backend/logs/app.log` 和 `backend/logs/error.log`
2. **启用调试模式**: 在 `.env` 中添加 `LOG_LEVEL=DEBUG`
3. **检查网络**: 确认能访问 https://www.google.com 和 https://api.openai.com
4. **尝试其他 API 端点**: 使用国内可访问的 OpenAI 兼容服务

---

**文档版本**: v1.0  
**最后更新**: 2026-02-03  
**适用场景**: OpenAI API 连接超时问题

