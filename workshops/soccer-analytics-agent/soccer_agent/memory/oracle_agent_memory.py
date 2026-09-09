"""Optional Oracle Agent Memory SDK showcase.

The workshop already has bespoke working/episodic/semantic memory tables.  This
module demonstrates how the same Oracle database can also host the
``oracleagentmemory`` PyPI package for durable agent memory.  Imports are lazy so
normal workshop runs do not fail when the alpha SDK is not installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from soccer_agent.agent.embeddings import embed_many
from soccer_agent.db import get_connection


class OracleAgentMemoryUnavailable(RuntimeError):
    """Raised when ``oracleagentmemory`` is not installed or its API changed."""


class OracleDatabaseEmbedder:
    """Small adapter exposing DB-side ONNX embeddings to oracleagentmemory.

    ``oracleagentmemory`` expects an embedder-like object with an ``embed``
    method returning a 2D ``numpy.ndarray``. We route that call to the workshop's
    existing in-database ``VECTOR_EMBEDDING`` model, so the demo still avoids
    external embedding APIs. Extra LangChain-style method names make the adapter
    tolerant of SDK changes.
    """

    model = os.environ.get("ORACLE_EMBED_MODEL", "ALL_MINILM_L6_V2")

    def embed(self, texts: str | Iterable[str], *, is_query: bool = False) -> np.ndarray:
        del is_query
        if isinstance(texts, str):
            payload = [texts]
        else:
            payload = [str(t) for t in texts]
        return embed_many(payload)

    async def embed_async(
        self,
        texts: str | Iterable[str],
        *,
        is_query: bool = False,
    ) -> np.ndarray:
        return self.embed(texts, is_query=is_query)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed(texts).astype(float).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text], is_query=True)[0].astype(float).tolist()


@dataclass(frozen=True)
class AgentMemoryDemoResult:
    thread_id: str
    stored_memory: str
    retrieved: list[str]
    warnings: list[str]


def _imports() -> dict[str, Any]:
    try:
        try:
            from oracleagentmemory.core import OracleAgentMemory, SchemaPolicy
        except ImportError:
            from oracleagentmemory.core import SchemaPolicy
            from oracleagentmemory.core.oracleagentmemory import OracleAgentMemory
        from oracleagentmemory.apis.searchscope import SearchScope
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional install state
        raise OracleAgentMemoryUnavailable(
            "Install oracleagentmemory to run this optional showcase: "
            "`uv add oracleagentmemory` or `pip install oracleagentmemory`."
        ) from exc
    except ImportError as exc:  # pragma: no cover - SDK import paths may change
        raise OracleAgentMemoryUnavailable(f"oracleagentmemory import failed: {exc}") from exc

    return {
        "OracleAgentMemory": OracleAgentMemory,
        "SchemaPolicy": SchemaPolicy,
        "SearchScope": SearchScope,
    }


def create_memory_client(conn: Any, *, table_name_prefix: str = "SOCCER_OAM_") -> Any:
    """Create an OracleAgentMemory client using this repo's Oracle connection."""
    imports = _imports()
    kwargs: dict[str, Any] = {
        "connection": conn,
        "embedder": OracleDatabaseEmbedder(),
        "extract_memories": False,
    }
    schema_policy = getattr(imports["SchemaPolicy"], "CREATE_IF_NECESSARY", None)
    if schema_policy is not None:
        kwargs["schema_policy"] = schema_policy
    kwargs["table_name_prefix"] = table_name_prefix
    try:
        return imports["OracleAgentMemory"](**kwargs)
    except TypeError:
        # Older/pre-release builds may not expose schema_policy/table_name_prefix.
        kwargs.pop("schema_policy", None)
        kwargs.pop("table_name_prefix", None)
        return imports["OracleAgentMemory"](**kwargs)


def _create_thread(memory: Any, *, thread_id: str, user_id: str, agent_id: str) -> Any:
    try:
        return memory.create_thread(
            thread_id=thread_id,
            user_id=user_id,
            agent_id=agent_id,
            extract_memories=False,
        )
    except TypeError:
        return memory.create_thread(thread_id=thread_id, user_id=user_id, agent_id=agent_id)


def run_demo(
    *,
    thread_id: str = "soccer-agent-memory-demo",
    user_id: str = "workshop-user",
    agent_id: str = "soccer-agent",
) -> AgentMemoryDemoResult:
    """Store and retrieve one durable soccer preference through oracleagentmemory."""
    imports = _imports()
    stored = (
        "The workshop user is evaluating Spain versus Brazil and wants answers "
        "that combine XGBoost match probabilities with football evidence."
    )
    messages = [
        {
            "role": "user",
            "content": "Remember that I care about Spain vs Brazil model evidence.",
        },
        {
            "role": "assistant",
            "content": "I will ground Spain vs Brazil answers in predictions and retrieved facts.",
        },
    ]

    warnings: list[str] = []
    with get_connection() as conn:
        memory = create_memory_client(conn)
        thread = _create_thread(memory, thread_id=thread_id, user_id=user_id, agent_id=agent_id)
        try:
            thread.add_messages(messages)
        except Exception as exc:
            # Message indexing is nice-to-have; manual durable memory is the core demo.
            warnings.append(f"thread.add_messages skipped: {exc.__class__.__name__}: {exc}")
        thread.add_memory(stored)

        try:
            scope = imports["SearchScope"](user_id=user_id, agent_id=agent_id)
            results = memory.search(
                query="Spain Brazil model evidence",
                scope=scope,
                max_results=3,
            )
        except TypeError:
            results = thread.search("Spain Brazil model evidence", max_results=3)

    retrieved = [str(getattr(item, "content", item)) for item in results]
    return AgentMemoryDemoResult(
        thread_id=thread_id,
        stored_memory=stored,
        retrieved=retrieved,
        warnings=warnings,
    )
