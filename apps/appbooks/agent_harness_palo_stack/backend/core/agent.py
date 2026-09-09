"""The agent loop: assemble grounded context (semantic catalog + skill manifest +
OAMP context card), select top-k tools from the registry, run a tool-use loop, and
stream every step (context, tool_call, tool_result, answer) over SSE."""
from __future__ import annotations

import asyncio
import json

from backend.config import settings
from backend.core import db, memory, registries
from backend.core.anthropic_client import client, text_of

SYSTEM = (
    "You are a retail-analytics agent. Ground yourself in the schema catalog before writing SQL. "
    "Reuse proven workflows and skills. Prefer create_automation to make a result recurring. "
    "Use only the provided tools, and answer concisely."
)

_JSON_TYPE = {"string": "string", "number": "number", "integer": "integer", "boolean": "boolean"}
ESSENTIAL = [
    "run_sql",
    "list_sources",
    "create_automation",
    "search_memory",
    "recall_workflow",
    "find_skill",
    "load_skill",
]


def _select_tool_names(query, k=8):
    names = [r["NAME"] for r in registries.retrieve_tools(query, k)]
    return [n for n in dict.fromkeys(names + ESSENTIAL) if n in registries.TOOLS]


def _anthropic_tools(names):
    tools = []
    for n in names:
        sch = registries.get_tool_schema(n)
        if not sch:
            continue
        props = {
            p: {"type": _JSON_TYPE.get(t, "string")}
            for p, t in (sch.get("parameters") or {}).items()
        }
        tools.append(
            {
                "name": n,
                "description": sch.get("description", ""),
                "input_schema": {
                    "type": "object",
                    "properties": props,
                    "required": list(props.keys()),
                },
            }
        )
    return tools


async def run_agent(prompt: str, thread_id: str = "appbook"):
    await asyncio.to_thread(memory.add_turn, thread_id, "user", prompt)

    catalog = await asyncio.to_thread(db.semantic_search, prompt, 5)
    manifest = await asyncio.to_thread(registries.build_skill_manifest, prompt, 4)
    card = await asyncio.to_thread(memory.context_card, thread_id) or ""
    recipes = await asyncio.to_thread(memory.recall_workflow, prompt, 3)
    recipe_lines = [f"{r['INTENT']} (x{r['OCCURRENCES']})" for r in (recipes or [])]
    tool_names = await asyncio.to_thread(_select_tool_names, prompt)
    tools = await asyncio.to_thread(_anthropic_tools, tool_names)

    system = (
        f"{SYSTEM}\n\n# SCHEMA CATALOG\n"
        + "\n".join(str(c["CONTENT"]) for c in catalog)
        + f"\n\n# SKILLS (manifest)\n{manifest}"
        + (("\n\n# PROVEN RECIPES\n" + "\n".join(recipe_lines)) if recipe_lines else "")
        + f"\n\n# WORKING MEMORY (context card)\n{card}"
    )

    yield {
        "type": "context",
        "catalog": [str(c["CONTENT"])[:90] for c in catalog],
        "skills": manifest,
        "recipes": recipe_lines,
        "tools": tool_names,
        "card": (card or "")[:1200],
        "est_tokens": len(system) // 4,
        "system_chars": len(system),
    }
    messages = [{"role": "user", "content": prompt}]
    used = []

    for _ in range(10):
        resp = await asyncio.to_thread(
            client.messages.create,
            model=settings.model,
            max_tokens=settings.max_tokens,
            system=system,
            tools=tools,
            messages=messages,
        )
        blocks = resp.content
        tool_uses = [b for b in blocks if getattr(b, "type", None) == "tool_use"]
        text = text_of(resp)
        if text.strip():
            yield {"type": "delta", "text": text}
        if resp.stop_reason != "tool_use" or not tool_uses:
            break
        messages.append({"role": "assistant", "content": [b.model_dump() for b in blocks]})
        results = []
        for tu in tool_uses:
            used.append(tu.name)
            yield {"type": "tool_call", "name": tu.name, "args": tu.input}
            try:
                out = await asyncio.to_thread(registries.TOOLS[tu.name], **(tu.input or {}))
            except Exception as e:
                out = {"error": str(e)}
            payload = json.dumps(out, default=str)
            yield {"type": "tool_result", "name": tu.name, "preview": payload[:600]}
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": payload[:6000]})
        messages.append({"role": "user", "content": results})
    else:
        # Reached the tool-iteration budget without a natural finish — force one clean
        # synthesis call (no tools) so the user always gets a final answer, not just the
        # intermediate thinking. messages already ends with the latest tool results.
        resp = await asyncio.to_thread(
            client.messages.create,
            model=settings.model,
            max_tokens=settings.max_tokens,
            system=system,
            messages=messages,
        )
        ftext = text_of(resp)
        if ftext.strip():
            yield {"type": "delta", "text": ftext}

    # persist the final answer + capture the workflow (what the agent did this turn)
    answer = text_of(resp) or next(
        (b.text for b in resp.content if getattr(b, "type", None) == "text"), ""
    )
    if answer:
        await asyncio.to_thread(memory.add_turn, thread_id, "assistant", answer)
    if used:
        await asyncio.to_thread(
            memory.capture_workflow, prompt, [{"tool": t} for t in used], list(dict.fromkeys(used))
        )
    yield {"type": "done", "tools_used": used}
