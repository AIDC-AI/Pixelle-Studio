#!/usr/bin/env python3
"""
测试脚本：验证模型是否可用以及 tool calling 行为
"""
import asyncio
import os
import json
from openai import AsyncOpenAI

# 配置
LLM_BASE_URL = "https://REDACTED_BASE_URL_HOST/v1"
LLM_API_KEY = "REDACTED_API_KEY"
MODEL_NAME = "gpt-5.1-2025-11-13-GlobalStandard"

# 测试用的工具定义
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Execute Python code to generate files",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            },
            "strict": True
        }
    }
]

async def test_basic_completion():
    """测试 1: 基础文本生成（无 tool calling）"""
    print("\n" + "="*80)
    print("测试 1: 基础文本生成")
    print("="*80)
    
    client = AsyncOpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL
    )
    
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello World' and nothing else."}
            ],
            temperature=0.7,
            max_tokens=50
        )
        
        print(f"✅ 模型响应成功")
        print(f"Response ID: {response.id}")
        print(f"Model: {response.model}")
        print(f"Choices 数量: {len(response.choices)}")
        print(f"Content: {response.choices[0].message.content}")
        print(f"Finish Reason: {response.choices[0].finish_reason}")
        
        return True
    except Exception as e:
        print(f"❌ 模型响应失败: {e}")
        return False


async def test_tool_calling():
    """测试 2: Tool Calling 能力"""
    print("\n" + "="*80)
    print("测试 2: Tool Calling")
    print("="*80)
    
    client = AsyncOpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL
    )
    
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """You have access to a tool called 'execute_code'.
When the user asks you to generate a file, you should:
1. First, explain what you'll do
2. Then, call the execute_code tool to do it
"""
                },
                {
                    "role": "user",
                    "content": "Please generate an HTML file with Hello World. Call the execute_code tool."
                }
            ],
            tools=TOOLS,
            temperature=0.7
        )
        
        print(f"✅ 模型响应成功")
        print(f"Response ID: {response.id}")
        print(f"Model: {response.model}")
        
        message = response.choices[0].message
        print(f"\nContent 长度: {len(message.content) if message.content else 0}")
        print(f"Content: {message.content[:200] if message.content else '(空)'}")
        print(f"Tool Calls: {message.tool_calls}")
        print(f"Finish Reason: {response.choices[0].finish_reason}")
        
        if message.tool_calls:
            print(f"\n✅ 模型调用了工具:")
            for tool_call in message.tool_calls:
                print(f"  - Tool: {tool_call.function.name}")
                print(f"  - Arguments: {tool_call.function.arguments}")
        elif not message.content or len(message.content.strip()) == 0:
            print(f"\n⚠️ 警告: 模型返回空内容且没有调用工具!")
            
        return True
    except Exception as e:
        print(f"❌ 模型响应失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_streaming():
    """测试 3: 流式响应"""
    print("\n" + "="*80)
    print("测试 3: 流式响应")
    print("="*80)
    
    client = AsyncOpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL
    )
    
    try:
        stream = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Count from 1 to 5, one number per line."}
            ],
            temperature=0.7,
            stream=True
        )
        
        print(f"✅ 开始接收流式响应:")
        
        chunk_count = 0
        full_content = ""
        
        async for chunk in stream:
            chunk_count += 1
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_content += delta.content
                    print(f"  Chunk {chunk_count}: {repr(delta.content)}")
        
        print(f"\n✅ 流式响应完成")
        print(f"总共接收 {chunk_count} 个 chunks")
        print(f"完整内容: {full_content}")
        
        return True
    except Exception as e:
        print(f"❌ 流式响应失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_streaming_with_tools():
    """测试 4: 流式响应 + Tool Calling"""
    print("\n" + "="*80)
    print("测试 4: 流式响应 + Tool Calling")
    print("="*80)
    
    client = AsyncOpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL
    )
    
    try:
        stream = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """You have access to a tool called 'execute_code'.
When the user asks you to generate a file, you MUST:
1. First, write a detailed explanation of what you'll do (at least 50 characters)
2. Then, call the execute_code tool
"""
                },
                {
                    "role": "user",
                    "content": "Please generate an HTML file. First explain, then call execute_code tool."
                }
            ],
            tools=TOOLS,
            temperature=0.7,
            stream=True
        )
        
        print(f"✅ 开始接收流式响应:")
        
        chunk_count = 0
        full_content = ""
        tool_calls_data = []
        
        async for chunk in stream:
            chunk_count += 1
            if chunk.choices:
                delta = chunk.choices[0].delta
                
                # 检查内容
                if delta.content:
                    full_content += delta.content
                    print(f"  Chunk {chunk_count} (content): {repr(delta.content)[:100]}")
                
                # 检查 tool calls
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        print(f"  Chunk {chunk_count} (tool_call): {tool_call}")
                        tool_calls_data.append(tool_call)
        
        print(f"\n✅ 流式响应完成")
        print(f"总共接收 {chunk_count} 个 chunks")
        print(f"完整内容长度: {len(full_content)}")
        print(f"完整内容: {full_content[:200]}")
        print(f"Tool Calls 数量: {len(tool_calls_data)}")
        
        if len(full_content.strip()) == 0 and len(tool_calls_data) > 0:
            print(f"\n⚠️ 警告: 模型返回空内容但调用了工具（这是问题所在！）")
        elif len(full_content.strip()) > 0 and len(tool_calls_data) > 0:
            print(f"\n✅ 正常: 模型返回内容并调用了工具")
        
        return True
    except Exception as e:
        print(f"❌ 流式响应失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_list_models():
    """测试 5: 列出可用模型"""
    print("\n" + "="*80)
    print("测试 5: 列出可用模型")
    print("="*80)
    
    client = AsyncOpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL
    )
    
    try:
        models = await client.models.list()
        print(f"✅ 可用模型列表:")
        for model in models.data:
            print(f"  - {model.id}")
            if MODEL_NAME in model.id or "gpt-5" in model.id:
                print(f"    ⭐ 包含目标模型名称")
        
        return True
    except Exception as e:
        print(f"❌ 获取模型列表失败: {e}")
        return False


async def main():
    print("\n" + "="*80)
    print("模型测试脚本")
    print("="*80)
    print(f"模型: {MODEL_NAME}")
    print(f"API 端点: {LLM_BASE_URL}")
    print(f"API Key: {LLM_API_KEY[:20]}...")
    
    # 运行所有测试
    results = {}
    
    results["basic"] = await test_basic_completion()
    results["tool_calling"] = await test_tool_calling()
    results["streaming"] = await test_streaming()
    results["streaming_tools"] = await test_streaming_with_tools()
    results["list_models"] = await test_list_models()
    
    # 总结
    print("\n" + "="*80)
    print("测试结果总结")
    print("="*80)
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\n总计: {passed}/{total} 通过")
    
    if results.get("streaming_tools"):
        print("\n💡 建议:")
        print("1. 如果模型返回空内容但调用工具，这是模型的特殊行为")
        print("2. 代码需要处理 content 为空的情况")
        print("3. 可以修改代码逻辑，允许 content 为空时继续处理")


if __name__ == "__main__":
    asyncio.run(main())




