"""Tools for the two specialist agents.

Mirrors the notebook's tools 1-to-1 so the workshop and the app use the
same retrieval surfaces.
"""

from __future__ import annotations

from app.backend.config import ONNX_EMBED_DIM, ONNX_EMBED_MODEL, STORE_SUFFIX, VS_TABLE
from app.backend.db.connections import store_connection, sync_client
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.tools import tool
from langchain_oracledb import OracleEmbeddings, OracleVS
from langgraph_oracledb.store.oracle import AsyncOracleStore

# ─── Process-level singletons ─────────────────────────────────────────────
_oracle_vs: OracleVS | None = None
_agent_store: AsyncOracleStore | None = None


def get_oracle_vs() -> OracleVS:
    """Return the shared OracleVS handle."""
    global _oracle_vs
    if _oracle_vs is None:
        client = sync_client()
        embeddings = OracleEmbeddings(
            conn=client,
            params={"provider": "database", "model": ONNX_EMBED_MODEL},
        )
        _oracle_vs = OracleVS(
            client=client,
            embedding_function=embeddings,
            table_name=VS_TABLE,
            distance_strategy=DistanceStrategy.COSINE,
        )
    return _oracle_vs


async def get_agent_store() -> AsyncOracleStore:
    """Return the shared AsyncOracleStore handle (setup runs once)."""
    global _agent_store
    if _agent_store is None:
        conn = await store_connection()
        # Note: the long-term store uses the same in-DB embedder, but it
        # needs its own connection because OracleEmbeddings is sync-only.
        # We let it reuse the sync client for embedding work.
        embeddings = OracleEmbeddings(
            conn=sync_client(),
            params={"provider": "database", "model": ONNX_EMBED_MODEL},
        )
        _agent_store = AsyncOracleStore(
            conn,
            index={
                "dims": ONNX_EMBED_DIM,
                "embed": embeddings,
                "fields": ["note"],
                "index_type": {"type": "hnsw", "distance_metric": "COSINE"},
            },
            table_suffix=STORE_SUFFIX,
        )
        await _agent_store.setup()
    return _agent_store


# ─── demand_analyst tools ─────────────────────────────────────────────────
@tool
def search_demand_reports(query: str) -> str:
    """Search historical product demand reports by semantic similarity.

    Use natural-language queries. Returns the top-5 matches as a joined string.
    """
    vs = get_oracle_vs()
    docs = vs.similarity_search(query, k=5)
    if not docs:
        return "No matches."
    return "\n\n---\n\n".join(d.page_content for d in docs)


# ─── policy_agent tools ───────────────────────────────────────────────────
@tool
def get_planner_policy() -> str:
    """Fetch the standing planner-prefs buy-volume policy from OracleVS."""
    vs = get_oracle_vs()
    docs = vs.similarity_search("planner buy volume policy", k=1)
    return docs[0].page_content if docs else "No policy on file."


@tool
async def get_user_memory(user_id: str) -> str:
    """Look up long-term saved preferences for a planner by their user_id."""
    store = await get_agent_store()
    items = await store.asearch(
        ("users", user_id, "memories"),
        query="preference",
        limit=3,
    )
    if not items:
        return f"No saved memories for user_id={user_id}."
    return "\n".join(f"- {it.value.get('note', '')}" for it in items)
