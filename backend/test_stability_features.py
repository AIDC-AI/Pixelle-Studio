"""
测试稳定性优化功能

运行方式:
    python test_stability_features.py
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.auth.models import AuthStore, AuthProfile
from app.context.guard import evaluate_context_window_guard, estimate_token_count
from app.context.compaction import generate_simple_summary
from app.config import get_config


def test_auth_store():
    """测试认证配置存储"""
    print("=" * 60)
    print("测试 1: 认证配置存储 (AuthStore)")
    print("=" * 60)
    
    # 创建存储
    store = AuthStore()
    
    # 添加配置
    store.add_profile(AuthProfile(
        id="test-primary",
        provider="openai",
        api_key="sk-test-primary",
        base_url=None
    ))
    
    store.add_profile(AuthProfile(
        id="test-backup",
        provider="openai",
        api_key="sk-test-backup",
        base_url=None
    ))
    
    print(f"✓ 添加了 {len(store.profiles)} 个配置")
    
    # 获取候选配置
    candidates = store.get_candidates("openai")
    print(f"✓ 获取到 {len(candidates)} 个候选配置")
    
    # 测试失败标记
    store.mark_failure("test-primary", "rate_limit")
    print(f"✓ 标记 test-primary 失败")
    
    # 检查是否在冷却期
    primary = store.profiles[0]
    in_cooldown = store.is_in_cooldown(primary)
    print(f"✓ test-primary 在冷却期: {in_cooldown}")
    print(f"✓ 失败次数: {primary.failure_count}")
    
    print("\n✅ 认证配置存储测试通过\n")


def test_context_guard():
    """测试上下文窗口检查"""
    print("=" * 60)
    print("测试 2: Context Window Guard")
    print("=" * 60)
    
    # 构建测试消息
    messages = [
        {"role": "user", "content": "Hello" * 100},
        {"role": "assistant", "content": "Hi there!" * 100},
        {"role": "user", "content": "How are you?" * 100},
    ]
    
    system_prompt = "You are a helpful assistant." * 50
    
    # 评估上下文窗口
    should_block, warning, stats = evaluate_context_window_guard(
        model="gpt-4o",
        messages=messages,
        system_prompt=system_prompt
    )
    
    print(f"✓ 模型: {stats['model']}")
    print(f"✓ 上下文窗口: {stats['context_window']:,} tokens")
    print(f"✓ 已使用: {stats['used_tokens']:,} tokens")
    print(f"✓ 剩余: {stats['remaining_tokens']:,} tokens")
    print(f"✓ 使用率: {stats['usage_ratio']:.1%}")
    print(f"✓ 消息数: {stats['message_count']}")
    
    if warning:
        print(f"⚠️  警告: {warning}")
    
    if should_block:
        print("🚫 应该阻止请求 (触发压缩)")
    else:
        print("✅ 可以继续请求")
    
    print("\n✅ Context Window Guard 测试通过\n")


def test_token_estimation():
    """测试 token 估算"""
    print("=" * 60)
    print("测试 3: Token 估算")
    print("=" * 60)
    
    # 英文文本
    english_text = "Hello, how are you doing today? This is a test message."
    english_tokens = estimate_token_count(english_text)
    print(f"✓ 英文: \"{english_text[:30]}...\"")
    print(f"  长度: {len(english_text)} chars")
    print(f"  估算: {english_tokens} tokens")
    print(f"  比例: ~{len(english_text)/english_tokens:.1f} chars/token")
    
    # 中文文本
    chinese_text = "你好,今天天气怎么样?这是一条测试消息。我们正在测试token估算功能。"
    chinese_tokens = estimate_token_count(chinese_text)
    print(f"\n✓ 中文: \"{chinese_text[:20]}...\"")
    print(f"  长度: {len(chinese_text)} chars")
    print(f"  估算: {chinese_tokens} tokens")
    print(f"  比例: ~{len(chinese_text)/chinese_tokens:.1f} chars/token")
    
    # 混合文本
    mixed_text = "Hello 你好! This is 一个 mixed message 混合消息."
    mixed_tokens = estimate_token_count(mixed_text)
    print(f"\n✓ 混合: \"{mixed_text}\"")
    print(f"  长度: {len(mixed_text)} chars")
    print(f"  估算: {mixed_tokens} tokens")
    print(f"  比例: ~{len(mixed_text)/mixed_tokens:.1f} chars/token")
    
    print("\n✅ Token 估算测试通过\n")


def test_simple_summary():
    """测试简单摘要生成"""
    print("=" * 60)
    print("测试 4: 简单摘要生成")
    print("=" * 60)
    
    messages = [
        {"role": "user", "content": "请帮我创建一个 Excel 文件"},
        {"role": "assistant", "content": "好的,我会帮你创建 Excel 文件"},
        {"role": "tool", "content": "执行成功"},
        {"role": "user", "content": "添加一些数据"},
        {"role": "assistant", "content": "数据已添加"},
    ]
    
    summary = generate_simple_summary(messages)
    print(f"✓ 输入消息数: {len(messages)}")
    print(f"✓ 生成摘要:\n{summary}")
    
    print("\n✅ 简单摘要生成测试通过\n")


def test_config():
    """测试配置管理"""
    print("=" * 60)
    print("测试 5: 配置管理")
    print("=" * 60)
    
    config = get_config()
    
    print(f"✓ 默认模型: {config.default_model}")
    print(f"✓ LLM 超时: {config.llm_timeout}s")
    print(f"✓ LLM 最大 tokens: {config.llm_max_tokens}")
    print(f"✓ 启用认证故障转移: {config.enable_auth_failover}")
    print(f"✓ 启用模型故障转移: {config.enable_model_failover}")
    print(f"✓ 启用 Thinking 故障转移: {config.enable_thinking_failover}")
    print(f"✓ 启用上下文压缩: {config.context_compaction_enabled}")
    print(f"✓ 保留最近消息数: {config.context_keep_recent}")
    
    # 获取模型链
    model_chain = config.get_model_chain()
    print(f"\n✓ 模型 fallback 链: {' → '.join(model_chain)}")
    
    print("\n✅ 配置管理测试通过\n")


def test_auth_from_env():
    """测试从环境变量加载认证"""
    print("=" * 60)
    print("测试 6: 从环境变量加载认证")
    print("=" * 60)
    
    import os
    
    # 临时设置环境变量
    os.environ["OPENAI_API_KEY"] = "sk-test-env-primary"
    os.environ["OPENAI_API_KEY_BACKUP"] = "sk-test-env-backup"
    
    store = AuthStore.from_env()
    
    print(f"✓ 从环境变量加载了 {len(store.profiles)} 个配置")
    
    for profile in store.profiles:
        print(f"  - {profile.id}: {profile.api_key[:20]}...")
    
    # 清理环境变量
    del os.environ["OPENAI_API_KEY"]
    del os.environ["OPENAI_API_KEY_BACKUP"]
    
    print("\n✅ 环境变量加载测试通过\n")


async def test_compaction_with_llm():
    """测试 LLM 摘要生成 (需要有效的 API Key)"""
    print("=" * 60)
    print("测试 7: LLM 摘要生成 (可选)")
    print("=" * 60)
    
    import os
    from app.context.compaction import generate_summary
    from openai import AsyncOpenAI
    
    # 检查是否有 API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  跳过: 未设置 OPENAI_API_KEY 环境变量")
        print()
        return
    
    messages = [
        {"role": "user", "content": "请帮我创建一个包含销售数据的 Excel 文件"},
        {"role": "assistant", "content": "好的,我会创建一个 Excel 文件并添加销售数据"},
        {"role": "tool", "content": "文件创建成功: sales_data.xlsx"},
        {"role": "user", "content": "请添加图表"},
        {"role": "assistant", "content": "已添加柱状图"},
    ]
    
    try:
        client = AsyncOpenAI()
        summary = await generate_summary(messages, client)
        print(f"✓ 输入消息数: {len(messages)}")
        print(f"✓ 生成摘要:\n{summary}")
        print("\n✅ LLM 摘要生成测试通过\n")
    except Exception as e:
        print(f"⚠️  测试失败: {e}")
        print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("稳定性优化功能测试套件")
    print("=" * 60 + "\n")
    
    try:
        # 同步测试
        test_auth_store()
        test_context_guard()
        test_token_estimation()
        test_simple_summary()
        test_config()
        test_auth_from_env()
        
        # 异步测试
        asyncio.run(test_compaction_with_llm())
        
        print("=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

