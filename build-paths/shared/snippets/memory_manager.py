"""Six-memory-types pattern, ported for the build-paths advanced path.

Source: apps/finance-ai-agent-demo/backend/memory/manager.py:1-100

WHY THIS EXISTS
---------------
The advanced path enforces "Oracle is the only state store." Agents typically
need:
  * conversational  — turn-by-turn message log per thread
  * knowledge_base  — durable, vector-searchable facts
  * workflow        — in-flight multi-step state
  * toolbox         — tool definitions / capabilities the agent knows about
  * entity          — people / places / topics with embeddings
  * summary         — compressed long-running context

This module gives a single `MemoryManager` with `write_*`, `read_*`, and
(where it makes sense) `search_*` methods backed by Oracle tables. It uses
the metadata monkeypatch so OracleVS metadata reads come back as dicts.

DDL is in migrations/002_memory.sql (the advanced skill emits it during
scaffolding).

USAGE
-----
    mem = MemoryManager(conn, embedder, project="REVIEW_AGENT")
    mem.write_conversational("thread-1", "user", "hi")
    mem.write_knowledge("oauth requires PKCE for public clients", source="rfc7636")
    hits = mem.search_knowledge("how does OAuth auth code flow work?", k=3)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

import oracledb
from langchain_core.embeddings import Embeddings
from langchain_oracledb import OracleVS
from langchain_oracledb.utils.distance_strategy import DistanceStrategy


@dataclass
class MemoryRow:
    id: int
    content: str
    metadata: dict[str, Any]
    score: Optional[float] = None


class MemoryManager:
    def __init__(self, conn: oracledb.Connection, embedder: Embeddings, project: str):
        self.conn = conn
        self.embedder = embedder
        self.project = project.upper()
        # Vector-searchable memories use OracleVS; non-vector ones use plain SQL.
        self._kb = OracleVS(
            client=conn,
            embedding_function=embedder,
            table_name=f"{self.project}_KNOWLEDGE",
            distance_strategy=DistanceStrategy.COSINE,
        )
        self._entities = OracleVS(
            client=conn,
            embedding_function=embedder,
            table_name=f"{self.project}_ENTITIES",
            distance_strategy=DistanceStrategy.COSINE,
        )
        self._summaries = OracleVS(
            client=conn,
            embedding_function=embedder,
            table_name=f"{self.project}_SUMMARIES",
            distance_strategy=DistanceStrategy.COSINE,
        )

    # ── conversational (per-thread message log; non-vector) ──────────────

    def write_conversational(self, thread_id: str, role: str, content: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.project}_CONVERSATIONAL (thread_id, role, content) "
                f"VALUES (:t, :r, :c)",
                t=thread_id, r=role, c=content,
            )
        self.conn.commit()

    def read_conversational(self, thread_id: str, limit: int = 50) -> list[MemoryRow]:
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT id, role, content, created_at FROM {self.project}_CONVERSATIONAL "
                f"WHERE thread_id = :t ORDER BY id DESC FETCH FIRST :n ROWS ONLY",
                t=thread_id, n=limit,
            )
            return [MemoryRow(id=r[0], content=r[2], metadata={"role": r[1], "ts": r[3]})
                    for r in cur.fetchall()]

    # ── knowledge base (vector-searchable durable facts) ─────────────────

    def write_knowledge(self, fact: str, **metadata: Any) -> None:
        self._kb.add_texts([fact], metadatas=[metadata])

    def search_knowledge(self, query: str, k: int = 5,
                         filter: Optional[dict] = None) -> list[MemoryRow]:
        hits = self._kb.similarity_search_with_score(query, k=k, filter=filter)
        return [MemoryRow(id=0, content=d.page_content, metadata=d.metadata, score=s)
                for d, s in hits]

    # ── workflow (in-flight multi-step state; non-vector, JSON CLOB) ─────

    def write_workflow(self, run_id: str, state: dict) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                f"MERGE INTO {self.project}_WORKFLOW USING dual ON (run_id = :r) "
                f"WHEN MATCHED THEN UPDATE SET state = :s, updated_at = SYSTIMESTAMP "
                f"WHEN NOT MATCHED THEN INSERT (run_id, state) VALUES (:r, :s)",
                r=run_id, s=json.dumps(state),
            )
        self.conn.commit()

    def read_workflow(self, run_id: str) -> Optional[dict]:
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT state FROM {self.project}_WORKFLOW WHERE run_id = :r",
                r=run_id,
            )
            row = cur.fetchone()
            if not row:
                return None
            payload = row[0]
            # oracledb 4.x returns IS JSON columns as dict directly.
            if isinstance(payload, dict):
                return payload
            return json.loads(payload.read() if hasattr(payload, "read") else payload)

    # ── toolbox (catalog of tools the agent knows about; non-vector) ─────

    def write_tool(self, name: str, schema: dict) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                f"MERGE INTO {self.project}_TOOLBOX USING dual ON (name = :n) "
                f"WHEN MATCHED THEN UPDATE SET schema = :s "
                f"WHEN NOT MATCHED THEN INSERT (name, schema) VALUES (:n, :s)",
                n=name, s=json.dumps(schema),
            )
        self.conn.commit()

    def list_tools(self) -> list[MemoryRow]:
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT name, schema FROM {self.project}_TOOLBOX ORDER BY name")
            out = []
            for r in cur.fetchall():
                schema_payload = r[1]
                # oracledb 4.x returns IS JSON columns as dict directly.
                if isinstance(schema_payload, dict):
                    metadata = schema_payload
                else:
                    raw = schema_payload.read() if hasattr(schema_payload, "read") else schema_payload
                    metadata = json.loads(raw)
                out.append(MemoryRow(id=0, content=r[0], metadata=metadata))
            return out

    # ── entity (people/places/topics with embeddings) ────────────────────

    def write_entity(self, name: str, profile: str, kind: str = "person") -> None:
        self._entities.add_texts([profile], metadatas=[{"name": name, "kind": kind}])

    def search_entities(self, query: str, k: int = 5) -> list[MemoryRow]:
        hits = self._entities.similarity_search_with_score(query, k=k)
        return [MemoryRow(id=0, content=d.page_content, metadata=d.metadata, score=s)
                for d, s in hits]

    # ── summary (compressed long-running context) ────────────────────────

    def write_summary(self, summary: str, scope: str) -> None:
        self._summaries.add_texts([summary], metadatas=[{"scope": scope}])

    def search_summaries(self, query: str, k: int = 3) -> list[MemoryRow]:
        hits = self._summaries.similarity_search_with_score(query, k=k)
        return [MemoryRow(id=0, content=d.page_content, metadata=d.metadata, score=s)
                for d, s in hits]
