# Part 4: Context Engineering Techniques

## What Is Context Engineering?

Context engineering is the discipline of deciding exactly which tokens enter the LLM's context window on each inference call.

A naive agent appends every message and every tool output to a growing list. This works for short sessions. For longer sessions it fails in two ways:

1. **Hard failure** — you exceed the model's token limit and the API call errors
2. **Soft failure** — the context fills with stale or irrelevant tokens, degrading response quality (the "lost in the middle" problem)

Context engineering replaces unbounded accumulation with deliberate curation.

## The Token Budget Mental Model

Every model has a token limit. Think of it as a budget:

| Model         | Token limit |
| ------------- | ----------- |
| GPT-5         | 128,000     |
| GPT-5-mini    | 128,000     |
| GPT-4-turbo   | 128,000     |
| GPT-4         | 8,192       |
| GPT-3.5-turbo | 16,385      |

Your context on each call consumes some of that budget across:

- System prompt
- Retrieved memory (conversation history, knowledge, workflow)
- Current user message
- Tool definitions
- Tool call outputs

The remaining budget is available for the model's response. Good context engineering keeps each component proportional and prunes aggressively when you approach the limit.

## TODO 12: `calculate_context_usage`

This function estimates how much of the context budget is used and returns a percentage. It is called inside the agent harness on each iteration to trigger summarisation when the context gets too large.

**Token estimation:** Dividing character count by 4 gives a reasonable approximation for English text (average ~4 characters per token). For production use `tiktoken` for exact counts. The approximation is sufficient for threshold-based decisions.

**Complete solution:**

```python
def calculate_context_usage(context: str, model: str = "gpt-5-mini") -> dict:
    """Calculate context window usage as a percentage."""
    estimated_tokens = len(context) // 4
    max_tokens = MODEL_TOKEN_LIMITS.get(model, 128000)
    percentage = (estimated_tokens / max_tokens) * 100
    return {"tokens": estimated_tokens, "max": max_tokens, "percent": round(percentage, 1)}
```

> **Key names matter.** The agent harness reads `usage["tokens"]`, `usage["max"]`, and `usage["percent"]` directly. If your dict uses different key names (such as `estimated_tokens` or `percent_used`), the agent will raise a `KeyError` at runtime.

**Usage in the agent harness:**

```python
usage = calculate_context_usage(current_context, model="gpt-5")
if usage["percent"] > 80:
    # Trigger summarisation before the next LLM call
    context, summaries = offload_to_summary(context, memory_manager, llm_client)
```

## Context Summarisation and Offloading (Pre-built — Read Carefully)

The code cells following the TODO contain `summarise_context_window` and `offload_to_summary`. These are provided complete. Read them to understand the pattern.

**`summarise_context_window`** calls the LLM to compress a block of context into a summary, stores the summary in `SUMMARY_MEMORY`, and returns a reference ID.

**`offload_to_summary`** wraps the above: if context usage exceeds a threshold (default 80%), it replaces the verbose context with a compact summary reference. The agent can expand the reference later using the `expand_summary` tool.

This is conversation compaction — the same technique used by production agent frameworks to handle long-running sessions.

## The Summary Expansion Pattern

When context is offloaded, the full content is not lost — it is stored in Oracle's `SUMMARY_MEMORY` table. A `expand_summary` tool is registered in the toolbox, allowing the agent to retrieve the full content on demand:

```
Agent context: "... [SUMMARY REF: abc-123] ..."
Agent decides: I need the detail from that summary
Agent calls:   expand_summary(summary_id="abc-123")
Oracle returns: full original content
```

This is the key advantage of using a database for memory: the content is always retrievable, never truly discarded.

## The Context Growth Chart

The plotting cell at the end of Part 6 shows context window usage across agent iterations. After completing the workshop, compare the chart for the memory-engineered agent (Part 6 Step 1) versus the naive agent (Part 6 Step 2). The difference will be visible as a flat line versus a continuously growing line.

## Troubleshooting

**`calculate_context_usage` returns `None`** — Your function is missing the `return` statement. Make sure you return the dict.

**`KeyError` on `MODEL_TOKEN_LIMITS`** — Check the model name string. The dict uses specific keys like `"gpt-5"`. The function defaults to 128,000 for unknown models, so this should not raise — check if you accidentally removed the `.get()` default.

---

## TODO 13: Write the Summarisation Prompt

This is the most open-ended TODO in the workshop. The prompt you write directly determines the quality of what gets stored in summary memory — and therefore what the agent can recall later.

**What makes a good summarisation prompt:**

A poor prompt produces a vague paragraph. A good prompt produces a structured, faithful, retrievable snapshot. The key constraints are:

- **Bullet points** force conciseness — prose summaries are harder to scan and embed less distinctly
- **Faithfulness** — the agent must not hallucinate facts into a summary that gets stored as ground truth
- **Specific entities** — paper titles, arXiv IDs, and author names must survive compression or the agent loses traceability
- **Next actions** — preserving unresolved questions means the agent can pick up where it left off across sessions

**Complete solution:**

```python
summary_prompt = f"""
You are compressing an AI agent context window for later retrieval.
The content may include conversation memory, retrieved papers, entities, workflows, and prior summaries.

Produce a compact summary that preserves:
- user goal and constraints
- key facts/findings already established
- important entities (paper titles, arXiv IDs, authors)
- unresolved questions and next actions

Output 4-7 short bullet points.
Be faithful to the source, and do not add new facts.

Context window content:
{content[:3000]}
""".strip()
```

**Why `content[:3000]`?** At the point summarisation is triggered, the context may already be large. Truncating to 3,000 characters prevents the summarisation call itself from exceeding the model's token limit — you are compressing because the context is large, so you cannot afford to send all of it.

**What happens after the prompt:** The function makes two LLM calls — one to produce the bullet-point summary, and one to generate a short label (max 12 words) used as the summary's description in Oracle. The description is what appears in `read_summary_context` so the agent can decide whether to expand a summary without fetching its full content.
