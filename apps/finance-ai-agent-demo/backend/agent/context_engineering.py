"""Context usage calculation, summarization, and offloading."""

import uuid

from config import MODEL_TOKEN_LIMITS, OPENAI_MODEL


def calculate_context_usage(context, model=None):
    """Calculate context window usage as percentage."""
    model = model or OPENAI_MODEL
    estimated_tokens = len(context) // 4  # ~4 chars per token
    max_tokens = MODEL_TOKEN_LIMITS.get(model, 128_000)
    percentage = (estimated_tokens / max_tokens) * 100
    return {
        "tokens": estimated_tokens,
        "max": max_tokens,
        "percent": round(percentage, 1),
    }


def estimate_tokens(text):
    """Rough token estimation: ~4 characters per token."""
    if not text:
        return 0
    return len(text) // 4


def get_token_breakdown(memory_manager, thread_id, query):
    """Get token usage breakdown by memory type."""
    try:
        conv = memory_manager.read_conversational_memory(thread_id)
        kb = memory_manager.read_knowledge_base(query) if query else ""
        entities = memory_manager.read_entity(query or "entities", thread_id=thread_id)
        workflows = memory_manager.read_workflow(query or "workflow", thread_id=thread_id)
        summaries = memory_manager.read_summary_context(query or "", thread_id=thread_id)
    except Exception:
        conv = kb = entities = workflows = summaries = ""

    from agent.system_prompt import AGENT_SYSTEM_PROMPT

    return {
        "conversation": estimate_tokens(conv),
        "knowledge_base": estimate_tokens(kb),
        "entities": estimate_tokens(entities),
        "workflows": estimate_tokens(workflows),
        "system_prompt": estimate_tokens(AGENT_SYSTEM_PROMPT),
        "summary_refs": estimate_tokens(summaries),
    }


def summarize_context_window(content, memory_manager, llm_client, model=None, thread_id=None):
    """Summarize content using LLM and store in summary memory."""
    model = model or OPENAI_MODEL

    summary_prompt = f"""You are compressing an AI agent context window for later retrieval.
Produce a compact summary that preserves:
- user goal and constraints
- key facts/findings already established
- important entities (account IDs, client names, holdings)
- unresolved questions and next actions

Output 4-7 short bullet points.
Be faithful to the source, and do not add new facts.

Context window content:
{content[:3000]}"""

    response = llm_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": summary_prompt}],
        max_completion_tokens=220,
    )
    summary = response.choices[0].message.content

    desc_response = llm_client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": f"Write a short label (max 12 words) for this summary:\n{summary}",
            }
        ],
        max_completion_tokens=40,
    )
    description = desc_response.choices[0].message.content.strip()

    summary_id = str(uuid.uuid4())[:8]
    memory_manager.write_summary(summary_id, content, summary, description, thread_id=thread_id)

    return {"id": summary_id, "summary": summary, "description": description}


def summarize_conversation_for_thread(thread_id, memory_manager, llm_client):
    """Summarize unsummarized conversation for a specific thread."""
    unsummarized = memory_manager.get_unsummarized_messages(thread_id, limit=200)
    if not unsummarized:
        return {"id": None, "description": "No messages to compact", "messages_compacted": 0}

    full_text = "\n".join([f"[{m['role']}] {m['content']}" for m in unsummarized])
    result = summarize_context_window(full_text, memory_manager, llm_client, thread_id=thread_id)

    message_ids = [m["id"] for m in unsummarized]
    memory_manager.mark_as_summarized(thread_id, result["id"], message_ids=message_ids)

    result["messages_compacted"] = len(unsummarized)
    return result
