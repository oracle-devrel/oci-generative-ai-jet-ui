"""Context policy, adapter identifiers, and transient tool-result helpers."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from copy import deepcopy
from datetime import datetime

AS_OF = datetime(2026, 9, 28, 12)
TABLES = {"guideline":"GUIDELINE_MEMORY","persona":"PERSONA_MEMORY","tool":"TOOLBOX_MEMORY","entity":"ENTITY_MEMORY","workflow":"WORKFLOW_MEMORY","summary":"SUMMARIZATION_MEMORY","conversation":"CONVERSATION_MEMORY","kb":"KNOWLEDGE_BASE_CHUNK","compression":"CONTEXT_COMPRESSION"}
SCOPE = {"tenant_id":"acme","user_id":"user:jane@acme.com","agent_id":"agent:research_v1","thread_id":"thread_demo"}
QUESTION = "For the retrieval side, is Helios-RAG still the one to beat? You told us it scored 0.92 on BEIR."
QUESTION_1 = "What did the Letta paper say about memory eviction, and how does that compare to what the AgentCore docs recommend?"
BUDGET = {
    "usable_context": 5000,
    "output_reserve": 400,
    "tool_reserve": 1000,
    "request_overhead_reserve": 500,
    "max_rounds": 3,
    "max_tool_result_tokens": 1000,
    "weights": {"rerank": 0.60, "confidence": 0.25, "recency": 0.15},
    "recency_days": 60,
    "shares": {
        "fact_check": {
            "durable_facts": 0.40,
            "evidence": 0.25,
            "recalled_history": 0.10,
            "volatile_tail": 0.25,
        },
        "comparison": {
            "durable_facts": 0.15,
            "evidence": 0.60,
            "recalled_history": 0.05,
            "volatile_tail": 0.20,
        },
    },
    "overflow_order": ["evidence", "durable_facts", "volatile_tail", "recalled_history"],
}


def dumps(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,default=lambda x: (int(x) if x==int(x) else float(x)) if isinstance(x,Decimal) else x.isoformat())


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def schema(properties, required=None):
    return {
        "type": "object",
        "properties": properties,
        "required": required or list(properties),
        "additionalProperties": False,
    }


TOOLS = [
    (
        "search_memory",
        "Search accessible memory.",
        schema({"query": {"type": "string", "minLength": 1, "maxLength": 500}}),
    ),
    (
        "lookup_entity",
        "Read the current canonical fact and labeled history for a named entity.",
        schema(
            {
                "subject": {
                    "type": "string",
                    # The example uses the existing canonical identifier. A production registry must
                    # expose scoped identifiers or resolve names before exact lookup.
                    "enum": ["model:helios-rag"],
                    "description": "Canonical entity name, not a memory row ID.",
                },
                "predicate": {
                    "type": "string",
                    "enum": ["beir_ndcg10"],
                    "description": "Canonical field key. beir_ndcg10 includes the benchmark name and metric in its result.",
                },
            }
        ),
    ),
    (
        "expand",
        "Expand a pointer issued in the current window.",
        schema({"memory_id": {"type": "string"}}),
    ),
    (
        "clarify",
        "Ask which retrieval workload the user means.",
        schema({"question": {"type": "string", "maxLength": 300}}),
    ),
]


def row(kind, id, content, **kw):
    base = {
        "kind": kind,
        "id": id,
        "tenant_id": "acme",
        "user_id": None,
        "agent_id": None,
        "thread_id": None,
        "version": 1,
        "valid_from": datetime(2026, 7, 1),
        "valid_until": None,
        "deleted_at": None,
        "content": content,
        "content_hash": digest(" ".join(content.split())),
        "source_event_id": "seed-" + id,
        "rerank": 0.0,
        "confidence": 1.0,
        "slice": "durable_facts",
        "claim_key": None,
        "meta": {},
    }
    base.update(kw)
    return base


