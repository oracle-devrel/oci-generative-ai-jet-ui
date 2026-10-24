"""Claude: answers from recalled memories, and the tool runner the agent sections use."""
from __future__ import annotations

import os

import anthropic

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
ARGS = {"model": MODEL, "betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
client = anthropic.Anthropic() if os.getenv("ANTHROPIC_API_KEY") else None

ANSWER_SYSTEM = """You are the memory-backed assistant for a platform team whose projects are Cairn (agent platform),
Beacon (customer-support agent) and Comet (coding agent). You are answering {user}.
The recalled memories below are your entire knowledge. Answer only from them and cite memory IDs in square
brackets, like [mem_013]. If they do not contain the answer, say so plainly instead of guessing. If two of them
contradict each other, name both and do not pick one silently. Plain text, no markdown, three sentences at most."""

AGENT_SYSTEM = """You are the memory-backed assistant for a platform team (projects Cairn, Beacon and Comet).
You have long-term memory through tools. Recall before answering questions about the team's past decisions,
incidents, preferences or procedures, and cite memory IDs in square brackets. When the user tells you something
durable that makes a recalled memory wrong, correct that memory instead of storing a duplicate; when it is new,
remember it. Never claim to have stored or changed something unless a tool result says so.
Plain text, no markdown, be brief."""

NO_MEMORY_SYSTEM = """You are the assistant for a platform team (projects Cairn, Beacon and Comet). You have no memory
of earlier conversations and no tools. Plain text, no markdown, be brief."""

USERS = {"user_ada": "Ada", "user_bob": "Bob", "user_cy": "Cy"}


def text_of(response):
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined the request: {response.stop_details}")
    return " ".join(b.text for b in response.content if b.type == "text").strip()


def answer(question, memories, user=None):
    """Ask Claude one question, giving it exactly the memories the recall step returned."""
    recalled = (
        "\n".join(f"[{m['memory_id']}] {m['content']}" for m in memories)
        or "(no memories were recalled)"
    )
    response = client.beta.messages.create(
        **ARGS,
        max_tokens=2000,
        output_config={"effort": "low"},
        system=ANSWER_SYSTEM.format(user=USERS.get(user, "a member of the team")),
        messages=[
            {"role": "user", "content": f"Recalled memories:\n{recalled}\n\nQuestion: {question}"}
        ],
    )
    return text_of(response)


def answer_without_memory(question):
    response = client.beta.messages.create(
        **ARGS,
        max_tokens=2000,
        output_config={"effort": "low"},
        system=NO_MEMORY_SYSTEM,
        messages=[{"role": "user", "content": question}],
    )
    return text_of(response)


def run_tools(system, message, tools, effort="medium"):
    """One user turn through the SDK's tool runner: Claude calls tools until it can answer."""
    runner = client.beta.messages.tool_runner(
        **ARGS,
        max_tokens=8000,
        output_config={"effort": effort},
        system=system,
        tools=tools,
        messages=[{"role": "user", "content": message}],
    )
    *_, final = runner  # run the loop to the end; the last message is the answer
    return text_of(final)
