"""Context Window Guard - 预防性检查上下文窗口大小"""

from typing import Optional, Tuple

# 模型上下文窗口配置 (tokens)
MODEL_CONTEXT_WINDOWS = {
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_384,
    "claude-3-5-sonnet": 200_000,
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "claude-sonnet-4": 200_000,
    "claude-opus-4": 200_000,
    "gemini-2.0-pro": 1_000_000,
    "gemini-1.5-pro": 1_000_000,
}

# 上下文窗口阈值
CONTEXT_WINDOW_HARD_MIN = 8_000  # 硬性最小值 (低于此值必须压缩)
CONTEXT_WINDOW_WARN_BELOW = 16_000  # 警告阈值


def estimate_token_count(text: str) -> int:
    """
    粗略估算 token 数量。
    
    简单规则: 1 token ≈ 4 字符 (英文)
    对于中文: 1 token ≈ 1.5-2 字符
    
    这是一个保守估计,实际可能会少一些。
    """
    # 检测中文字符比例
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total_chars = len(text)
    
    if total_chars == 0:
        return 0
    
    chinese_ratio = chinese_chars / total_chars
    
    # 根据中文比例调整估算
    if chinese_ratio > 0.5:
        # 主要是中文
        return int(total_chars / 1.5)
    else:
        # 主要是英文
        return int(total_chars / 4)


def evaluate_context_window_guard(
    model: str,
    messages: list,
    system_prompt: str = ""
) -> Tuple[bool, Optional[str], dict]:
    """
    评估上下文窗口是否足够。
    
    Args:
        model: 模型名称
        messages: 消息历史
        system_prompt: 系统提示词
    
    Returns:
        (should_block, warning_message, stats)
        - should_block: 是否应该阻止请求 (触发自动压缩)
        - warning_message: 警告信息 (如果有)
        - stats: 统计信息
    """
    # 获取模型的上下文窗口大小
    context_window = MODEL_CONTEXT_WINDOWS.get(model, 16_384)
    
    # 估算当前使用的 token 数
    total_text = system_prompt
    for msg in messages:
        content = msg.get("content")
        if content:
            total_text += str(content)
        
        # 如果有 tool_calls,也要计算
        if "tool_calls" in msg:
            for tc in msg["tool_calls"]:
                if "function" in tc:
                    total_text += str(tc["function"])
    
    used_tokens = estimate_token_count(total_text)
    remaining_tokens = context_window - used_tokens
    usage_ratio = used_tokens / context_window
    
    # 构建统计信息
    stats = {
        "model": model,
        "context_window": context_window,
        "used_tokens": used_tokens,
        "remaining_tokens": remaining_tokens,
        "usage_ratio": usage_ratio,
        "message_count": len(messages)
    }
    
    # 检查是否低于硬性最小值
    if remaining_tokens < CONTEXT_WINDOW_HARD_MIN:
        warning = (
            f"Context window too small ({remaining_tokens} tokens remaining, "
            f"minimum is {CONTEXT_WINDOW_HARD_MIN}). Auto-compaction required."
        )
        return True, warning, stats
    
    # 检查是否低于警告阈值
    if remaining_tokens < CONTEXT_WINDOW_WARN_BELOW:
        warning = (
            f"Low context window: {remaining_tokens} tokens remaining "
            f"(usage: {usage_ratio:.1%}, warn threshold: {CONTEXT_WINDOW_WARN_BELOW})"
        )
        return False, warning, stats
    
    # 一切正常
    return False, None, stats


def should_compact_history(
    messages: list,
    model: str,
    min_messages_before_compact: int = 10
) -> bool:
    """
    判断是否应该压缩历史消息。
    
    Args:
        messages: 消息历史
        model: 模型名称
        min_messages_before_compact: 最少消息数量才考虑压缩
    
    Returns:
        是否应该压缩
    """
    # 消息太少,不需要压缩
    if len(messages) < min_messages_before_compact:
        return False
    
    # 检查上下文窗口
    should_block, _, stats = evaluate_context_window_guard(model, messages)
    
    # 如果已经接近上限,建议压缩
    if should_block:
        return True
    
    # 如果使用率超过 70%,也建议压缩
    if stats["usage_ratio"] > 0.7:
        return True
    
    return False

