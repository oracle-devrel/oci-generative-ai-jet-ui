"""Semantic memory: distilled facts with vector search."""

from __future__ import annotations

import array
import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from soccer_agent.db import get_connection


@dataclass
class Fact:
    fact_type: str
    subject_key: str
    summary: str
    source: dict[str, Any]
    embedding: np.ndarray


def _to_vector(arr: np.ndarray) -> array.array:
    if arr.dtype != np.float32:
        arr = arr.astype(np.float32)
    if arr.shape != (384,):
        raise ValueError(f"Expected (384,) embedding, got {arr.shape}")
    return array.array("f", arr.tolist())


class SemanticMemory:
    def upsert(self, fact: Fact) -> None:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM semantic_memory "
                "WHERE fact_type = :t AND subject_key = :k",
                t=fact.fact_type, k=fact.subject_key,
            )
            cur.execute(
                "INSERT INTO semantic_memory "
                "(fact_type, subject_key, summary, source_json, embedding) "
                "VALUES (:t, :k, :s, :j, :e)",
                t=fact.fact_type, k=fact.subject_key, s=fact.summary,
                j=json.dumps(fact.source), e=_to_vector(fact.embedding),
            )
            conn.commit()

    def search(self, query_embedding: np.ndarray, limit: int = 5,
               fact_type: str | None = None) -> list[Fact]:
        sql = (
            "SELECT fact_type, subject_key, summary, source_json "
            "FROM semantic_memory "
        )
        binds: dict[str, Any] = {"q": _to_vector(query_embedding), "lim": limit}
        if fact_type:
            sql += "WHERE fact_type = :ft "
            binds["ft"] = fact_type
        sql += "ORDER BY VECTOR_DISTANCE(embedding, :q, COSINE) FETCH FIRST :lim ROWS ONLY"

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, binds)
            raw_rows = [
                (
                    ft,
                    key,
                    summary.read() if hasattr(summary, "read") else summary,
                    src.read() if hasattr(src, "read") else src,
                )
                for ft, key, summary, src in cur.fetchall()
            ]

        out: list[Fact] = []
        for ft, key, summary, src in raw_rows:
            if src is None:
                parsed_src: dict[str, Any] = {}
            elif isinstance(src, (dict, list)):
                parsed_src = src
            else:
                parsed_src = json.loads(src)
            out.append(Fact(
                fact_type=ft, subject_key=key, summary=summary,
                source=parsed_src,
                embedding=np.zeros(384, dtype=np.float32),
            ))
        return out
