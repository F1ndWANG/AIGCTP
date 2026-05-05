"""
Conversation history truncation service.

Prevents unbounded message growth by summarizing old messages
when the estimated token count exceeds a threshold.
"""
from app.services.llm import llm_service
from app.core.logging import get_logger

logger = get_logger(__name__)

# Conservative heuristic: Chinese text ~2 chars/token, English ~4 chars/token
# Using len // 2 as a safe middle ground for mixed text
CHARS_PER_TOKEN = 2

SOFT_MAX_TOKENS = 3000
HARD_MAX_TOKENS = 4000
KEEP_RECENT = 6  # always keep the last N messages intact


def _estimate_tokens(text: str) -> int:
    """Estimate token count from text length."""
    return len(text) // CHARS_PER_TOKEN


def _estimate_messages_tokens(messages: list[dict]) -> int:
    """Estimate total tokens in a list of messages."""
    total = 0
    for msg in messages:
        total += _estimate_tokens(msg.get("content", "") or "")
        total += _estimate_tokens(msg.get("role", ""))
    return total


async def truncate_messages(messages: list[dict]) -> list[dict]:
    """Truncate message history if it exceeds token thresholds.

    Keeps the last KEEP_RECENT messages intact and summarizes older ones.
    Returns the truncated (or original) message list.
    """
    total_tokens = _estimate_messages_tokens(messages)

    if total_tokens < SOFT_MAX_TOKENS:
        return messages

    if len(messages) <= KEEP_RECENT + 1:
        # Not enough messages to truncate meaningfully, just keep recent
        return messages

    # Split: old messages to summarize + recent messages to keep
    recent = messages[-KEEP_RECENT:]
    old = messages[:-KEEP_RECENT]

    # Build summary from old messages
    old_text = "\n".join(
        f"{m['role']}: {m['content'][:500]}" for m in old
    )

    try:
        summary = await llm_service.chat(
            system_prompt="你是对话摘要助手。请用中文简洁概括以下对话的核心内容，"
                          "保留关键事实、用户偏好和已做出的决定。控制在200字以内。",
            messages=[{"role": "user", "content": f"请概括这段对话：\n\n{old_text}"}],
            max_tokens=512,
            temperature=0.3,
        )
        summary_entry = {
            "role": "system",
            "content": f"[会话摘要] {summary}",
        }
        truncated = [summary_entry] + recent
    except Exception as e:
        logger.warning("Truncation summary failed: %s", e)
        # Fallback: just keep recent messages
        truncated = recent

    # Check if we're still over HARD_MAX after one round
    if _estimate_messages_tokens(truncated) > HARD_MAX_TOKENS and len(truncated) > KEEP_RECENT:
        # Keep only the summary + the most recent messages
        truncated = truncated[:1] + truncated[-min(KEEP_RECENT, len(truncated) - 1):]

    return truncated
