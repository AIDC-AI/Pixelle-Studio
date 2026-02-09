"""Context Window Guard - preventive context window size check"""

from typing import Optional, Tuple

# Model context window configuration (tokens)
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

# Context window thresholds
CONTEXT_WINDOW_HARD_MIN = 8_000  # Hard minimum (must compress below this)
CONTEXT_WINDOW_WARN_BELOW = 16_000  # Warning threshold


def estimate_token_count(text: str) -> int:
    """
    Roughly estimate token count.
    
    Simple rule: 1 token ≈ 4 characters (English)
    For Chinese: 1 token ≈ 1.5-2 characters
    
    This is a conservative estimate; actual count may be lower.
    """
    # Detect Chinese character ratio
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total_chars = len(text)
    
    if total_chars == 0:
        return 0
    
    chinese_ratio = chinese_chars / total_chars
    
    # Adjust estimate based on Chinese ratio
    if chinese_ratio > 0.5:
        # Mainly Chinese
        return int(total_chars / 1.5)
    else:
        # Mainly English
        return int(total_chars / 4)


def evaluate_context_window_guard(
    model: str,
    messages: list,
    system_prompt: str = ""
) -> Tuple[bool, Optional[str], dict]:
    """
    Evaluate whether the context window is sufficient.
    
    Args:
        model: Model name
        messages: Message history
        system_prompt: System prompt
    
    Returns:
        (should_block, warning_message, stats)
        - should_block: Whether to block request (trigger auto-compaction)
        - warning_message: Warning message (if any)
        - stats: Statistics
    """
    # Get model's context window size
    context_window = MODEL_CONTEXT_WINDOWS.get(model, 16_384)
    
    # Estimate currently used tokens
    total_text = system_prompt
    for msg in messages:
        content = msg.get("content")
        if content:
            total_text += str(content)
        
        # Also count tool_calls if present
        if "tool_calls" in msg:
            for tc in msg["tool_calls"]:
                if "function" in tc:
                    total_text += str(tc["function"])
    
    used_tokens = estimate_token_count(total_text)
    remaining_tokens = context_window - used_tokens
    usage_ratio = used_tokens / context_window
    
    # Build statistics
    stats = {
        "model": model,
        "context_window": context_window,
        "used_tokens": used_tokens,
        "remaining_tokens": remaining_tokens,
        "usage_ratio": usage_ratio,
        "message_count": len(messages)
    }
    
    # Check if below hard minimum
    if remaining_tokens < CONTEXT_WINDOW_HARD_MIN:
        warning = (
            f"Context window too small ({remaining_tokens} tokens remaining, "
            f"minimum is {CONTEXT_WINDOW_HARD_MIN}). Auto-compaction required."
        )
        return True, warning, stats
    
    # Check if below warning threshold
    if remaining_tokens < CONTEXT_WINDOW_WARN_BELOW:
        warning = (
            f"Low context window: {remaining_tokens} tokens remaining "
            f"(usage: {usage_ratio:.1%}, warn threshold: {CONTEXT_WINDOW_WARN_BELOW})"
        )
        return False, warning, stats
    
    # Everything normal
    return False, None, stats


def should_compact_history(
    messages: list,
    model: str,
    min_messages_before_compact: int = 10
) -> bool:
    """
    Determine whether history messages should be compacted.
    
    Args:
        messages: Message history
        model: Model name
        min_messages_before_compact: Minimum message count before considering compaction
    
    Returns:
        Whether to compact
    """
    # Too few messages, no compaction needed
    if len(messages) < min_messages_before_compact:
        return False
    
    # Check context window
    should_block, _, stats = evaluate_context_window_guard(model, messages)
    
    # If approaching the limit, recommend compaction
    if should_block:
        return True
    
    # If usage exceeds 70%, also recommend compaction
    if stats["usage_ratio"] > 0.7:
        return True
    
    return False

