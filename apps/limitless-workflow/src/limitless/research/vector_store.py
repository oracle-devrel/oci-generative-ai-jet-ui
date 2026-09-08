from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_oci.embeddings import OCIGenAIEmbeddings
from langchain_oracledb.vectorstores import OracleVS
from langchain_oracledb.vectorstores.oraclevs import create_index
from langchain_community.vectorstores.utils import DistanceStrategy

from limitless.db.pool import get_pool
from limitless.settings import Settings


class VectorRetrievalConfigError(RuntimeError):
    """Raised when OCI vector retrieval configuration is incomplete."""


@dataclass(slots=True)
class RetrievedChunk:
    text: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class VectorCheckResult:
    enabled: bool
    ready: bool
    message: str


RESEARCH_VECTOR_TABLE = "LIMITLESS_RESEARCH_VS"
RESEARCH_VECTOR_INDEX = "LIMITLESS_RESEARCH_HNSW_IDX"


def vector_enabled(settings: Settings) -> bool:
    return settings.oracle_vector_enabled


def validate_vector_settings(settings: Settings) -> VectorCheckResult:
    if not settings.oracle_vector_enabled:
        return VectorCheckResult(
            enabled=False,
            ready=False,
            message="Vector retrieval is disabled. Set ORACLE_VECTOR_ENABLED=true to enable it.",
        )
    missing = []
    if not settings.oci_compartment_id:
        missing.append("OCI_COMPARTMENT_ID")
    if not settings.oci_region:
        missing.append("OCI_REGION")
    if missing:
        return VectorCheckResult(
            enabled=True,
            ready=False,
            message="Missing required OCI vector settings: " + ", ".join(missing),
        )
    return VectorCheckResult(
        enabled=True,
        ready=True,
        message="OCI vector retrieval settings look complete.",
    )


def _service_endpoint(settings: Settings) -> str:
    if settings.oci_genai_endpoint:
        return settings.oci_genai_endpoint
    return f"https://inference.generativeai.{settings.oci_region}.oci.oraclecloud.com"


def build_oci_embeddings(settings: Settings) -> OCIGenAIEmbeddings:
    check = validate_vector_settings(settings)
    if not check.ready:
        raise VectorRetrievalConfigError(check.message)

    kwargs: dict[str, Any] = {
        "auth_profile": settings.oci_auth_profile,
        "auth_file_location": settings.oci_config_file,
        "model_id": settings.oracle_embedding_model,
        "service_endpoint": _service_endpoint(settings),
        "compartment_id": settings.oci_compartment_id,
    }
    if settings.oci_auth_type:
        kwargs["auth_type"] = settings.oci_auth_type
    return OCIGenAIEmbeddings(**kwargs)


def build_vector_store(settings: Settings) -> OracleVS:
    embeddings = build_oci_embeddings(settings)
    pool = get_pool(settings)
    return OracleVS(
        pool,
        embeddings,
        settings.oracle_vector_table,
        distance_strategy=DistanceStrategy.COSINE,
        mutate_on_duplicate=True,
    )


def _fetch_topic_chunks(topic_slug: str, settings: Settings) -> list[tuple[str, dict[str, Any], str]]:
    pool = get_pool(settings)
    with pool.acquire() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    rc.ID,
                    rc.CHUNK_TEXT,
                    rc.CHUNK_INDEX,
                    rc.SOURCE_HEADING,
                    t.SLUG,
                    rr.VERSION_NUMBER
                FROM RESEARCH_CHUNKS rc
                JOIN TOPICS t ON t.ID = rc.TOPIC_ID
                JOIN RESEARCH_REPORTS rr ON rr.ID = rc.REPORT_ID
                WHERE t.SLUG = :topic_slug
                ORDER BY rc.CHUNK_INDEX
                """,
                topic_slug=topic_slug,
            )
            rows = cursor.fetchall()
    chunks: list[tuple[str, dict[str, Any], str]] = []
    for row in rows:
        chunk_id = str(row[0])
        chunk_text = row[1].read() if hasattr(row[1], "read") else row[1]
        metadata = {
            "chunk_id": chunk_id,
            "chunk_index": int(row[2]),
            "source_heading": row[3],
            "topic_slug": row[4],
            "report_version": int(row[5]),
        }
        vector_id = f"{row[4]}:{chunk_id}"
        chunks.append((chunk_text, metadata, vector_id))
    return chunks


def sync_topic_chunks_to_vector_store(topic_slug: str, settings: Settings) -> int:
    chunks = _fetch_topic_chunks(topic_slug, settings)
    if not chunks:
        return 0

    vector_store = build_vector_store(settings)
    texts = [item[0] for item in chunks]
    metadatas = [item[1] for item in chunks]
    ids = [item[2] for item in chunks]
    vector_store.add_texts(texts, metadatas=metadatas, ids=ids)

    pool = get_pool(settings)
    with pool.acquire() as connection:
        try:
            create_index(
                connection,
                vector_store,
                params={
                    "idx_name": settings.oracle_vector_index_name,
                    "idx_type": "HNSW",
                },
            )
        except Exception:
            # Re-running sync should stay harmless even if the index already exists.
            pass

    return len(chunks)


def similarity_search(topic_slug: str, query: str, settings: Settings, k: int = 4) -> list[RetrievedChunk]:
    vector_store = build_vector_store(settings)
    docs = vector_store.similarity_search(
        query,
        k=k,
        filter={"topic_slug": {"$eq": topic_slug}},
    )
    return [RetrievedChunk(text=document.page_content, metadata=document.metadata or {}) for document in docs]
