"""Agent turn: pull context, call Grok, run tool loop, persist turns."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from soccer_agent.agent.embeddings import embed_one
from soccer_agent.agent.grok_client import chat as grok_chat
from soccer_agent.agent.tools import TOOL_SCHEMAS, dispatch
from soccer_agent.memory.episodic import EpisodicMemory, Turn
from soccer_agent.memory.semantic import SemanticMemory
from soccer_agent.observability.langgraph_steps import (
    LangGraphObservabilityUnavailable,
    new_turn_id,
    record_step,
)


SYSTEM_PROMPT = (
    "You are a soccer analytics assistant. You can call tools to query the "
    "FIFA World Cup match database, look up ML predictions, and search "
    "semantic memory. Be concise. Cite the numbers you used.\n\n"
    "Database schema (Oracle AI Database, use exactly these names — `DATE` is reserved "
    "in Oracle so the date column is renamed `DATE_RW`):\n"
    "- MATCH_RESULTS(DATE_RW, HOME_TEAM, AWAY_TEAM, HOME_SCORE, AWAY_SCORE, "
    "TOURNAMENT, CITY, COUNTRY, NEUTRAL)\n"
    "- GOALSCORERS(DATE_RW, HOME_TEAM, AWAY_TEAM, TEAM, SCORER, MINUTE, "
    "OWN_GOAL, PENALTY)\n"
    "- SHOOTOUTS(DATE_RW, HOME_TEAM, AWAY_TEAM, WINNER)\n"
    "- WC2026_VENUES(CITY, COUNTRY, ALTITUDE_M, CAPACITY)\n"
    "- PREDICCIONES_FINAL(HOME_TEAM, AWAY_TEAM, PROB_HOME_WIN, PROB_DRAW, "
    "PROB_AWAY_WIN, MODEL_VERSION)\n"
    "- SOCCER_LANGCHAIN_DOCS(text, metadata, embedding) managed by "
    "langchain-oracledb for hybrid retrieval\n"
    "- Views: VW_COMPETITIVE_MATCHES, VW_TEAM_STATISTICS\n"
    "SQL rules: use `FETCH FIRST N ROWS ONLY` for limits (not LIMIT). "
    "When ordering by date, use `DATE_RW`, not `date`.\n"
    "For current or hypothetical match predictions, prefer `predict_match`; "
    "use `lookup_prediction` only when the user explicitly asks for a cached "
    "or precomputed prediction row. This agent is hybrid-first: for any "
    "explanatory answer, evidence comparison, model-rationale request, or "
    "final workshop chat, prefer `hybrid_retrieve` over raw `vector_search` "
    "because it queries the langchain-oracledb OracleVS vector store and "
    "combines vector similarity with keyword/text retrieval in Oracle. Use "
    "`vector_search` mainly when the user explicitly asks for the semantic-only "
    "baseline or when the hybrid store is unavailable."
)

MAX_TOOL_ITERATIONS = 6
LOGGER = logging.getLogger(__name__)


@dataclass
class AssistantReply:
    session_id: str
    text: str
    tool_trace: list[dict[str, Any]]


def _embed_one(text: str) -> np.ndarray:
    return embed_one(text)


def run_turn(session_id: str, user_message: str) -> AssistantReply:
    em = EpisodicMemory(session_id)
    sm = SemanticMemory()
    turn_id = new_turn_id()
    step_index = 0

    def observe(event_type: str, payload: dict[str, Any] | None = None,
                tool_name: str | None = None) -> None:
        nonlocal step_index
        try:
            record_step(
                session_id=session_id,
                turn_id=turn_id,
                step_index=step_index,
                event_type=event_type,
                payload=payload,
                tool_name=tool_name,
            )
        except LangGraphObservabilityUnavailable as exc:
            LOGGER.warning("Agent-step observability write skipped: %s", exc)
        finally:
            step_index += 1

    observe("turn_start", {"user_message": user_message})

    history = em.recent(limit=8)

    q_emb = _embed_one(user_message)
    grounding_label = "semantic memory"
    grounding = ""
    from soccer_agent.memory.langchain_hybrid import (
        LangChainOracleDBUnavailable,
        hybrid_search,
    )

    try:
        docs = hybrid_search(user_message, limit=5, search_mode="hybrid")
    except LangChainOracleDBUnavailable:
        docs = []

    if docs:
        grounding_label = "hybrid retrieval (LangChain OracleVS)"
        observe("grounding_retrieved", {
            "source": grounding_label,
            "document_count": len(docs),
            "doc_types": [d.metadata.get("doc_type", "doc") for d in docs],
            "retrieval_modes": [d.retrieval_mode for d in docs],
        })
        grounding = "\n".join(
            f"- ({d.metadata.get('doc_type', 'doc')}:{d.metadata.get('doc_id', 'unknown')}) "
            f"{d.page_content}"
            for d in docs
        )

    if not grounding:
        facts = sm.search(q_emb, limit=5)
        observe("grounding_retrieved", {
            "source": grounding_label,
            "fact_count": len(facts),
            "fact_types": [f.fact_type for f in facts],
        })
        grounding = "\n".join(
            f"- ({f.fact_type}:{f.subject_key}) {f.summary}" for f in facts
        ) or "(no relevant facts found)"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system",
         "content": f"Relevant context from {grounding_label}:\n{grounding}"},
    ]
    for t in history:
        # Skip "tool" role turns — OCI GenAI requires a toolCallId we don't track.
        # Tool results from prior turns aren't part of the cross-turn context anyway.
        if t.role == "tool":
            continue
        messages.append({"role": t.role, "content": t.content})
    messages.append({"role": "user", "content": user_message})

    em.append(Turn(role="user", content=user_message, embedding=q_emb))

    tool_trace: list[dict[str, Any]] = []
    for iteration in range(MAX_TOOL_ITERATIONS):
        reply = grok_chat(messages, TOOL_SCHEMAS)
        observe("model_response", {
            "iteration": iteration,
            "text_preview": reply.text[:500] if reply.text else "",
            "tool_call_count": len(reply.tool_calls),
            "tool_names": [call.get("name") for call in reply.tool_calls],
        })
        if not reply.tool_calls:
            r_emb = _embed_one(reply.text) if reply.text else np.zeros(384, dtype=np.float32)
            em.append(Turn(role="assistant", content=reply.text, embedding=r_emb))
            observe("final_response", {
                "text_preview": reply.text[:1000] if reply.text else "",
                "tool_count": len(tool_trace),
            })
            return AssistantReply(session_id=session_id, text=reply.text,
                                  tool_trace=tool_trace)

        # Record the model's tool-call turn so the next iteration sees it.
        if reply.text:
            messages.append({"role": "assistant", "content": reply.text})

        for call in reply.tool_calls:
            args = json.loads(call["arguments"]) if isinstance(call["arguments"], str) else call["arguments"]
            observe("tool_call", {
                "iteration": iteration,
                "args": args,
            }, tool_name=call["name"])
            result = dispatch(call["name"], args, session_id=session_id)
            observe("tool_result", {
                "iteration": iteration,
                "result": result,
            }, tool_name=call["name"])
            tool_trace.append({
                "name": call["name"], "args": args, "result": result,
            })
            em.append(Turn(
                role="tool", content=json.dumps(result, default=str)[:4000],
                embedding=np.zeros(384, dtype=np.float32),
                tool_name=call["name"], tool_args=args,
            ))
            # OCI GenAI's chat API doesn't accept role="tool" messages at this
            # endpoint (it demands a toolCallId we never received). Surface the
            # result back to the model as a system note instead.
            messages.append({
                "role": "system",
                "content": (
                    f"Tool result for {call['name']}({json.dumps(args, default=str)}):\n"
                    f"{json.dumps(result, default=str)[:4000]}\n"
                    "Use this to answer. If you still need more data, request "
                    "another tool call; otherwise reply with plain prose."
                ),
            })

    # Summarise what was gathered rather than dumping raw JSON.
    tools_used = ", ".join(t["name"] for t in tool_trace)
    final = (
        f"I reached my tool-call limit ({MAX_TOOL_ITERATIONS} iterations) while working "
        f"on your question. I called: {tools_used}. "
        "The last tool result is available in the trace below. "
        "Try rephrasing your question to narrow the scope, or ask about one team or matchup at a time."
    )
    em.append(Turn(role="assistant", content=final,
                   embedding=np.zeros(384, dtype=np.float32)))
    observe("tool_budget_exhausted", {"tool_count": len(tool_trace), "tools_used": tools_used})
    return AssistantReply(session_id=session_id, text=final, tool_trace=tool_trace)
