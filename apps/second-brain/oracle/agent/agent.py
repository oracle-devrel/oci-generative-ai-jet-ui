"""The agent loop — Claude drafts a hook, tests it, and remembers the outcome.

Manual agentic loop (not the auto tool-runner) on purpose: we read memory BEFORE
the model acts and write memory AFTER each tool call. That read/write around the
step is the demo.
"""
import anthropic

from memory import record, recall
from tools import score_hook, lesson_for

MODEL = "claude-opus-4-8"

SYSTEM = (
    "You are a content strategist for a creator's business. For the given topic, "
    "write ONE short hook (the first line of a social post), then call publish_hook "
    "to test it. If past lessons are provided, use them to write a better hook. "
    "Call publish_hook exactly once."
)

PUBLISH_TOOL = {
    "name": "publish_hook",
    "description": "Publish a hook to test it and get an engagement score (0..1). "
                   "Call exactly once, with your single best hook.",
    "input_schema": {
        "type": "object",
        "properties": {
            "hook":  {"type": "string", "description": "The hook line."},
            "style": {"type": "string", "description": "A short label for the approach you used."},
        },
        "required": ["hook", "style"],
    },
}


def _format_lessons(memories):
    if not memories:
        return ""
    lines = []
    for m in memories:
        lines.append(f"- {m['outcome']} ({m.get('detail') or ''}) — hook was: {m['action']}")
    return "\n".join(lines)


def run_task(client, conn, run_id, topic):
    """Run one task end-to-end; returns the engagement score achieved."""
    task = f"Write a high-engagement hook about: {topic}"

    # 1) RECALL relevant past experience BEFORE acting.
    memories = recall(conn, task, k=5)
    lessons = _format_lessons(memories)
    print(f"  recalled {len(memories)} past experience(s)")

    user = task + (
        f"\n\nLessons from past attempts (learn from these):\n{lessons}"
        if lessons else "\n\n(No past experience yet — this is your first attempt.)"
    )
    messages = [{"role": "user", "content": user}]

    final_score = None
    while True:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            thinking={"type": "adaptive"},
            system=SYSTEM,
            tools=[PUBLISH_TOOL],
            messages=messages,
        )
        if resp.stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if block.type == "tool_use" and block.name == "publish_hook":
                hook = block.input["hook"]
                style = block.input.get("style", "")
                score = score_hook(hook)
                final_score = score
                detail = lesson_for(hook, score)
                outcome = "success" if score >= 0.7 else "failure"

                # 2) WRITE the experience to memory (embedded in-DB).
                record(conn, run_id, task, f"[{style}] {hook}",
                       "publish_hook", outcome, reward=score, detail=detail)
                print(f"  hook: {hook!r}  ->  score {score} ({outcome})")

                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"Engagement score: {score}. Notes: {detail}.",
                })
        messages.append({"role": "user", "content": results})

    return final_score
