# LLM Configuration Guide

## Where to Configure

LLM settings are now configured via **environment variables**, which are loaded from `.env` file when starting the server.

**File**: `backend/.env` (create if not exists)

## Environment Variables

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-your-api-key-here

# Optional: Custom API Base URL (for compatible providers)
OPENAI_BASE_URL=https://api.openai.com/v1

# Optional: Model name (default: gpt-4o)
OPENAI_MODEL=gpt-4o
```

## Supported LLM Providers

### OpenAI (Default)
```bash
OPENAI_API_KEY=sk-your-openai-key-here
# OPENAI_BASE_URL is optional, defaults to OpenAI's API
OPENAI_MODEL=gpt-4o
```

### DeepSeek
```bash
OPENAI_API_KEY=sk-your-deepseek-key-here
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

### Other OpenAI-Compatible APIs
Any API that follows the OpenAI chat completions format will work:
```bash
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-api-endpoint.com/v1
OPENAI_MODEL=your-model-name
```

## How to Update

1. Create or edit `backend/.env` file
2. Add your LLM configuration
3. Restart the backend server (the `.env` file is loaded by `start_server.sh`)

### Example `.env` file:
```bash
# LLM Configuration
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# Other environment variables...
```

## How Environment Variables are Loaded

The `backend/start_server.sh` script automatically loads all environment variables from `.env`:

```bash
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
fi
```

## Verification

After updating the configuration:
1. Restart the backend with `./start_server.sh`
2. Go to http://localhost:5173/
3. Enter a chat message
4. You should see the LLM responding based on your configuration

## Current Implementation

The system now:
- ✅ Uses standard OpenAI environment variables (OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)
- ✅ OpenAI SDK automatically reads these from environment
- ✅ Supports any OpenAI-compatible API provider
- ✅ No hardcoded API keys in source code
