"""Agent memory store: Oracle's AI Agent Memory package, its schema, and the model a configuration names.

Facts are `fact` records in the package (specs/010-agent-memory, research R1), scoped by repository name. The
package is imported only where facts are touched, never on the recording path.
"""

import logging
from collections.abc import Mapping

from golestan_code_mcp.config import environment, memory_model
from golestan_code_mcp.search import model as search_model

AGENT = "ccctx"
STORE_ID = "CCCTX_MEM"  # the package's tables are named CCCTX_MEM_*

MAX_INPUT_TOKENS = 128  # the ONNX model's input window; the package cannot infer it

log = logging.getLogger("golestan_code_mcp.memory")


class MemoryStoreError(ValueError):
    """The memory store is missing or unusable. Safe to show the user."""


def _store(conn, policy, embedder, store_id: str):
    from oracleagentmemory.core import OracleDBMemoryStore

    return OracleDBMemoryStore(embedder=embedder, pool=conn, vector_dim=search_model.DIMENSION, schema_policy=policy,
                               memory_store_id=store_id)


def create_package_schema(conn, store_id: str = STORE_ID) -> None:
    """Migration 8's step: the package creates (or repairs) its tables. Needs no embedding model."""
    from oracleagentmemory.core import SchemaPolicy

    _store(conn, SchemaPolicy.CREATE_IF_NECESSARY, None, store_id)


def client(conn, store_id: str = STORE_ID):
    """A package client over the migrated store, embedding with the in-database model. Never creates tables."""
    search_model.require_model(conn)
    from oracleagentmemory.core import (
        MemoryExtractionConfig,
        OracleAgentMemory,
        SchemaPolicy,
    )
    from oracleagentmemory.core.embedders import OracleDBEmbedder

    embedder = OracleDBEmbedder(connection=conn, model=search_model.MODEL, embedding_dimension=search_model.DIMENSION,
                                max_input_tokens=MAX_INPUT_TOKENS)
    try:
        store = _store(conn, SchemaPolicy.REQUIRE_EXISTING, embedder, store_id)
    except RuntimeError:
        raise MemoryStoreError(f"memory store {store_id} is missing or out of date; run `ccctx db migrate`") from None
    return OracleAgentMemory(store=store, embedder=embedder,
                             memory_extraction_config=MemoryExtractionConfig(extract_memories=False))


def model(env: Mapping[str, str] | None = None):
    """(package Llm, distiller name) for the configured model, or None: then the templates write every fact."""
    configured = memory_model(environment() if env is None else env)
    if configured is None:
        return None
    from oracleagentmemory.core.llms.llm import Llm

    options = {k: v for k, v in (("api_base", configured.base), ("api_key", configured.key)) if v}
    return Llm(model=configured.model, temperature=0, **options), f"llm:{configured.model}"
