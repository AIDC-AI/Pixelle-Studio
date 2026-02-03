"""Auto-Compaction - 自动上下文压缩"""

from typing import List, Dict, Any
from openai import AsyncOpenAI
import logging

logger = logging.getLogger(__name__)


async def compact_history(
    messages: List[Dict[str, Any]],
    keep_recent: int = 10,
    client: AsyncOpenAI = None
) -> List[Dict[str, Any]]:
    """
    压缩历史消息。
    
    策略:
    1. 保留最近 N 条消息 (默认 10 条)
    2. 对早期消息生成摘要
    3. 将摘要插入为 system 消息
    
    Args:
        messages: 历史消息列表
        keep_recent: 保留最近几条消息
        client: OpenAI 客户端 (可选)
    
    Returns:
        压缩后的消息列表
    """
    if len(messages) <= keep_recent:
        logger.info(f"[Compaction] Message count ({len(messages)}) <= keep_recent ({keep_recent}), no compaction needed")
        return messages
    
    logger.info(f"[Compaction] Starting compaction: {len(messages)} messages -> keep recent {keep_recent}")
    
    # 分离早期消息和最近消息
    old_messages = messages[:-keep_recent]
    recent_messages = messages[-keep_recent:]
    
    # 生成摘要
    try:
        summary = await generate_summary(old_messages, client)
        logger.info(f"[Compaction] Generated summary ({len(summary)} chars)")
    except Exception as e:
        logger.error(f"[Compaction] Failed to generate summary: {e}")
        # 如果摘要生成失败,使用简单的文本摘要
        summary = generate_simple_summary(old_messages)
    
    # 构建新历史
    compacted = [
        {
            "role": "system",
            "content": f"[Previous Conversation Summary]\n{summary}\n\n[Note] The above is a summary of earlier conversation. Continue from the recent messages below."
        },
        *recent_messages
    ]
    
    logger.info(f"[Compaction] Compaction complete: {len(messages)} -> {len(compacted)} messages")
    
    return compacted


async def generate_summary(
    messages: List[Dict[str, Any]],
    client: AsyncOpenAI = None
) -> str:
    """
    使用 LLM 生成摘要。
    
    Args:
        messages: 要摘要的消息列表
        client: OpenAI 客户端
    
    Returns:
        摘要文本
    """
    if client is None:
        client = AsyncOpenAI()
    
    # 构建摘要请求
    messages_text = ""
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # 跳过过长的内容
        if len(str(content)) > 2000:
            content = str(content)[:2000] + "... (truncated)"
        
        messages_text += f"{role}: {content}\n\n"
    
    # 限制输入长度
    if len(messages_text) > 10000:
        messages_text = messages_text[:10000] + "\n... (truncated due to length)"
    
    logger.info(f"[Compaction] Generating summary for {len(messages_text)} chars of history")
    
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",  # 使用便宜快速的模型
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a conversation summarizer. "
                        "Summarize the key points of the following conversation. "
                        "Focus on: user requests, actions taken, results, and important context. "
                        "Keep it concise (300 words or less)."
                    )
                },
                {
                    "role": "user",
                    "content": f"Summarize this conversation:\n\n{messages_text}"
                }
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        summary = response.choices[0].message.content
        return summary or "(No summary generated)"
    
    except Exception as e:
        logger.error(f"[Compaction] LLM summary failed: {e}")
        raise


def generate_simple_summary(messages: List[Dict[str, Any]]) -> str:
    """
    生成简单的文本摘要 (不使用 LLM)。
    
    当 LLM 摘要失败时使用此方法作为 fallback。
    """
    logger.info(f"[Compaction] Using simple summary for {len(messages)} messages")
    
    summary_parts = [
        f"Summary of {len(messages)} previous messages:",
        ""
    ]
    
    user_messages = [m for m in messages if m.get("role") == "user"]
    assistant_messages = [m for m in messages if m.get("role") == "assistant"]
    
    summary_parts.append(f"- User messages: {len(user_messages)}")
    summary_parts.append(f"- Assistant messages: {len(assistant_messages)}")
    
    # 提取一些关键信息
    if user_messages:
        first_user = user_messages[0].get("content", "")[:100]
        summary_parts.append(f"- First user request: {first_user}...")
    
    # 检查是否有工具调用
    tool_calls_count = sum(
        1 for m in messages 
        if m.get("role") == "assistant" and "tool_calls" in m
    )
    if tool_calls_count > 0:
        summary_parts.append(f"- Tool calls made: {tool_calls_count}")
    
    return "\n".join(summary_parts)


def estimate_compacted_size(
    messages: List[Dict[str, Any]],
    keep_recent: int = 10
) -> int:
    """
    估算压缩后的大小 (token 数量)。
    
    用于预测压缩效果。
    """
    from .guard import estimate_token_count
    
    if len(messages) <= keep_recent:
        # 不需要压缩
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += estimate_token_count(str(content))
        return total
    
    # 估算摘要大小 (保守估计 500 tokens)
    summary_size = 500
    
    # 估算保留消息大小
    recent_size = 0
    for msg in messages[-keep_recent:]:
        content = msg.get("content", "")
        recent_size += estimate_token_count(str(content))
    
    return summary_size + recent_size

