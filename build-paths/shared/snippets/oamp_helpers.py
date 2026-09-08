"""OracleAgentMemory (OAMP) helpers — wires the PyPI package into the
build-paths advanced tier with our in-DB ONNX embedder + Grok-4 LLM.

WHY THIS EXISTS
---------------
OAMP (https://pypi.org/project/oracleagentmemory/) ships the conversational +
durable per-user memory primitives we kept hand-rolling at the advanced tier:
threads, message logs, automatic memory extraction, prompt-ready context
cards, schema management. The advanced cold-start walks all converged on
"reinvent these primitives in 200 LOC". This module is the canonical wiring so
that doesn't keep happening (advanced retrofit, friction P3-V3-OAMP-1).

WHAT OAMP OWNS vs WHAT IT DOES NOT
----------------------------------
OAMP owns:
  * thread = (user_id, agent_id) conversation
  * per-user durable memory (`add_memory`, `search`, scoped by user + agent)
  * automatic LLM-driven extraction of durable facts from recent messages
  * prompt-ready context cards (`thread.get_context_card()`)
  * its own schema (auto-created via `schema_policy="create_if_necessary"`)

OAMP does NOT own (keep these as project code):
  * fixed RAG corpora — runbooks, glossary, decision docs.
    Use `OracleVS` multi-collection (`store.py` from langchain-oracledb-helper).
  * structured DDL audit / tool-success counters.
    Use plain SQL tables (idea 2's `TOOL_REGISTRY`, idea 3's `DESIGN_HISTORY`).
  * tool execution telemetry as a vector store.
    Use `OracleVS` over a project-defined collection (idea 2's `TOOL_RUNS`).

The decision tree lives in `shared/references/oamp.md`.

EMBEDDER WIRING — IN-DB ONNX
----------------------------
OAMP's bundled `Embedder` ships OpenAI / Cohere / SentenceTransformers paths.
The advanced tier embeds inside Oracle via the registered `MY_MINILM_V1` ONNX
model (384 dim) for parity with `OracleVS`. We provide that by implementing
OAMP's `IEmbedder` interface — a 30-line shim that runs the same
`VECTOR_EMBEDDING(MY_MINILM_V1 USING :t AS data) FROM dual` query
`shared/snippets/in_db_embeddings.py` already uses for LangChain.

LLM WIRING — GROK-4 OVER OCI BEARER-TOKEN
-----------------------------------------
OAMP's bundled `Llm` is a thin LiteLLM/OpenAI wrapper. The CYP canonical chat
recipe is `xai.grok-4` against the OCI OpenAI-compat endpoint at
`us-phoenix-1` with `OCI_GENAI_API_KEY` (no `~/.oci/config`). We implement
OAMP's `ILlm` directly using `shared/snippets/oci_chat_factory.chat_complete`
so OAMP's auto-extraction runs against Grok via the same client the rest of
the project uses.

If `OCI_GENAI_API_KEY` is not set, `make_oamp_client` returns a client with
`extract_memories=False` (still useful — manual `add_memory` / threads /
context cards all work, just no LLM-driven fact extraction).

USAGE
-----
    from <package_slug>.store import get_connection
    from shared.snippets.oamp_helpers import make_oamp_client, make_oamp_thread
    from oracleagentmemory.apis.thread import Message

    conn = get_connection()
    client = make_oamp_client(conn)                      # in-DB ONNX + Grok-4
    client.add_user(USER_ID, "Alice — EU growth lead.")
    client.add_agent(AGENT_ID, "Hybrid analyst v1.")

    thread = make_oamp_thread(client, USER_ID, AGENT_ID)
    # IMPORTANT: one add_messages() call per turn — see V4-OAMP-1 in
    # shared/references/oamp.md. Batching messages into one call works for the
    # context-summary path but never triggers memory extraction.
    add_turn(thread, "user",      "Q3 EU revenue?")
    add_turn(thread, "assistant", "$4.2M, up 18% YoY.")
    card = thread.get_context_card()                     # prompt-ready

    # Cold→warm recovery on a fresh process:
    saved_id = thread.thread_id
    fresh_client = make_oamp_client(conn)
    recovered = fresh_client.get_thread(saved_id)        # same conversation
"""

from __future__ import annotations

import os
from typing import Any, Sequence

import numpy as np
import oracledb


# --- Embedder: in-DB ONNX (MY_MINILM_V1, 384 dim) ----------------------------
#
# Mirrors `shared/snippets/in_db_embeddings.py` but adapts to OAMP's
# `IEmbedder` interface (returns `np.ndarray`, supports `is_query` hint).
def _make_in_db_embedder(conn: oracledb.Connection, model_db_name: str = "MY_MINILM_V1"):
    """Return an OAMP IEmbedder backed by Oracle's VECTOR_EMBEDDING."""
    from oracleagentmemory.apis.embedders.embedder import IEmbedder

    class _InDBOAMPEmbedder(IEmbedder):
        def __init__(self, _conn, _model):
            self._conn = _conn
            self._model = _model

        def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
            # is_query is a hint; the in-DB ONNX model produces the same
            # embedding either way. Kept for IEmbedder contract.
            del is_query
            vectors: list[list[float]] = []
            with self._conn.cursor() as cur:
                for text in texts:
                    cur.execute(
                        f"SELECT VECTOR_EMBEDDING({self._model} USING :t AS data) "
                        f"FROM dual",
                        t=text,
                    )
                    (vec,) = cur.fetchone()
                    if hasattr(vec, "tolist"):
                        vectors.append(list(vec.tolist()))
                    elif isinstance(vec, (bytes, bytearray, str)):
                        import json as _json

                        vectors.append(_json.loads(
                            vec.decode("utf-8") if isinstance(vec, (bytes, bytearray)) else vec
                        ))
                    else:
                        vectors.append(list(vec))
            return np.asarray(vectors, dtype=np.float32)

        async def embed_async(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
            import asyncio

            return await asyncio.to_thread(self.embed, texts, is_query=is_query)

    return _InDBOAMPEmbedder(conn, model_db_name)


# --- LLM: Grok-4 over OCI OpenAI-compat (bearer-token) -----------------------
#
# OAMP's bundled Llm hard-codes LiteLLM/OpenAI. We subclass ILlm directly so
# auto-extraction runs against the same Grok client the rest of the project
# uses (oci_chat_factory.chat_complete).
def _make_grok_llm():
    """Return an OAMP ILlm backed by `oci_chat_factory.chat_complete`."""
    from oracleagentmemory.apis.llms.llm import ILlm, LlmResponse

    # Local import: keeps the snippet usable when oci_chat_factory.py was
    # copied into the project as <pkg>/inference.py instead.
    try:
        from .oci_chat_factory import chat_complete  # type: ignore
    except ImportError:  # pragma: no cover — fallback for project-local copy
        from shared.snippets.oci_chat_factory import chat_complete  # type: ignore

    class _GrokOAMPLlm(ILlm):
        def __init__(self, temperature: float = 0.2, max_tokens: int = 1500):
            # max_tokens=1500 mirrors the planner-loop minimum from advanced
            # SKILL Step 3b idea 2 (friction v2-F-v2-1) — auto-extraction
            # JSON envelopes truncate at lower budgets.
            self.temperature = temperature
            self.max_tokens = max_tokens

        def generate(
            self,
            prompt: str | Sequence[dict[str, str]],
            *,
            response_json_schema: dict[str, Any] | None = None,
            **kwargs: Any,
        ) -> LlmResponse:
            del response_json_schema  # OAMP requests JSON via prompt; Grok complies.
            messages = (
                [{"role": "user", "content": prompt}]
                if isinstance(prompt, str)
                else list(prompt)
            )
            text = chat_complete(
                messages,
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
            )
            return LlmResponse(text=text)

    return _GrokOAMPLlm()


# --- Public API ---------------------------------------------------------------

def make_oamp_client(
    conn: oracledb.Connection,
    *,
    in_db_model: str = "MY_MINILM_V1",
):
    """Construct an `OracleAgentMemory` client wired for the CYP advanced tier.

    Defaults:
      * embedder = in-DB ONNX (MY_MINILM_V1, 384 dim) — same model `OracleVS`
        uses, so OAMP and your fixed-corpus collections share an embedder.
      * llm = Grok-4 over OCI bearer-token IFF `OCI_GENAI_API_KEY` is set.
        Without that env var, `extract_memories=False` and no LLM is attached
        (manual `add_memory` / threads / context cards still work).
      * schema_policy = "create_if_necessary" — OAMP creates its own tables
        on first connect. They coexist with your project's OracleVS tables in
        the same Oracle schema; OAMP names are prefixed `OAM_*` to avoid
        collisions. See `shared/references/oamp.md` for the full table list.
    """
    from oracleagentmemory.core import OracleAgentMemory

    embedder = _make_in_db_embedder(conn, model_db_name=in_db_model)

    if os.environ.get("OCI_GENAI_API_KEY"):
        return OracleAgentMemory(
            connection=conn,
            embedder=embedder,
            llm=_make_grok_llm(),
            extract_memories=True,
            schema_policy="create_if_necessary",
        )

    # No LLM available — keep the client useful, just without auto-extraction.
    return OracleAgentMemory(
        connection=conn,
        embedder=embedder,
        extract_memories=False,
        schema_policy="create_if_necessary",
    )


def make_oamp_thread(
    client,
    user_id: str,
    agent_id: str,
    *,
    summary: bool = True,
):
    """Create a thread with the recommended advanced-tier defaults.

    These defaults track the OCI developer-guide notebook
    (`notebooks/agent_memory/oracle_agent_memory_developer_guide_oci.ipynb`):

      memory_extraction_frequency=2   # extract every 2 user turns
      memory_extraction_window=4      # over the last 4 messages
      enable_context_summary=True     # on by default; idempotent
      context_summary_update_frequency=2

    Pass `summary=False` to skip the running summary (cheaper, but the context
    card will only reflect retrieved memories, not a rolling synopsis).
    """
    return client.create_thread(
        user_id=user_id,
        agent_id=agent_id,
        memory_extraction_frequency=2,
        memory_extraction_window=4,
        enable_context_summary=summary,
        context_summary_update_frequency=2,
    )


def add_turn(thread, role: str, content: str):
    """Append one message to an OAMP thread.

    Use this instead of calling `thread.add_messages([...])` with multiple
    messages. OAMP's auto-extraction counts `add_messages()` calls (not
    Message rows), so a batched call of N messages registers as one event
    and never trips `memory_extraction_frequency`. Calling once per turn
    keeps extraction firing on schedule and gives each message a distinct
    timestamp. See V4-OAMP-1 / V4-OAMP-3 in shared/references/oamp.md.
    """
    from oracleagentmemory.apis.thread import Message

    thread.add_messages([Message(role=role, content=content)])
