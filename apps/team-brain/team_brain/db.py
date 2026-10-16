"""Oracle AI Database data layer: the ONE shared table, and the policy on it.

Every source lands in `documents`. Each row carries its embedding (a native
VECTOR column, computed in-database by the MERGE that writes the row), its
searchable text (an Oracle Text index over title + text), and the team columns
(`visibility`/`acl`/`domains`/`project`). `(source, external_id)` is unique so
re-ingestion upserts in place instead of duplicating.

What is different from a plain vector store:

  * Identity is a property of the SESSION, established through the trusted
    `tb_session` package (see access.py), and the row policy attached to
    `documents` filters every SELECT by it. The read methods below carry no
    permission SQL at all. They cannot forget to filter, because the filter is
    not theirs.
  * A session with no identity gets zero rows. Fail closed.
  * Ingestion switches the session into INGEST mode so the write path can see
    the rows it needs to upsert and tombstone.

This is PERMISSION POLICY living where it belongs: with the data. Identity is a
filter on the rows, not a separate store per person. Connectors are per source,
never per teammate. See docs/PERSONAL_VS_TEAM.md.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from team_brain.access import (
    INGEST,
    Identity,
    apply_identity,
    clear_identity,
    policy_function_sql,
    session_package_sql,
)
from team_brain.config import (
    EMBEDDING_DIMENSIONS,
    ORACLE_DSN,
    ORACLE_PASSWORD,
    ORACLE_USER,
    RETRIEVAL_BACKEND,
)
from team_brain.embeddings import clip_for_embedding, embedding_sql
from team_brain.schema import Document

_STOP_WORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "do", "does", "for",
        "from", "had", "has", "have", "he", "her", "his", "how", "i", "if", "in", "is", "it",
        "its", "may", "my", "no", "not", "of", "on", "or", "our", "out", "she", "so", "that",
        "the", "their", "them", "then", "there", "they", "this", "to", "up", "us", "was", "we",
        "went", "were", "what", "when", "which", "who", "will", "with", "would", "you",
    }
)  # fmt: skip


def _strip_stop_words(query: str) -> list[str]:
    terms = [t for t in query.strip().split() if t.lower() not in _STOP_WORDS]
    return terms or query.strip().split()


def build_contains_query(query: str) -> str:
    """Free text -> an Oracle Text CONTAINS expression.

    Alphanumeric terms only, each wrapped in braces so Oracle Text operators
    (NEAR, ABOUT, WITHIN, ...) can never be injected, joined with ACCUM so a
    document matching more terms scores higher. Empty when nothing searchable
    survives.
    """
    cleaned = []
    for t in _strip_stop_words(query):
        term = "".join(ch for ch in t if ch.isalnum())
        if term:
            cleaned.append("{" + term + "}")
    return " ACCUM ".join(cleaned)


class IdentityError(RuntimeError):
    """A read was attempted before the session established who is asking."""


_DOC_COLUMNS = "id, source, external_id, title, text, url, author, created_at, project, metadata"


class DocumentDB:
    """oracledb wrapper over the `documents` table and its policy."""

    def __init__(
        self,
        user: str | None = None,
        password: str | None = None,
        dsn: str | None = None,
        identity: Identity | None = None,
    ) -> None:
        self._user = user or ORACLE_USER
        self._password = password or ORACLE_PASSWORD
        self._dsn = dsn or ORACLE_DSN
        self._conn: Any = None
        self._identity: Identity | None = identity
        self._identity_failed = False
        self._schema: str | None = None

    # --- connection ---------------------------------------------------------
    def _get_conn(self) -> Any:
        if self._conn is None:
            oracledb.defaults.program = "devrel-developerhub-team-brain"
            import oracledb

            oracledb.defaults.fetch_lobs = False
            conn = oracledb.connect(user=self._user, password=self._password, dsn=self._dsn)
            try:
                if self._identity is not None:
                    apply_identity(conn, self._identity)
            except Exception:
                conn.close()
                self._identity = None
                self._identity_failed = True
                raise
            self._conn = conn
        return self._conn

    @property
    def connection(self) -> Any:
        """The live session (identity already applied). Used by the LangChain legs."""
        return self._get_conn()

    def close(self) -> None:
        if self._conn is not None:
            try:
                clear_identity(self._conn)
            except Exception:  # noqa: BLE001 - closing anyway
                pass
            self._conn.close()
            self._conn = None

    def commit(self) -> None:
        if self._conn is not None:
            self._conn.commit()

    def rollback(self) -> None:
        if self._conn is not None:
            self._conn.rollback()

    @property
    def schema(self) -> str:
        if self._schema is None:
            cur = self._get_conn().cursor()
            cur.execute("SELECT USER FROM dual")
            self._schema = str(cur.fetchone()[0])
        return self._schema

    @property
    def context_name(self) -> str:
        return f"{self.schema}_CTX"

    # --- identity -----------------------------------------------------------
    def set_identity(self, identity: Identity) -> None:
        """Tell the database who is asking. Every read after this is filtered by it."""
        self._identity = None
        self._identity_failed = True
        conn = self._get_conn()
        try:
            apply_identity(conn, identity)
        except Exception:
            # Discard a failed session even if the failure was not an auth error.
            # The PL/SQL package also clears context for direct SQL callers.
            self.close()
            raise
        self._identity = identity
        self._identity_failed = False

    @property
    def identity(self) -> Identity | None:
        return self._identity

    def _require_identity(self) -> None:
        if self._identity is None:
            raise IdentityError(
                "no identity on this session; call set_identity(...) before reading "
                "(the database would return zero rows anyway: fail closed)"
            )

    # --- schema -------------------------------------------------------------
    def init_schema(self) -> None:
        """Create the table, the Oracle Text index, the identity tables, the
        trusted session package, and the row policy. Idempotent."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM user_tables")
        tables = {r[0] for r in cur.fetchall()}

        if "DOCUMENTS" not in tables:
            cur.execute(
                f"""
                CREATE TABLE documents (
                    id           RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
                    source       VARCHAR2(64)   NOT NULL,
                    external_id  VARCHAR2(1000) NOT NULL,
                    title        VARCHAR2(2000),
                    text         CLOB           NOT NULL,
                    url          VARCHAR2(2000),
                    author       VARCHAR2(400),
                    created_at   TIMESTAMP WITH TIME ZONE NOT NULL,
                    project      VARCHAR2(200)  DEFAULT 'default' NOT NULL,
                    visibility   VARCHAR2(20)   DEFAULT 'public' NOT NULL,
                    acl          JSON,
                    domains      JSON,
                    metadata     JSON,
                    content_hash VARCHAR2(64)   NOT NULL,
                    embedding    VECTOR({EMBEDDING_DIMENSIONS}, FLOAT32),
                    indexed_at   TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
                    deleted_at   TIMESTAMP WITH TIME ZONE,
                    CONSTRAINT uq_documents_source_ext UNIQUE (source, external_id)
                )
                """
            )
            cur.execute("CREATE INDEX idx_documents_source ON documents(source)")
            cur.execute("CREATE INDEX idx_documents_project ON documents(project)")

        if "INGESTION_RUNS" not in tables:
            cur.execute(
                """
                CREATE TABLE ingestion_runs (
                    id          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    source      VARCHAR2(64) NOT NULL,
                    started_at  TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
                    finished_at TIMESTAMP WITH TIME ZONE,
                    upserted    NUMBER DEFAULT 0,
                    tombstoned  NUMBER DEFAULT 0,
                    error       VARCHAR2(4000)
                )
                """
            )
        conn.commit()

        # Identity tables must exist before the package that reads them compiles.
        from team_brain.access import AccessControl

        ac = AccessControl(self._user, self._password, self._dsn)
        try:
            ac.init_schema()
        finally:
            ac.close()

        self._ensure_text_index(cur)
        self._ensure_policy(cur)
        conn.commit()

    def _ensure_text_index(self, cur: Any) -> None:
        # One Oracle Text index over title + text. SYNC (ON COMMIT) keeps it
        # current transactionally, which is what a demo needs.
        cur.execute("SELECT pre_name FROM ctx_user_preferences WHERE pre_name = 'TB_MCDS'")
        if not cur.fetchone():
            cur.execute(
                """
                BEGIN
                  ctx_ddl.create_preference('TB_MCDS', 'MULTI_COLUMN_DATASTORE');
                  ctx_ddl.set_attribute('TB_MCDS', 'COLUMNS', 'title, text');
                END;
                """
            )
        cur.execute("SELECT index_name FROM user_indexes WHERE index_name = 'IDX_DOCUMENTS_TEXT'")
        if not cur.fetchone():
            cur.execute(
                """
                CREATE INDEX idx_documents_text ON documents(text)
                INDEXTYPE IS CTXSYS.CONTEXT
                PARAMETERS('DATASTORE TB_MCDS FILTER CTXSYS.NULL_FILTER
                            SECTION GROUP CTXSYS.NULL_SECTION_GROUP SYNC (ON COMMIT)')
                """
            )

    def _ensure_policy(self, cur: Any) -> None:
        ctx = self.context_name
        for stmt in session_package_sql(ctx):
            cur.execute(stmt)
        cur.execute(f"CREATE OR REPLACE CONTEXT {ctx} USING tb_session")
        cur.execute(policy_function_sql(ctx))
        cur.execute(
            "SELECT name, line, text FROM user_errors "
            "WHERE name IN ('TB_SESSION', 'TB_DOCUMENTS_POLICY') AND attribute = 'ERROR' "
            "ORDER BY name, sequence"
        )
        errs = cur.fetchall()
        if errs:
            raise RuntimeError(f"PL/SQL compile errors: {errs}")
        cur.execute(
            "SELECT policy_name FROM user_policies "
            "WHERE object_name = 'DOCUMENTS' AND policy_name = 'TB_DOCUMENTS_READ'"
        )
        if not cur.fetchone():
            cur.execute(
                """
                BEGIN
                  DBMS_RLS.ADD_POLICY(
                    object_schema   => USER,
                    object_name     => 'DOCUMENTS',
                    policy_name     => 'TB_DOCUMENTS_READ',
                    function_schema => USER,
                    policy_function => 'TB_DOCUMENTS_POLICY',
                    statement_types => 'SELECT');
                END;
                """
            )
        # Re-establish the session's identity: the package was just replaced.
        if self._identity is not None:
            apply_identity(self._get_conn(), self._identity)

    def truncate(self) -> None:
        """Wipe all rows (used by the test suite between tests)."""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("TRUNCATE TABLE documents")
        cur.execute("TRUNCATE TABLE ingestion_runs")
        conn.commit()

    # --- writes (require INGEST identity) -----------------------------------
    def _require_ingest(self) -> None:
        """Writes run in INGEST mode. A session with no identity is an operator session and
        is switched; a session that already speaks for a caller is never silently escalated."""
        if self._identity == INGEST:
            return
        if self._identity is None and not self._identity_failed:
            self.set_identity(INGEST)
            return
        raise PermissionError("write attempted without an operator identity; use an INGEST session")

    def upsert_document(self, doc: Document, embed_text: str | None = None) -> None:
        """Insert or update by (source, external_id). Resurrects if tombstoned.

        The embedding is computed by the database as part of this statement.
        `embed_text` is what gets embedded (enriched summary if any, else
        title + body); defaults to the document text.
        """
        import oracledb

        self._require_ingest()
        conn = self._get_conn()
        cur = conn.cursor()
        cur.setinputsizes(text=oracledb.DB_TYPE_CLOB)
        to_embed = clip_for_embedding(embed_text if embed_text is not None else doc.body)
        emb = embedding_sql("embed_text")
        cur.execute(
            f"""
            MERGE INTO documents d
            USING (SELECT :source AS source, :external_id AS external_id FROM dual) s
               ON (d.source = s.source AND d.external_id = s.external_id)
             WHEN MATCHED THEN UPDATE SET
                    title = :title, text = :text, url = :url, author = :author,
                    created_at = :created_at, project = :project, visibility = :visibility,
                    acl = JSON(:acl), domains = JSON(:domains), metadata = JSON(:metadata),
                    content_hash = :content_hash, embedding = {emb},
                    indexed_at = SYSTIMESTAMP, deleted_at = NULL
             WHEN NOT MATCHED THEN INSERT
                    (source, external_id, title, text, url, author, created_at, project,
                     visibility, acl, domains, metadata, content_hash, embedding)
                    VALUES (:source, :external_id, :title, :text, :url, :author, :created_at,
                            :project, :visibility, JSON(:acl), JSON(:domains), JSON(:metadata),
                            :content_hash, {emb})
            """,
            source=doc.source,
            external_id=doc.external_id,
            title=doc.title[:2000],
            text=doc.body,
            url=doc.url[:2000],
            author=doc.author[:400],
            created_at=doc.created_at,
            project=doc.project,
            visibility=doc.visibility,
            acl=json.dumps(list(doc.acl)),
            domains=json.dumps(list(doc.domains)),
            metadata=json.dumps(self._metadata_for(doc)),
            content_hash=doc.content_hash(),
            embed_text=to_embed,
        )

    @staticmethod
    def _metadata_for(doc: Document) -> dict[str, Any]:
        """The JSON `metadata` column doubles as the row LangChain's retrievers
        hand back, so it carries the columns Evidence needs."""
        md = dict(doc.metadata)
        md.update(
            {
                "source": doc.source,
                "external_id": doc.external_id,
                "title": doc.title,
                "url": doc.url,
                "author": doc.author,
                "created_at": doc.created_at.isoformat(),
                "project": doc.project,
                "domains": list(doc.domains),
                "visibility": doc.visibility,
            }
        )
        return md

    def seen_external_ids(self, source: str) -> set[str]:
        self._require_ingest()
        cur = self._get_conn().cursor()
        cur.execute(
            "SELECT external_id FROM documents WHERE source = :s AND deleted_at IS NULL",
            s=source,
        )
        return {r[0] for r in cur.fetchall()}

    def tombstone_missing(self, source: str, seen_ids: set[str]) -> int:
        """Soft-delete live rows for `source` whose external_id was not seen this sync."""
        self._require_ingest()
        cur = self._get_conn().cursor()
        if seen_ids:
            cur.execute(
                """
                UPDATE documents SET deleted_at = SYSTIMESTAMP
                 WHERE source = :s AND deleted_at IS NULL
                   AND NOT JSON_EXISTS(:seen, '$[*]?(@ == $e)' PASSING external_id AS "e")
                """,
                s=source,
                seen=json.dumps(sorted(seen_ids)),
            )
        else:
            cur.execute(
                "UPDATE documents SET deleted_at = SYSTIMESTAMP "
                "WHERE source = :s AND deleted_at IS NULL",
                s=source,
            )
        return int(cur.rowcount)

    # --- ingestion run log --------------------------------------------------
    def record_run_start(self, source: str) -> int:
        import oracledb

        conn = self._get_conn()
        cur = conn.cursor()
        out = cur.var(oracledb.NUMBER)
        cur.execute(
            "INSERT INTO ingestion_runs (source) VALUES (:s) RETURNING id INTO :rid",
            s=source,
            rid=out,
        )
        conn.commit()
        return int(out.getvalue()[0])

    def record_run_finish(
        self, run_id: int, upserted: int, tombstoned: int, error: str | None = None
    ) -> None:
        conn = self._get_conn()
        conn.cursor().execute(
            "UPDATE ingestion_runs SET finished_at = SYSTIMESTAMP, upserted = :u, "
            "tombstoned = :t, error = :e WHERE id = :id",
            u=upserted,
            t=tombstoned,
            e=(error or "")[:4000] or None,
            id=run_id,
        )
        conn.commit()

    # --- reads (the row policy filters every one of these) -------------------
    def keyword_search(self, query: str, project: str | None, limit: int) -> list[dict[str, Any]]:
        self._require_identity()
        if RETRIEVAL_BACKEND == "langchain":
            from team_brain.langchain_legs import keyword_leg

            return keyword_leg(self, query, project, limit)
        return self.keyword_search_sql(query, project, limit)

    def vector_search(self, query: str, project: str | None, limit: int) -> list[dict[str, Any]]:
        self._require_identity()
        if RETRIEVAL_BACKEND == "langchain":
            from team_brain.langchain_legs import vector_leg

            return vector_leg(self, query, project, limit)
        return self.vector_search_sql(query, project, limit)

    def keyword_search_sql(
        self, query: str, project: str | None, limit: int
    ) -> list[dict[str, Any]]:
        """Oracle Text: CONTAINS over title + text, ranked by SCORE."""
        self._require_identity()
        expr = build_contains_query(query)
        if not expr:
            return []
        cur = self._get_conn().cursor()
        cur.execute(
            f"""
            SELECT {_DOC_COLUMNS}, SCORE(1) AS score
              FROM documents
             WHERE CONTAINS(text, :q, 1) > 0
               AND (:project IS NULL OR project = :project)
             ORDER BY SCORE(1) DESC
             FETCH FIRST :lim ROWS ONLY
            """,
            q=expr,
            project=project,
            lim=limit,
        )
        # Oracle Text SCORE is 0..100; normalise to 0..1 like the FTS rank was.
        return [self._row_to_dict(r, float(r[10]) / 100.0) for r in cur.fetchall()]

    def vector_search_sql(
        self, query: str, project: str | None, limit: int
    ) -> list[dict[str, Any]]:
        """Vector search: the query is embedded in-database, cosine distance ranks."""
        self._require_identity()
        cur = self._get_conn().cursor()
        cur.execute(
            f"""
            WITH q AS (SELECT {embedding_sql("q")} AS v FROM dual)
            SELECT {_DOC_COLUMNS}, VECTOR_DISTANCE(d.embedding, q.v, COSINE) AS distance
              FROM documents d, q
             WHERE d.embedding IS NOT NULL
               AND (:project IS NULL OR d.project = :project)
             ORDER BY distance
             FETCH FIRST :lim ROWS ONLY
            """,
            q=clip_for_embedding(query),
            project=project,
            lim=limit,
        )
        # cosine similarity = 1 - cosine distance
        return [self._row_to_dict(r, 1.0 - float(r[10])) for r in cur.fetchall()]

    def who_knows(self, query: str, project: str | None, limit: int) -> list[dict[str, Any]]:
        """Rank authors by how much matching (and visible) knowledge they own."""
        self._require_identity()
        expr = build_contains_query(query)
        if not expr:
            return []
        cur = self._get_conn().cursor()
        cur.execute(
            """
            SELECT author, COUNT(*) AS doc_count, SUM(SCORE(1)) / 100 AS total_score
              FROM documents
             WHERE author IS NOT NULL AND CONTAINS(text, :q, 1) > 0
               AND (:project IS NULL OR project = :project)
             GROUP BY author
             ORDER BY total_score DESC
             FETCH FIRST :lim ROWS ONLY
            """,
            q=expr,
            project=project,
            lim=limit,
        )
        return [
            {"author": r[0], "doc_count": int(r[1]), "score": float(r[2])} for r in cur.fetchall()
        ]

    def get_document(self, row_id: str) -> dict[str, Any] | None:
        """Full text of one row by its `source::external_id` key, or None.

        None means "no such row, or not visible to this identity"; the policy
        decides which and the caller cannot tell the difference. Fail closed.
        """
        self._require_identity()
        if "::" not in row_id:
            return None
        source, external_id = row_id.split("::", 1)
        cur = self._get_conn().cursor()
        cur.execute(
            f"SELECT {_DOC_COLUMNS} FROM documents WHERE source = :s AND external_id = :e",
            s=source,
            e=external_id,
        )
        row = cur.fetchone()
        return self._row_to_dict(row, 1.0) if row else None

    def stats(self) -> dict[str, Any]:
        """Counts for the operator. Runs in INGEST mode: it is about the store, not a caller."""
        saved = self._identity
        self.set_identity(INGEST)
        try:
            cur = self._get_conn().cursor()
            cur.execute("SELECT COUNT(*) FROM documents WHERE deleted_at IS NULL")
            live = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM documents WHERE deleted_at IS NOT NULL")
            tombstoned = cur.fetchone()[0]
            cur.execute(
                "SELECT source, COUNT(*) FROM documents WHERE deleted_at IS NULL "
                "GROUP BY source ORDER BY source"
            )
            by_source = {r[0]: int(r[1]) for r in cur.fetchall()}
        finally:
            if saved is None:
                clear_identity(self._get_conn())
                self._identity = None
            elif saved != INGEST:
                self.set_identity(saved)
        return {"live_documents": int(live), "tombstoned": int(tombstoned), "by_source": by_source}

    def visible_count(self) -> int:
        """How many rows THIS session's identity may see. The demo's one-liner."""
        self._require_identity()
        cur = self._get_conn().cursor()
        cur.execute("SELECT COUNT(*) FROM documents")
        return int(cur.fetchone()[0])

    @staticmethod
    def _row_to_dict(row: tuple[Any, ...], score: float) -> dict[str, Any]:
        created = row[7]
        if isinstance(created, datetime) and created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        return {
            # Stable, human-readable key shared by both retrieval backends.
            "id": f"{row[1]}::{row[2]}",
            "source": row[1],
            "external_id": row[2],
            "title": row[3] or "",
            "body": row[4] or "",
            "url": row[5] or "",
            "author": row[6] or "",
            "created_at": created,
            "project": row[8],
            "metadata": row[9] or {},
            "score": score,
        }
