"""
基础功能测试 - 不依赖外部库

运行方式:
    python3 test_basic_features.py
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def test_auth_models():
    """测试认证模型"""
    print("=" * 60)
    print("测试 1: 认证模型 (AuthProfile & AuthStore)")
    print("=" * 60)
    
    from app.auth.models import AuthStore, AuthProfile
    
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
    assert len(store.profiles) == 2, "应该有 2 个配置"
    
    # 获取候选配置
    candidates = store.get_candidates("openai")
    print(f"✓ 获取到 {len(candidates)} 个候选配置")
    assert len(candidates) == 2, "应该有 2 个候选配置"
    
    # 测试失败标记
    store.mark_failure("test-primary", "rate_limit")
    print(f"✓ 标记 test-primary 失败")
    
    # 检查失败次数
    primary = store.profiles[0]
    assert primary.failure_count == 1, "失败次数应该是 1"
    print(f"✓ 失败次数: {primary.failure_count}")
    
    # 检查是否在冷却期
    in_cooldown = store.is_in_cooldown(primary)
    print(f"✓ test-primary 在冷却期: {in_cooldown}")
    assert in_cooldown == True, "应该在冷却期"
    
    # 测试成功标记
    store.mark_success("test-primary")
    assert primary.failure_count == 0, "失败次数应该重置为 0"
    print(f"✓ 成功重置失败计数")
    
    print("\n✅ 认证模型测试通过\n")


def test_context_guard():
    """测试上下文窗口检查"""
    print("=" * 60)
    print("测试 2: Context Window Guard")
    print("=" * 60)
    
    from app.context.guard import (
        evaluate_context_window_guard, 
        estimate_token_count,
        MODEL_CONTEXT_WINDOWS
    )
    
    # 测试 token 估算
    english_text = "Hello, how are you?" * 10
    english_tokens = estimate_token_count(english_text)
    print(f"✓ 英文 token 估算: {len(english_text)} chars → {english_tokens} tokens")
    assert english_tokens > 0, "token 数应该大于 0"
    
    chinese_text = "你好,今天天气怎么样?" * 10
    chinese_tokens = estimate_token_count(chinese_text)
    print(f"✓ 中文 token 估算: {len(chinese_text)} chars → {chinese_tokens} tokens")
    assert chinese_tokens > 0, "token 数应该大于 0"
    
    # 测试上下文窗口检查
    messages = [
        {"role": "user", "content": "Hello" * 1000},
        {"role": "assistant", "content": "Hi" * 1000},
    ]
    
    should_block, warning, stats = evaluate_context_window_guard(
        model="gpt-4o",
        messages=messages,
        system_prompt="You are a helpful assistant."
    )
    
    print(f"\n✓ 上下文窗口检查:")
    print(f"  - 模型: {stats['model']}")
    print(f"  - 窗口大小: {stats['context_window']:,} tokens")
    print(f"  - 已使用: {stats['used_tokens']:,} tokens")
    print(f"  - 剩余: {stats['remaining_tokens']:,} tokens")
    print(f"  - 使用率: {stats['usage_ratio']:.1%}")
    
    assert stats['context_window'] == MODEL_CONTEXT_WINDOWS['gpt-4o'], "窗口大小应该匹配"
    assert stats['used_tokens'] > 0, "已使用 token 应该大于 0"
    assert stats['remaining_tokens'] > 0, "剩余 token 应该大于 0"
    
    if warning:
        print(f"  ⚠️  {warning}")
    
    if should_block:
        print(f"  🚫 应该阻止请求")
    else:
        print(f"  ✅ 可以继续请求")
    
    print("\n✅ Context Window Guard 测试通过\n")


def test_compaction():
    """测试简单摘要"""
    print("=" * 60)
    print("测试 3: 简单摘要生成")
    print("=" * 60)
    
    from app.context.compaction import generate_simple_summary
    
    messages = [
        {"role": "user", "content": "创建 Excel"},
        {"role": "assistant", "content": "好的"},
        {"role": "tool", "content": "成功", "tool_call_id": "call_123"},
        {"role": "user", "content": "添加数据"},
        {"role": "assistant", "content": "已添加"},
    ]
    
    summary = generate_simple_summary(messages)
    
    print(f"✓ 输入: {len(messages)} 条消息")
    print(f"✓ 摘要:\n{summary}")
    
    assert len(summary) > 0, "摘要应该不为空"
    assert "5" in summary, "摘要应该包含消息数量"
    
    print("\n✅ 简单摘要生成测试通过\n")


def test_config():
    """测试配置"""
    print("=" * 60)
    print("测试 4: 配置管理")
    print("=" * 60)
    
    from app.config import get_config
    
    config = get_config()
    
    print(f"✓ 默认模型: {config.default_model}")
    print(f"✓ LLM 超时: {config.llm_timeout}s")
    print(f"✓ 启用认证故障转移: {config.enable_auth_failover}")
    print(f"✓ 启用模型故障转移: {config.enable_model_failover}")
    print(f"✓ 启用上下文压缩: {config.context_compaction_enabled}")
    
    # 测试模型链
    model_chain = config.get_model_chain()
    print(f"✓ 模型链: {' → '.join(model_chain)}")
    
    assert len(model_chain) > 0, "模型链不应为空"
    assert model_chain[0] == config.default_model, "第一个应该是默认模型"
    
    # 测试配置字典
    config_dict = config.to_dict()
    assert 'default_model' in config_dict, "配置字典应包含 default_model"
    print(f"✓ 配置字典包含 {len(config_dict)} 个键")
    
    print("\n✅ 配置管理测试通过\n")


def test_auth_from_env():
    """测试从环境变量加载"""
    print("=" * 60)
    print("测试 5: 从环境变量加载认证")
    print("=" * 60)
    
    import os
    from app.auth.models import AuthStore
    
    # 临时设置
    original_key = os.environ.get("OPENAI_API_KEY")
    original_backup = os.environ.get("OPENAI_API_KEY_BACKUP")
    
    os.environ["OPENAI_API_KEY"] = "sk-test-env"
    os.environ["OPENAI_API_KEY_BACKUP"] = "sk-test-backup"
    
    store = AuthStore.from_env()
    
    print(f"✓ 加载了 {len(store.profiles)} 个配置")
    
    assert len(store.profiles) >= 1, "应该至少有 1 个配置"
    
    for profile in store.profiles:
        print(f"  - {profile.id}: {profile.api_key[:15]}...")
    
    # 恢复环境变量
    if original_key:
        os.environ["OPENAI_API_KEY"] = original_key
    else:
        del os.environ["OPENAI_API_KEY"]
    
    if original_backup:
        os.environ["OPENAI_API_KEY_BACKUP"] = original_backup
    elif "OPENAI_API_KEY_BACKUP" in os.environ:
        del os.environ["OPENAI_API_KEY_BACKUP"]
    
    print("\n✅ 环境变量加载测试通过\n")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("稳定性优化基础功能测试")
    print("=" * 60 + "\n")
    
    tests = [
        test_auth_models,
        test_context_guard,
        test_compaction,
        test_config,
        test_auth_from_env,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n❌ 测试失败: {test.__name__}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
            print()
    
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("✅ 所有测试通过!")
    else:
        print("❌ 部分测试失败")
    
    print("=" * 60 + "\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

