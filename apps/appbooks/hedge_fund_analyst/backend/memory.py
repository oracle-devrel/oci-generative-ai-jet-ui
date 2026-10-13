import threading
from contextlib import contextmanager

from oracleagentmemory.core import (
    MemoryExtractionConfig,
    OracleAgentMemory,
    SchemaPolicy,
    SearchStrategy,
)
from oracleagentmemory.core.embedders import OracleDBEmbedder

from .config import EMBED
from .db import DB, pool

CLIENTS = {}
LOCK = threading.Lock()


def build(connection, policy=SchemaPolicy.REQUIRE_EXISTING, embed_connection=None):
    # Runtime clients only validate the schema: no DDL during a turn, so concurrent sessions cannot collide on locks.
    # Embedding runs on True Cache when available (its own PGA budget); memory reads and writes stay on the primary.
    return OracleAgentMemory(
        connection=connection,
        embedder=OracleDBEmbedder(
            connection=embed_connection or connection,
            model=EMBED,
            embedding_dimension=384,
            max_input_tokens=512,
        ),
        memory_store_id="HFM",
        schema_policy=policy,
        search_strategy=SearchStrategy.VECTOR,
        memory_extraction_config=MemoryExtractionConfig(extract_memories=False),
    )


def memory_client(persona):
    # Pooled client used by setup and tests; registers the analyst user and plane agent once.
    with LOCK:
        if persona not in CLIENTS:
            CLIENTS[persona] = c = build(
                pool(persona, memory=True), SchemaPolicy.CREATE_IF_NECESSARY
            )
            for fn, id, info in [
                (c.add_user, "analyst", persona + " analyst"),
                (c.add_agent, "plane", "Governed hedge fund research analyst"),
            ]:
                try:
                    fn(id, info)
                except ValueError:
                    pass
        return CLIENTS[persona]


# Bind runtime memory operations to one authenticated database connection per operation.
# OAMP and its embedder use this connection, so every generated audit record carries the turn ID.
@contextmanager
def scoped_client(persona, request_id=None):
    db = DB(persona, request_id, memory=True)
    try:
        yield build(db.c, embed_connection=db.r)
    finally:
        db.close()


def scoped_thread(c, tid):
    try:
        return c.get_thread(tid)
    except (KeyError, ValueError):
        return c.create_thread(
            thread_id=tid, user_id="analyst", agent_id="plane", context_card_token_limit=1500
        )


def append_messages(persona, tid, messages, request_id=None):
    with scoped_client(persona, request_id) as c:
        return scoped_thread(c, tid).add_messages(messages)


def store_fact(persona, content, memory_type, metadata, request_id=None):
    with scoped_client(persona, request_id) as c:
        return c.add_memory(
            content, memory_type=memory_type, user_id="analyst", agent_id="plane", metadata=metadata
        )


def recall(persona, q, request_id=None):
    with scoped_client(persona, request_id) as c:
        hits = c.search(
            q,
            user_id="analyst",
            agent_id="plane",
            record_types=["fact", "preference", "guideline", "memory"],
            max_results=6,
            token_budget=1500,
        )
        return [
            {"id": h.id, "content": h.content, "type": h.record.record_type, "metadata": h.metadata}
            for h in hits
        ]


def inventory(persona):
    with scoped_client(persona) as c:
        return {
            "threads": [
                {"id": t.id, "user_id": t.user_id, "agent_id": t.agent_id}
                for t in c.list_threads("analyst", limit=50)
            ],
            "facts": [
                {"id": m.id, "content": m.content, "type": m.record_type, "metadata": m.metadata}
                for m in c.list_memories("analyst", limit=50)
            ],
        }


def reset_memories(persona, request_id=None):
    # Clears durable facts for this desk's analyst only; runs under the desk's own memory identity.
    with scoped_client(persona, request_id) as c:
        ids = [m.id for m in c.list_memories("analyst", limit=500)]
        for id in ids:
            c.delete_memory(id)
        return ids
