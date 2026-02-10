"""Auto-Compaction - automatic context compression"""

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
    Compress history messages.
    
    Strategy:
    1. Keep the most recent N messages (default 10)
    2. Generate summary for earlier messages
    3. Insert summary as system message
    
    Args:
        messages: History message list
        keep_recent: Number of recent messages to keep
        client: OpenAI client (optional)
    
    Returns:
        Compressed message list
    """
    if len(messages) <= keep_recent:
        logger.info(f"[Compaction] Message count ({len(messages)}) <= keep_recent ({keep_recent}), no compaction needed")
        return messages
    
    logger.info(f"[Compaction] Starting compaction: {len(messages)} messages -> keep recent {keep_recent}")
    
    # Separate old messages and recent messages
    old_messages = messages[:-keep_recent]
    recent_messages = messages[-keep_recent:]
    
    # Generate summary
    try:
        summary = await generate_summary(old_messages, client)
        logger.info(f"[Compaction] Generated summary ({len(summary)} chars)")
    except Exception as e:
        logger.error(f"[Compaction] Failed to generate summary: {e}")
        # If summary generation fails, use simple text summary
        summary = generate_simple_summary(old_messages)
    
    # Build new history
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
    Generate summary using LLM.
    
    Args:
        messages: List of messages to summarize
        client: OpenAI client
    
    Returns:
        Summary text
    """
    if client is None:
        client = AsyncOpenAI()
    
    # Build summary request
    messages_text = ""
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        
        # Skip overly long content
        if len(str(content)) > 2000:
            content = str(content)[:2000] + "... (truncated)"
        
        messages_text += f"{role}: {content}\n\n"
    
    # Limit input length
    if len(messages_text) > 10000:
        messages_text = messages_text[:10000] + "\n... (truncated due to length)"
    
    logger.info(f"[Compaction] Generating summary for {len(messages_text)} chars of history")
    
    try:
        summary_model = "gpt-3.5-turbo"
        response = await client.chat.completions.create(
            model=summary_model,  # Use cheap and fast model
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
        
        # Log token usage
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            from app.utils.session_logger_simple import estimate_cost
            cost = estimate_cost(summary_model, usage.prompt_tokens, usage.completion_tokens)
            logger.info(
                f"[TokenUsage][compaction_summary] model={summary_model} "
                f"prompt={usage.prompt_tokens} completion={usage.completion_tokens} "
                f"total={usage.total_tokens} cost=${cost:.6f}"
            )
        
        summary = response.choices[0].message.content
        return summary or "(No summary generated)"
    
    except Exception as e:
        logger.error(f"[Compaction] LLM summary failed: {e}")
        raise


def generate_simple_summary(messages: List[Dict[str, Any]]) -> str:
    """
    Generate simple text summary (without LLM).
    
    Used as fallback when LLM summary generation fails.
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
    
    # Extract some key information
    if user_messages:
        first_user = user_messages[0].get("content", "")[:100]
        summary_parts.append(f"- First user request: {first_user}...")
    
    # Check for tool calls
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
    Estimate compressed size (token count).
    
    Used to predict compression effectiveness.
    """
    from .guard import estimate_token_count
    
    if len(messages) <= keep_recent:
        # No compression needed
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += estimate_token_count(str(content))
        return total
    
    # Estimate summary size (conservative estimate of 500 tokens)
    summary_size = 500
    
    # Estimate size of retained messages
    recent_size = 0
    for msg in messages[-keep_recent:]:
        content = msg.get("content", "")
        recent_size += estimate_token_count(str(content))
    
    return summary_size + recent_size

