from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import oracledb

from limitless.graph.models import TopicPacket
from limitless.research.chunker import ResearchChunk, chunk_markdown
from limitless.research.grounding import match_concept_snippets_to_chunks


def split_sql_statements(sql: str) -> list[str]:
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def prepare_connection_for_app_dml(connection: oracledb.Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute("ALTER SESSION DISABLE PARALLEL DML")
        cursor.execute("ALTER SESSION DISABLE PARALLEL QUERY")


def apply_schema(connection: oracledb.Connection, schema_path: str | Path = "config/schema.sql") -> None:
    sql = Path(schema_path).read_text(encoding="utf-8")
    with connection.cursor() as cursor:
        for statement in split_sql_statements(sql):
            try:
                cursor.execute(statement)
            except oracledb.DatabaseError as exc:
                error = exc.args[0]
                code = getattr(error, "code", None)
                if code in {54, 955, 1408}:
                    continue
                raise
    connection.commit()


def upsert_topic(
    connection: oracledb.Connection,
    *,
    slug: str,
    title: str,
    description: str | None = None,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            MERGE INTO TOPICS target
            USING (
                SELECT :slug AS SLUG, :title AS TITLE, :description AS DESCRIPTION FROM dual
            ) source
            ON (target.SLUG = source.SLUG)
            WHEN MATCHED THEN UPDATE SET
                target.TITLE = source.TITLE,
                target.DESCRIPTION = source.DESCRIPTION,
                target.UPDATED_AT = CURRENT_TIMESTAMP
            WHEN NOT MATCHED THEN INSERT (SLUG, TITLE, DESCRIPTION)
            VALUES (source.SLUG, source.TITLE, source.DESCRIPTION)
            """,
            slug=slug,
            title=title,
            description=description,
        )
        cursor.execute("SELECT ID FROM TOPICS WHERE SLUG = :slug", slug=slug)
        return int(cursor.fetchone()[0])


def get_topic_by_slug(connection: oracledb.Connection, slug: str) -> dict[str, Any] | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ID, SLUG, TITLE, DESCRIPTION FROM TOPICS WHERE SLUG = :slug",
            slug=slug,
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": int(row[0]),
            "slug": row[1],
            "title": row[2],
            "description": row[3],
        }


def upsert_concept(
    connection: oracledb.Connection,
    *,
    topic_id: int,
    slug: str,
    label: str,
    summary: str,
    primary_topic_slug: str,
    related_topics: list[str] | None = None,
    foundational: bool = False,
) -> int:
    related_topics_json = json.dumps(related_topics or [])
    with connection.cursor() as cursor:
        cursor.execute(
            """
            MERGE INTO CONCEPTS target
            USING (
                SELECT
                    :topic_id AS TOPIC_ID,
                    :slug AS SLUG,
                    :label AS LABEL,
                    :summary AS SUMMARY,
                    :primary_topic_slug AS PRIMARY_TOPIC_SLUG,
                    :related_topics_json AS RELATED_TOPICS_JSON,
                    :foundational AS FOUNDATIONAL
                FROM dual
            ) source
            ON (target.TOPIC_ID = source.TOPIC_ID AND target.SLUG = source.SLUG)
            WHEN MATCHED THEN UPDATE SET
                target.LABEL = source.LABEL,
                target.SUMMARY = source.SUMMARY,
                target.PRIMARY_TOPIC_SLUG = source.PRIMARY_TOPIC_SLUG,
                target.RELATED_TOPICS_JSON = source.RELATED_TOPICS_JSON,
                target.FOUNDATIONAL = source.FOUNDATIONAL,
                target.UPDATED_AT = CURRENT_TIMESTAMP
            WHEN NOT MATCHED THEN INSERT (
                TOPIC_ID,
                SLUG,
                LABEL,
                SUMMARY,
                PRIMARY_TOPIC_SLUG,
                RELATED_TOPICS_JSON,
                FOUNDATIONAL
            ) VALUES (
                source.TOPIC_ID,
                source.SLUG,
                source.LABEL,
                source.SUMMARY,
                source.PRIMARY_TOPIC_SLUG,
                source.RELATED_TOPICS_JSON,
                source.FOUNDATIONAL
            )
            """,
            topic_id=topic_id,
            slug=slug,
            label=label,
            summary=summary,
            primary_topic_slug=primary_topic_slug,
            related_topics_json=related_topics_json,
            foundational=1 if foundational else 0,
        )
        cursor.execute(
            "SELECT ID FROM CONCEPTS WHERE TOPIC_ID = :topic_id AND SLUG = :slug",
            topic_id=topic_id,
            slug=slug,
        )
        return int(cursor.fetchone()[0])


def get_concept_id_by_slug(connection: oracledb.Connection, slug: str) -> int | None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ID FROM CONCEPTS WHERE SLUG = :slug FETCH FIRST 1 ROWS ONLY",
            slug=slug,
        )
        row = cursor.fetchone()
        return int(row[0]) if row else None


def upsert_concept_edge(
    connection: oracledb.Connection,
    *,
    source_concept_id: int,
    target_concept_id: int,
    edge_kind: str,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            MERGE INTO CONCEPT_EDGES target
            USING (
                SELECT :source_concept_id AS SOURCE_CONCEPT_ID,
                       :target_concept_id AS TARGET_CONCEPT_ID,
                       :edge_kind AS EDGE_KIND
                FROM dual
            ) source
            ON (
                target.SOURCE_CONCEPT_ID = source.SOURCE_CONCEPT_ID
                AND target.TARGET_CONCEPT_ID = source.TARGET_CONCEPT_ID
                AND target.EDGE_KIND = source.EDGE_KIND
            )
            WHEN NOT MATCHED THEN INSERT (
                SOURCE_CONCEPT_ID,
                TARGET_CONCEPT_ID,
                EDGE_KIND
            ) VALUES (
                source.SOURCE_CONCEPT_ID,
                source.TARGET_CONCEPT_ID,
                source.EDGE_KIND
            )
            """,
            source_concept_id=source_concept_id,
            target_concept_id=target_concept_id,
            edge_kind=edge_kind,
        )


def upsert_research_report(
    connection: oracledb.Connection,
    *,
    topic_id: int,
    title: str,
    source_path: str | None,
    version_number: int,
    content: str,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT ID FROM RESEARCH_REPORTS WHERE TOPIC_ID = :topic_id AND VERSION_NUMBER = :version_number",
            topic_id=topic_id,
            version_number=version_number,
        )
        row = cursor.fetchone()

        if row is None:
            report_id_var = cursor.var(oracledb.NUMBER)
            cursor.execute(
                """
                INSERT INTO RESEARCH_REPORTS (
                    TOPIC_ID,
                    TITLE,
                    SOURCE_PATH,
                    VERSION_NUMBER,
                    CONTENT
                ) VALUES (
                    :topic_id,
                    :title,
                    :source_path,
                    :version_number,
                    :content
                )
                RETURNING ID INTO :report_id
                """,
                topic_id=topic_id,
                title=title,
                source_path=source_path,
                version_number=version_number,
                content=content,
                report_id=report_id_var,
            )
            return int(report_id_var.getvalue()[0])

        report_id = int(row[0])
        cursor.execute(
            """
            UPDATE RESEARCH_REPORTS
            SET TITLE = :title,
                SOURCE_PATH = :source_path,
                CONTENT = :content
            WHERE ID = :report_id
            """,
            title=title,
            source_path=source_path,
            content=content,
            report_id=report_id,
        )
        return report_id


def replace_research_chunks(
    connection: oracledb.Connection,
    *,
    report_id: int,
    topic_id: int,
    chunks: list[ResearchChunk],
) -> dict[int, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM CONCEPT_CHUNK_LINKS WHERE CHUNK_ID IN (SELECT ID FROM RESEARCH_CHUNKS WHERE REPORT_ID = :report_id)",
            report_id=report_id,
        )
        cursor.execute("DELETE FROM RESEARCH_CHUNKS WHERE REPORT_ID = :report_id", report_id=report_id)

        chunk_id_by_index: dict[int, int] = {}
        for chunk in chunks:
            chunk_id_var = cursor.var(oracledb.NUMBER)
            cursor.execute(
                """
                INSERT INTO RESEARCH_CHUNKS (
                    REPORT_ID,
                    TOPIC_ID,
                    CHUNK_INDEX,
                    CHUNK_TEXT,
                    SOURCE_HEADING,
                    SOURCE_REFERENCE
                ) VALUES (
                    :report_id,
                    :topic_id,
                    :chunk_index,
                    :chunk_text,
                    :source_heading,
                    :source_reference
                )
                RETURNING ID INTO :chunk_id
                """,
                report_id=report_id,
                topic_id=topic_id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.content,
                source_heading=chunk.source_heading,
                source_reference=chunk.source_heading,
                chunk_id=chunk_id_var,
            )
            chunk_id_by_index[chunk.chunk_index] = int(chunk_id_var.getvalue()[0])

        return chunk_id_by_index


def replace_concept_chunk_links(
    connection: oracledb.Connection,
    *,
    concept_id: int,
    snippet_matches: list[tuple[str, int]],
    chunk_id_by_index: dict[int, int],
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM CONCEPT_CHUNK_LINKS WHERE CONCEPT_ID = :concept_id",
            concept_id=concept_id,
        )
        for order, (snippet_text, chunk_index) in enumerate(snippet_matches):
            chunk_id = chunk_id_by_index[chunk_index]
            cursor.execute(
                """
                INSERT INTO CONCEPT_CHUNK_LINKS (
                    CONCEPT_ID,
                    CHUNK_ID,
                    SNIPPET_TEXT,
                    SNIPPET_ORDER
                ) VALUES (
                    :concept_id,
                    :chunk_id,
                    :snippet_text,
                    :snippet_order
                )
                """,
                concept_id=concept_id,
                chunk_id=chunk_id,
                snippet_text=snippet_text,
                snippet_order=order,
            )


def load_packet_into_oracle(
    connection: oracledb.Connection,
    *,
    packet: TopicPacket,
    research_markdown: str,
) -> dict[str, Any]:
    topic_id = upsert_topic(connection, slug=packet.topic_slug, title=packet.title)

    concept_ids: dict[str, int] = {}
    for concept in packet.concepts:
        concept_ids[concept.id] = upsert_concept(
            connection,
            topic_id=topic_id,
            slug=concept.id,
            label=concept.label,
            summary=concept.summary,
            primary_topic_slug=concept.primary_topic,
            related_topics=concept.related_topics,
            foundational=concept.foundational,
        )

    for edge in packet.edges:
        source_concept_id = concept_ids.get(edge.source) or get_concept_id_by_slug(connection, edge.source)
        target_concept_id = concept_ids.get(edge.target) or get_concept_id_by_slug(connection, edge.target)
        if source_concept_id and target_concept_id:
            upsert_concept_edge(
                connection,
                source_concept_id=source_concept_id,
                target_concept_id=target_concept_id,
                edge_kind=edge.kind,
            )

    report_id = upsert_research_report(
        connection,
        topic_id=topic_id,
        title=packet.title,
        source_path=packet.source_report_path,
        version_number=1,
        content=research_markdown,
    )

    chunks = chunk_markdown(research_markdown)
    chunk_id_by_index = replace_research_chunks(
        connection,
        report_id=report_id,
        topic_id=topic_id,
        chunks=chunks,
    )

    matches = match_concept_snippets_to_chunks(packet, chunks)
    for concept in packet.concepts:
        replace_concept_chunk_links(
            connection,
            concept_id=concept_ids[concept.id],
            snippet_matches=matches.get(concept.id, []),
            chunk_id_by_index=chunk_id_by_index,
        )

    return {
        "topic_id": topic_id,
        "report_id": report_id,
        "concept_count": len(packet.concepts),
        "chunk_count": len(chunks),
    }
