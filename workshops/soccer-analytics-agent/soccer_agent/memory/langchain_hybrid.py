"""LangChain OracleDB vector-store and hybrid retrieval support.

This module keeps the original hand-rolled ``semantic_memory`` table intact while
adding an official ``langchain-oracledb`` showcase table.  The table is populated
from model prediction rows plus football summary facts, then queried with native
Oracle hybrid search when available or an Oracle Text + vector RRF fallback.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict

import oracledb
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Sequence

from soccer_agent.db import get_connection

_TABLE_NAME = os.environ.get("ORACLE_LANGCHAIN_VECTOR_TABLE", "SOCCER_LANGCHAIN_DOCS")
_VECTOR_INDEX_NAME = os.environ.get("ORACLE_LANGCHAIN_VECTOR_INDEX", "IDX_SOCCER_LC_HNSW")
_TEXT_INDEX_NAME = os.environ.get("ORACLE_LANGCHAIN_TEXT_INDEX", "IDX_SOCCER_LC_TEXT")
_HYBRID_INDEX_NAME = os.environ.get("ORACLE_LANGCHAIN_HYBRID_INDEX", "IDX_SOCCER_LC_HYBRID")
_EMBED_MODEL = os.environ.get("ORACLE_EMBED_MODEL", "ALL_MINILM_L6_V2")

_SIMPLE_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]*$")
_RRF_K = 60


class LangChainOracleDBUnavailable(RuntimeError):
    """Raised when the optional LangChain OracleDB integration is unavailable."""


def _identifier(name: str, *, label: str) -> str:
    """Validate an Oracle identifier controlled by env vars before string SQL."""
    upper = name.upper()
    if not _SIMPLE_IDENTIFIER.fullmatch(upper):
        raise ValueError(f"{label} must be a simple Oracle identifier, got {name!r}")
    return upper


TABLE_NAME = _identifier(_TABLE_NAME, label="ORACLE_LANGCHAIN_VECTOR_TABLE")
VECTOR_INDEX_NAME = _identifier(_VECTOR_INDEX_NAME, label="ORACLE_LANGCHAIN_VECTOR_INDEX")
TEXT_INDEX_NAME = _identifier(_TEXT_INDEX_NAME, label="ORACLE_LANGCHAIN_TEXT_INDEX")
HYBRID_INDEX_NAME = _identifier(_HYBRID_INDEX_NAME, label="ORACLE_LANGCHAIN_HYBRID_INDEX")


@dataclass(frozen=True)
class SourceDocument:
    """A project-native document before it is converted to LangChain."""

    doc_id: str
    page_content: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class HybridSearchResult:
    """A retrieval result normalized across native and fallback search paths."""

    page_content: str
    metadata: dict[str, Any]
    score: float | None = None
    retrieval_mode: str = "hybrid"


def _langchain_imports() -> dict[str, Any]:
    try:
        from langchain_community.vectorstores.utils import DistanceStrategy
        from langchain_core.documents import Document
        from langchain_oracledb.embeddings.oracleai import OracleEmbeddings
        from langchain_oracledb.retrievers.hybrid_search import (
            OracleHybridSearchRetriever,
            create_hybrid_index,
        )
        from langchain_oracledb.retrievers.text_search import (
            OracleTextSearchRetriever,
            create_text_index,
        )
        from langchain_oracledb.vectorstores.oraclevs import OracleVS, create_index
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional install state
        raise LangChainOracleDBUnavailable(
            "Install langchain-oracledb to use the OracleVS hybrid retrieval demo: "
            "`uv add langchain-oracledb` or `pip install langchain-oracledb`."
        ) from exc

    return {
        "DistanceStrategy": DistanceStrategy,
        "Document": Document,
        "OracleEmbeddings": OracleEmbeddings,
        "OracleHybridSearchRetriever": OracleHybridSearchRetriever,
        "OracleTextSearchRetriever": OracleTextSearchRetriever,
        "OracleVS": OracleVS,
        "create_hybrid_index": create_hybrid_index,
        "create_index": create_index,
        "create_text_index": create_text_index,
    }


def _jsonable(value: Any) -> Any:
    """Convert Oracle/numpy-ish scalars to metadata values JSON can store."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _error_summary(exc: BaseException) -> str:
    """Return concise error evidence for retrieval fallback metadata/statuses."""
    message = " ".join(str(exc).split())
    if len(message) > 220:
        message = f"{message[:217]}..."
    return f"{exc.__class__.__name__}: {message}"


def _is_missing_table_error(exc: BaseException) -> bool:
    """True only for the expected optional-table-not-created state."""
    return "ORA-00942" in str(exc)


def prediction_document_from_row(row: Sequence[Any]) -> SourceDocument:
    """Build a retrievable text record from one PREDICCIONES_FINAL row."""
    home, away, p_home, p_draw, p_away, model_version = row
    probs = {
        str(home): float(p_home or 0.0),
        "Draw": float(p_draw or 0.0),
        str(away): float(p_away or 0.0),
    }
    favorite = max(probs, key=probs.get)
    confidence = probs[favorite]
    doc_id = f"prediction:{model_version}:{home}:{away}"
    content = (
        f"ML prediction for {home} vs {away}: {home} win probability "
        f"{float(p_home):.1%}, draw probability {float(p_draw):.1%}, "
        f"{away} win probability {float(p_away):.1%}. The trained XGBoost "
        f"model version {model_version} favors {favorite} with {confidence:.1%} "
        "confidence. Use this as cached inference context, then call "
        "predict_match when the user asks for a live hypothetical prediction."
    )
    return SourceDocument(
        doc_id=doc_id,
        page_content=content,
        metadata={
            "doc_id": doc_id,
            "doc_type": "prediction",
            "home_team": _jsonable(home),
            "away_team": _jsonable(away),
            "model_version": _jsonable(model_version),
            "prob_home_win": float(p_home or 0.0),
            "prob_draw": float(p_draw or 0.0),
            "prob_away_win": float(p_away or 0.0),
            "favorite": favorite,
            "confidence": confidence,
            "source_table": "PREDICCIONES_FINAL",
        },
    )


def team_stat_document_from_row(row: Sequence[Any]) -> SourceDocument:
    """Build a retrievable text record from one VW_TEAM_STATISTICS row."""
    team, matches, wins, win_pct, goals_for, goal_diff = row
    doc_id = f"team_stat:{team}"
    content = (
        f"World Cup team profile for {team}: {int(matches or 0)} competitive "
        f"matches since 1950, {int(wins or 0)} wins, win percentage "
        f"{float(win_pct or 0):.2f}%, {int(goals_for or 0)} goals scored, "
        f"goal difference {int(goal_diff or 0)}. This row comes from the "
        "VW_TEAM_STATISTICS analytical view in Oracle."
    )
    return SourceDocument(
        doc_id=doc_id,
        page_content=content,
        metadata={
            "doc_id": doc_id,
            "doc_type": "team_stat",
            "team": _jsonable(team),
            "total_matches": int(matches or 0),
            "total_wins": int(wins or 0),
            "win_percentage": float(win_pct or 0.0),
            "total_goals_scored": int(goals_for or 0),
            "goal_difference": int(goal_diff or 0),
            "source_view": "VW_TEAM_STATISTICS",
        },
    )


def team_decade_document_from_row(row: Sequence[Any]) -> SourceDocument:
    """Build a retrievable text record from one team/decade World Cup aggregate."""
    team, decade, matches, wins, goals_for, goals_against = row
    decade_i = int(decade or 0)
    doc_id = f"team_decade:{team}:{decade_i}"
    content = (
        f"{team} in the {decade_i}s FIFA World Cups: {int(matches or 0)} "
        f"matches, {int(wins or 0)} wins, {int(goals_for or 0)} goals scored, "
        f"{int(goals_against or 0)} goals conceded. This is a decade-level "
        "football fact suitable for keyword plus semantic retrieval."
    )
    return SourceDocument(
        doc_id=doc_id,
        page_content=content,
        metadata={
            "doc_id": doc_id,
            "doc_type": "team_decade",
            "team": _jsonable(team),
            "decade": decade_i,
            "matches": int(matches or 0),
            "wins": int(wins or 0),
            "goals_for": int(goals_for or 0),
            "goals_against": int(goals_against or 0),
            "source_table": "MATCH_RESULTS",
        },
    )


def fetch_prediction_documents(limit: int = 2_500) -> list[SourceDocument]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT HOME_TEAM, AWAY_TEAM, PROB_HOME_WIN, PROB_DRAW,
                   PROB_AWAY_WIN, MODEL_VERSION
            FROM PREDICCIONES_FINAL
            ORDER BY MODEL_VERSION, HOME_TEAM, AWAY_TEAM
            FETCH FIRST :lim ROWS ONLY
            """,
            lim=int(limit),
        )
        return [prediction_document_from_row(row) for row in cur.fetchall()]


def fetch_team_stat_documents(limit: int = 250) -> list[SourceDocument]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT TEAM, TOTAL_MATCHES, TOTAL_WINS, WIN_PERCENTAGE,
                   TOTAL_GOALS_SCORED, GOAL_DIFFERENCE
            FROM VW_TEAM_STATISTICS
            ORDER BY TOTAL_MATCHES DESC, TEAM
            FETCH FIRST :lim ROWS ONLY
            """,
            lim=int(limit),
        )
        return [team_stat_document_from_row(row) for row in cur.fetchall()]


def fetch_team_decade_documents(limit: int = 750) -> list[SourceDocument]:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            WITH team_decade AS (
                SELECT home_team AS team,
                       FLOOR(EXTRACT(YEAR FROM date_rw) / 10) * 10 AS decade,
                       CASE WHEN home_score > away_score THEN 1 ELSE 0 END AS win,
                       home_score AS gf, away_score AS ga
                FROM match_results WHERE tournament = 'FIFA World Cup'
                UNION ALL
                SELECT away_team AS team,
                       FLOOR(EXTRACT(YEAR FROM date_rw) / 10) * 10 AS decade,
                       CASE WHEN away_score > home_score THEN 1 ELSE 0 END AS win,
                       away_score AS gf, home_score AS ga
                FROM match_results WHERE tournament = 'FIFA World Cup'
            )
            SELECT team, decade, COUNT(*) AS n,
                   SUM(win) AS wins, SUM(gf) AS gf, SUM(ga) AS ga
            FROM team_decade
            WHERE team IS NOT NULL
            GROUP BY team, decade
            HAVING COUNT(*) >= 3
            ORDER BY team, decade
            FETCH FIRST :lim ROWS ONLY
            """,
            lim=int(limit),
        )
        return [team_decade_document_from_row(row) for row in cur.fetchall()]


def fetch_soccer_documents(
    *,
    max_predictions: int = 2_500,
    max_team_stats: int = 250,
    max_team_decades: int = 750,
) -> list[SourceDocument]:
    """Return all project documents selected for the LangChain vector store."""
    docs: list[SourceDocument] = []
    docs.extend(fetch_prediction_documents(max_predictions))
    docs.extend(fetch_team_stat_documents(max_team_stats))
    docs.extend(fetch_team_decade_documents(max_team_decades))
    return docs


def get_vector_store(conn: Any) -> Any:
    """Create/load the LangChain ``OracleVS`` wrapper for the soccer docs table."""
    imports = _langchain_imports()
    embeddings = imports["OracleEmbeddings"](
        conn=conn,
        params={"provider": "database", "model": _EMBED_MODEL},
    )
    return imports["OracleVS"](
        client=conn,
        embedding_function=embeddings,
        table_name=TABLE_NAME,
        distance_strategy=imports["DistanceStrategy"].COSINE,
        query="Spain Brazil World Cup prediction football retrieval",
        mutate_on_duplicate=True,
    )


def _to_langchain_documents(docs: Iterable[SourceDocument]) -> tuple[list[Any], list[str]]:
    imports = _langchain_imports()
    out = []
    ids = []
    for doc in docs:
        metadata = {k: _jsonable(v) for k, v in doc.metadata.items()}
        metadata.setdefault("doc_id", doc.doc_id)
        out.append(imports["Document"](
            page_content=doc.page_content,
            metadata=metadata,
            id=doc.doc_id,
        ))
        ids.append(doc.doc_id)
    return out, ids


def _drop_table_if_exists(conn: Any, table_name: str = TABLE_NAME) -> None:
    cur = conn.cursor()
    try:
        cur.execute(f"DROP TABLE {table_name} PURGE")
        conn.commit()
    except oracledb.DatabaseError as exc:
        conn.rollback()
        if not _is_missing_table_error(exc):
            raise


def create_retrieval_indexes(conn: Any, vector_store: Any, *, strict: bool = False) -> list[str]:
    """Create vector, text, and native hybrid indexes when the DB supports them."""
    imports = _langchain_imports()
    statuses: list[str] = []
    index_jobs = [
        (
            "vector",
            lambda: imports["create_index"](
                conn,
                vector_store,
                params={
                    "idx_name": VECTOR_INDEX_NAME,
                    "idx_type": "HNSW",
                    "parallel": 2,
                    "accuracy": 90,
                },
            ),
        ),
        # Try native hybrid before a standalone Oracle Text index. A HYBRID
        # VECTOR INDEX owns its text side; creating text first can conflict with
        # ORA-29879 on the same column list. If native hybrid is unavailable,
        # the next job creates text for the fallback path.
        (
            "hybrid",
            lambda: imports["create_hybrid_index"](
                conn,
                idx_name=HYBRID_INDEX_NAME,
                vector_store=vector_store,
                params={"parallel": 2},
            ),
        ),
        (
            "text",
            lambda: imports["create_text_index"](
                conn,
                idx_name=TEXT_INDEX_NAME,
                vector_store=vector_store,
            ),
        ),
    ]
    for label, job in index_jobs:
        try:
            job()
            conn.commit()
            statuses.append(f"{label}: ready")
        except Exception as exc:  # optional vector/text/hybrid indexes vary by image
            conn.rollback()
            msg = f"{label}: skipped ({_error_summary(exc)})"
            if strict:
                raise RuntimeError(msg) from exc
            statuses.append(msg)
    return statuses


def load_documents_into_vector_store(
    docs: Sequence[SourceDocument],
    *,
    reset: bool = False,
    batch_size: int = 64,
    create_indexes: bool = True,
    strict_indexes: bool = False,
) -> dict[str, Any]:
    """Insert project documents into the LangChain OracleVS table."""
    if not docs:
        return {"inserted": 0, "table": TABLE_NAME, "indexes": []}

    with get_connection() as conn:
        if reset:
            _drop_table_if_exists(conn)
        vector_store = get_vector_store(conn)
        lc_docs, ids = _to_langchain_documents(docs)
        inserted = 0
        for start in range(0, len(lc_docs), batch_size):
            stop = start + batch_size
            added = vector_store.add_documents(lc_docs[start:stop], ids=ids[start:stop])
            inserted += len(added)
            conn.commit()
        index_statuses = (
            create_retrieval_indexes(conn, vector_store, strict=strict_indexes)
            if create_indexes
            else []
        )
    return {"inserted": inserted, "table": TABLE_NAME, "indexes": index_statuses}


def count_vector_store_rows() -> int:
    """Return zero when the LangChain vector-store table has not been created yet."""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
            return int(cur.fetchone()[0])
        except oracledb.DatabaseError as exc:
            if _is_missing_table_error(exc):
                return 0
            raise


def _materialize_text(value: Any) -> str:
    return value.read() if hasattr(value, "read") else str(value)


def _parse_metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "read"):
        value = value.read()
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        return json.loads(value)
    return dict(value)


def _doc_key(doc: Any) -> str:
    metadata = dict(getattr(doc, "metadata", {}) or {})
    return str(getattr(doc, "id", None) or metadata.get("doc_id") or doc.page_content[:120])


def _doc_to_result(doc: Any, *, score: float | None, mode: str) -> HybridSearchResult:
    metadata = dict(getattr(doc, "metadata", {}) or {})
    doc_id = getattr(doc, "id", None) or metadata.get("doc_id")
    if doc_id:
        metadata.setdefault("doc_id", doc_id)
    return HybridSearchResult(
        page_content=str(getattr(doc, "page_content", "")),
        metadata=metadata,
        score=score,
        retrieval_mode=mode,
    )


def _keyword_like_documents(conn: Any, query: str, limit: int) -> list[Any]:
    """Last-resort lexical retrieval when Oracle Text search index is unavailable."""
    imports = _langchain_imports()
    tokens = [t.lower() for t in re.findall(r"[\w']+", query) if len(t) > 2][:8]
    if not tokens:
        return []
    where = " OR ".join(f"LOWER(text) LIKE :t{i}" for i, _ in enumerate(tokens))
    binds = {f"t{i}": f"%{token}%" for i, token in enumerate(tokens)}
    binds["lim"] = int(limit)
    cur = conn.cursor()
    cur.execute(
        f"SELECT text, metadata FROM {TABLE_NAME} WHERE {where} FETCH FIRST :lim ROWS ONLY",
        binds,
    )
    docs = []
    for text, metadata in cur.fetchall():
        parsed = _parse_metadata(metadata)
        docs.append(imports["Document"](
            page_content=_materialize_text(text),
            metadata=parsed,
            id=parsed.get("doc_id"),
        ))
    return docs


def _rrf_merge(
    vector_results: Sequence[tuple[Any, float]],
    text_docs: Sequence[Any],
    *,
    limit: int,
    note: str | None = None,
) -> list[HybridSearchResult]:
    scores: defaultdict[str, float] = defaultdict(float)
    best_docs: dict[str, Any] = {}
    metadata_updates: dict[str, dict[str, Any]] = defaultdict(dict)

    for rank, (doc, distance) in enumerate(vector_results, start=1):
        key = _doc_key(doc)
        best_docs.setdefault(key, doc)
        scores[key] += 1.0 / (_RRF_K + rank)
        metadata_updates[key].update({
            "vector_rank": rank,
            "vector_distance": float(distance),
        })

    for rank, doc in enumerate(text_docs, start=1):
        key = _doc_key(doc)
        best_docs.setdefault(key, doc)
        scores[key] += 1.0 / (_RRF_K + rank)
        text_score = dict(getattr(doc, "metadata", {}) or {}).get("score")
        update = {"text_rank": rank}
        if text_score is not None:
            update["text_score"] = float(text_score)
        metadata_updates[key].update(update)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
    out: list[HybridSearchResult] = []
    for key, score in ranked:
        result = _doc_to_result(best_docs[key], score=score, mode="fallback_rrf")
        result.metadata.update(metadata_updates[key])
        if note:
            result.metadata.setdefault("retrieval_note", note)
        out.append(result)
    return out


def hybrid_search(
    query: str,
    *,
    limit: int = 5,
    search_mode: Literal["hybrid", "semantic", "keyword"] = "hybrid",
) -> list[HybridSearchResult]:
    """Retrieve from the LangChain OracleVS table with hybrid semantics.

    The preferred path uses ``OracleHybridSearchRetriever`` and a HYBRID VECTOR
    INDEX when the database image supports it. The fallback path runs LangChain
    vector search plus Oracle Text search (or LIKE as a last resort) and fuses
    ranks with RRF, preserving retrieval evidence in result metadata.
    """
    if count_vector_store_rows() <= 0:
        return []

    imports = _langchain_imports()
    pool = max(int(limit) * 3, 10)
    native_error: str | None = None

    with get_connection() as conn:
        vector_store = get_vector_store(conn)

        if search_mode in {"hybrid", "semantic", "keyword"}:
            try:
                retriever = imports["OracleHybridSearchRetriever"](
                    vector_store=vector_store,
                    idx_name=HYBRID_INDEX_NAME,
                    search_mode=search_mode,
                    k=int(limit),
                    return_scores=True,
                )
                docs = retriever.invoke(query)
                if docs:
                    return [
                        _doc_to_result(
                            doc,
                            score=(doc.metadata or {}).get("score"),
                            mode=f"native_{search_mode}",
                        )
                        for doc in docs
                    ]
            except Exception as exc:
                native_error = f"native hybrid unavailable: {_error_summary(exc)}"

        vector_results: list[tuple[Any, float]] = []
        text_docs: list[Any] = []

        if search_mode in {"hybrid", "semantic"}:
            try:
                vector_results = vector_store.similarity_search_with_score(query, k=pool)
            except Exception as exc:
                native_error = f"{native_error or ''}; vector fallback failed: {_error_summary(exc)}".strip("; ")

        if search_mode in {"hybrid", "keyword"}:
            try:
                text_retriever = imports["OracleTextSearchRetriever"](
                    vector_store=vector_store,
                    k=pool,
                    return_scores=True,
                    returned_columns=["metadata"],
                )
                text_docs = text_retriever.invoke(query)
            except Exception as exc:
                native_error = f"{native_error or ''}; text fallback used LIKE after {_error_summary(exc)}".strip("; ")
                text_docs = _keyword_like_documents(conn, query, pool)

        return _rrf_merge(vector_results, text_docs, limit=int(limit), note=native_error)
