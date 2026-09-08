"""OAMP-backed memory layer. Mirrors §4.1 of the notebook: the OracleAgentMemory
client owns memories/threads/context-cards; we add a custom in-DB ONNX embedder.

The whole agent reads/writes memory through this module so the API surface is
small and stable.
"""

from __future__ import annotations

import numpy as np

import os

from oracleagentmemory.core import OracleAgentMemory
from oracleagentmemory.core.llms import Llm
from oracleagentmemory.apis.embedders.embedder import IEmbedder

from config import (
    AGENT_ID, USER_ID,
    LLM_FALLBACK_MODEL, LLM_MODEL, LLM_PROVIDER,
    OCI_GENAI_API_KEY, OCI_GENAI_ENDPOINT,
    ONNX_EMBED_DIM, ONNX_EMBED_MODEL,
    OPENAI_API_KEY,
)


class OracleONNXEmbedder(IEmbedder):
    """Routes embedding through Oracle's in-DB ONNX model (§3.4 of the notebook).
    Same connection the OAMP client uses → no network round-trip, no extra keys.
    """

    def __init__(self, conn, model_name: str = ONNX_EMBED_MODEL, dim: int = ONNX_EMBED_DIM):
        self._conn = conn
        self._model = model_name
        self._dim = dim

    def embed(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        out = np.zeros((len(texts), self._dim), dtype=np.float32)
        sql = f"SELECT VECTOR_EMBEDDING({self._model} USING :t AS DATA) FROM dual"
        with self._conn.cursor() as cur:
            for i, t in enumerate(texts):
                cur.execute(sql, t=t)
                vec = cur.fetchone()[0]
                out[i] = np.asarray(list(vec), dtype=np.float32)
        return out

    async def embed_async(self, texts: list[str], *, is_query: bool = False) -> np.ndarray:
        return self.embed(texts, is_query=is_query)


def build_extraction_llm():
    """LLM used by OAMP for memory extraction + context-summary refresh.

    Mirrors agent/llm.py's OCI-first / OpenAI-fallback policy: try OCI when
    LLM_PROVIDER=oci and credentials are present, otherwise (or on init
    failure) build an OpenAI client on `LLM_FALLBACK_MODEL` (gpt-5.5).
    Returns None if neither is available — caller disables extraction.
    """
    if LLM_PROVIDER == "oci" and OCI_GENAI_API_KEY and OCI_GENAI_ENDPOINT:
        try:
            llm = Llm(
                f"openai/{LLM_MODEL}",
                api_base=OCI_GENAI_ENDPOINT,
                api_key=OCI_GENAI_API_KEY,
            )
            print(f"[memory] OAMP extraction LLM = OCI {LLM_MODEL} @ {OCI_GENAI_ENDPOINT}")
            return llm
        except Exception as e:
            print(f"[memory] OCI extraction LLM init failed: "
                  f"{type(e).__name__}: {e}; falling back to OpenAI {LLM_FALLBACK_MODEL}.")

    if OPENAI_API_KEY:
        # litellm reads OPENAI_API_KEY from os.environ. Make sure it's set
        # even if the .env loader stashed it only on os.environ via dotenv.
        os.environ.setdefault("OPENAI_API_KEY", OPENAI_API_KEY)
        print(f"[memory] OAMP extraction LLM = OpenAI {LLM_FALLBACK_MODEL}")
        return Llm(LLM_FALLBACK_MODEL)

    print("[memory] No usable LLM credentials — OAMP extraction DISABLED.")
    return None


def build_memory_client(agent_conn) -> OracleAgentMemory:
    """The single OAMP client used by the loop and the API.

    If no LLM is available we still build the client (for memory storage and
    semantic retrieval), but disable auto-extraction so OAMP doesn't hit a
    None LLM during add_messages.
    """
    extraction_llm = build_extraction_llm()
    client = OracleAgentMemory(
        connection=agent_conn,
        embedder=OracleONNXEmbedder(agent_conn),
        llm=extraction_llm,
        extract_memories=(extraction_llm is not None),
        schema_policy="create_if_necessary",
        table_name_prefix="eda_onnx_",
    )
    for register_fn, eid, info in [
        (client.add_user, USER_ID, "Operator querying the enterprise database in natural language."),
        (client.add_agent, AGENT_ID, "Data agent grounded in scanned schema metadata."),
    ]:
        try:
            register_fn(eid, info)
        except ValueError as e:
            if "already exists" not in str(e):
                raise
    return client


def get_or_create_thread(client: OracleAgentMemory, thread_id: str):
    """Return the OAMP thread for a harness-level id, creating it on first use."""
    try:
        return client.get_thread(thread_id)
    except Exception:
        return client.create_thread(
            thread_id=thread_id,
            user_id=USER_ID,
            agent_id=AGENT_ID,
            enable_context_summary=True,
        )
