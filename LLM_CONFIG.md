# LLM Configuration Guide

## Where to Configure

LLM settings are configured in the backend at:

**File**: `/Users/huqingli/Desktop/hql_files/projs/pycharms/mcp-workflow/backend/app/llm_adapter.py`

## Configuration Variables

```python
# LLM Configuration (Lines 6-8)
LLM_BASE_URL = "https://api.deepseek.com"  # Your LLM API base URL
LLM_API_KEY = "sk-88435555444444444444444444444444"  # Your API Key
LLM_MODEL = "deepseek-chat"  # Model name
```

## Supported LLM Providers

### DeepSeek (Current Default)
```python
LLM_BASE_URL = "https://api.deepseek.com"
LLM_API_KEY = "sk-your-actual-deepseek-key-here"
LLM_MODEL = "deepseek-chat"
```

### OpenAI
```python
LLM_BASE_URL = "https://api.openai.com/v1"
LLM_API_KEY = "sk-your-openai-key-here"
LLM_MODEL = "gpt-4"
```

### Other OpenAI-Compatible APIs
Any API that follows the OpenAI chat completions format will work:
```python
LLM_BASE_URL = "https://your-api-endpoint.com/v1"
LLM_API_KEY = "your-api-key"
LLM_MODEL = "your-model-name"
```

## How to Update

1. Open `backend/app/llm_adapter.py`
2. Update lines 6-8 with your LLM configuration
3. Save the file
4. The backend will auto-reload (if running with `--reload` flag)

## Verification

After updating the configuration:
1. Go to http://localhost:5173/
2. Select some MCP tools
3. Enter a request like "给我生成一个主题为治愈原生家庭的视频"
4. Click Send
5. You should see the LLM generate a custom script based on your request

## Current Implementation

The system now:
- ✅ Uses **real LLM** to generate workflow scripts (not mock)
- ✅ Makes **real MCP calls** to configured servers (not mock)
- ✅ Executes generated scripts with actual async tool calls
- ✅ Handles errors gracefully with fallback scripts
