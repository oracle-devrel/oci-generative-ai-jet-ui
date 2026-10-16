"""Database-level guarantees — proofs that hold even with every Python-side
identity check deleted, because the enforcement lives in the database itself:

  (a) a brand-new session with NO identity established sees ZERO rows from a
      plain `SELECT COUNT(*) FROM documents`; the same session in INGEST mode
      sees everything. This is the row policy (DBMS_RLS), not app code.
  (b) an ordinary session cannot forge its own context value — only the
      trusted `tb_session` package (bound via `CREATE CONTEXT ... USING`) may
      write it. The kernel refuses with ORA-01031.
  (c) an unknown token / unknown principal is rejected INSIDE the database
      (ORA-20402 / ORA-20401), surfaced to Python as AccessError.
  (d) the raw-SQL retrieval legs (`keyword_search_sql` / `vector_search_sql`)
      and the LangChain legs (`langchain_legs.keyword_leg` / `vector_leg`)
      return identical (id, score) lists for the same query/identity/project —
      both are plain SQL over the same policy-protected table.
  (e) a raw username (`Identity.user`) has no domain grant: it never sees a
      domain-labelled row, so the CLI default identity cannot bypass the demo.
"""

from __future__ import annotations

from datetime import UTC, datetime

import oracledb
import pytest

from team_brain import langchain_legs as lc
from team_brain.access import AccessError, Identity
from team_brain.config import ORACLE_DSN, ORACLE_PASSWORD, ORACLE_USER
from team_brain.db import DocumentDB, IdentityError
from team_brain.schema import Document
oracledb.defaults.program = "devrel-developerhub-team-brain"

pytestmark = pytest.mark.requires_oracle


def _raw_connection() -> oracledb.Connection:
    """A brand-new oracledb connection as the schema owner — no identity applied."""
    oracledb.defaults.fetch_lobs = False
    return oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)


def test_no_identity_session_sees_zero_rows_ingest_sees_all(db: DocumentDB) -> None:
    db.upsert_document(Document("md", "seed", "Seed", "seed content", datetime.now(UTC)))
    db.commit()

    conn = _raw_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM documents")
        assert cur.fetchone()[0] == 0  # fail closed: no identity, no rows

        cur.callproc("tb_session.set_ingest")
        cur.execute("SELECT COUNT(*) FROM documents")
        assert cur.fetchone()[0] == 1  # INGEST mode: unfiltered
    finally:
        conn.close()


def test_app_session_cannot_forge_context(db: DocumentDB) -> None:
    """Only tb_session may write the app context; a direct SET_CONTEXT is refused."""
    conn = db.connection
    cur = conn.cursor()
    with pytest.raises(oracledb.DatabaseError) as excinfo:
        cur.execute(
            f"BEGIN DBMS_SESSION.SET_CONTEXT('{db.context_name}', 'ALL_DOMAINS', 'Y'); END;"
        )
    (err,) = excinfo.value.args
    assert err.code == 1031  # ORA-01031: insufficient privileges


def test_unknown_token_and_principal_are_rejected(db: DocumentDB) -> None:
    with pytest.raises(AccessError):
        db.set_identity(Identity.token("bogus"))
    with pytest.raises(AccessError):
        db.set_identity(Identity.principal("nobody"))


@pytest.mark.parametrize("initial", ["brian", "ingest"])
@pytest.mark.parametrize(
    "procedure,value,code",
    [("set_principal_by_token", "bogus", 20402), ("set_principal", "nobody", 20401)],
)
def test_failed_authentication_clears_raw_database_context(
    db: DocumentDB, tokens: dict[str, str], initial: str, procedure: str, value: str, code: int
) -> None:
    db.upsert_document(
        Document("md", "secret", "Secret", "sales policy", datetime.now(UTC), domains=["sales"])
    )
    db.commit()
    with _raw_connection() as conn:
        cur = conn.cursor()
        if initial == "ingest":
            cur.callproc("tb_session.set_ingest")
        else:
            cur.callproc("tb_session.set_principal", [initial])
        cur.execute("SELECT COUNT(*) FROM documents")
        assert cur.fetchone()[0] == 1
        with pytest.raises(oracledb.DatabaseError) as error:
            cur.callproc(f"tb_session.{procedure}", [value])
        assert error.value.args[0].code == code
        cur.execute("SELECT COUNT(*) FROM documents")
        assert cur.fetchone()[0] == 0
        cur.execute(f"SELECT SYS_CONTEXT('{db.context_name}', 'MODE') FROM dual")
        assert cur.fetchone()[0] is None
        cur.callproc("tb_session.set_principal", ["brian"])
        cur.execute("SELECT COUNT(*) FROM documents")
        assert cur.fetchone()[0] == 1


@pytest.mark.parametrize("lazy", [False, True])
def test_failed_python_identity_cannot_read_or_silently_become_ingest(
    db: DocumentDB, tokens: dict[str, str], lazy: bool
) -> None:
    doc = Document("md", "secret", "Secret", "sales policy", datetime.now(UTC), domains=["sales"])
    db.upsert_document(doc)
    db.commit()
    reader = DocumentDB(identity=Identity.token("bogus") if lazy else Identity.principal("brian"))
    try:
        if lazy:
            with pytest.raises(AccessError):
                _ = reader.connection
        else:
            assert reader.visible_count() == 1
            with pytest.raises(AccessError):
                reader.set_identity(Identity.token("bogus"))
        assert reader.identity is None
        with pytest.raises(IdentityError):
            reader.get_document("md::secret")
        with pytest.raises(PermissionError):
            reader.upsert_document(doc)
        cur = reader.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM documents")
        assert cur.fetchone()[0] == 0
        reader.set_identity(Identity.principal("brian"))
        assert reader.visible_count() == 1
    finally:
        reader.close()


_PARITY_DOCS = [
    # source, external_id, title, body, author, project, domains
    (
        "markdown",
        "deploy.md",
        "Deploy runbook",
        "We deploy the billing service with a blue-green rollout. "
        "Roll back by promoting the previous release.",
        "alice",
        "default",
        [],
    ),
    (
        "markdown",
        "oncall.md",
        "On-call rotation",
        "The on-call rotation hands over Monday at 9am. Unacknowledged pages "
        "escalate to the secondary.",
        "bob",
        "platform",
        [],
    ),
    (
        "slack",
        "ops:1",
        "onnxruntime pin",
        "Why is onnxruntime pinned below 1.26? Because FastEmbed breaks on newer builds.",
        "jeff",
        "default",
        ["ops"],
    ),
    (
        "slack",
        "sales:1",
        "Deal desk",
        "Sales pipeline: the Acme deal closes at 40k with a discount.",
        "sam",
        "default",
        ["sales"],
    ),
]

_PARITY_QUERIES = [
    "how do we deploy billing",
    "onnxruntime pinned",
    "when does on-call hand over",
    "acme deal",
]


def _pairs(rows: list[dict[str, object]]) -> list[tuple[str, float]]:
    return [(str(r["id"]), round(float(r["score"]), 3)) for r in rows]  # type: ignore[arg-type]


def test_sql_and_langchain_legs_agree(db: DocumentDB, tokens: dict[str, str]) -> None:
    now = datetime.now(UTC)
    for source, ext, title, body, author, project, domains in _PARITY_DOCS:
        db.upsert_document(
            Document(source, ext, title, body, now, author=author, project=project, domains=domains)
        )
    db.commit()

    for who in (Identity.principal("brian"), Identity.principal("jeff"), Identity.user("alice")):
        db.set_identity(who)
        for q in _PARITY_QUERIES:
            for proj in (None, "platform"):
                sql_kw = _pairs(db.keyword_search_sql(q, proj, 10))
                lc_kw = _pairs(lc.keyword_leg(db, q, proj, 10))
                sql_v = _pairs(db.vector_search_sql(q, proj, 10))
                lc_v = _pairs(lc.vector_leg(db, q, proj, 10))
                assert sql_kw == lc_kw, (who, q, proj, "keyword", sql_kw, lc_kw)
                assert sql_v == lc_v, (who, q, proj, "vector", sql_v, lc_v)


def test_raw_user_has_no_domain_grant(db: DocumentDB) -> None:
    """`Identity.user` (the CLI default) is ACL-only: company-wide rows yes, domain rows never."""
    now = datetime.now(UTC)
    db.upsert_document(Document("md", "public", "Deploy runbook", "blue-green deploy steps", now))
    db.upsert_document(
        Document("md", "sales", "Deal desk", "discount ceiling policy", now, domains=["sales"])
    )
    db.commit()

    db.set_identity(Identity.user("demo"))
    assert db.visible_count() == 1
    ids = {r["id"] for r in db.keyword_search("discount ceiling policy", None, limit=5)}
    assert "md::sales" not in ids
    ids = {r["id"] for r in db.keyword_search("deploy steps", None, limit=5)}
    assert "md::public" in ids


def test_project_keyword_filter_precedes_limit(db: DocumentDB) -> None:
    now = datetime.now(UTC)
    for i in range(5):
        db.upsert_document(
            Document(
                "md",
                f"other-{i}",
                "quasar nebula pulsar",
                "quasar nebula pulsar " * 20,
                now,
                project="elsewhere",
            )
        )
    db.upsert_document(
        Document("md", "target", "quasar", "quasar ordinary text", now, project="desired")
    )
    db.upsert_document(
        Document(
            "md",
            "secret",
            "quasar nebula pulsar",
            "quasar nebula pulsar",
            now,
            project="desired",
            visibility="restricted",
            acl=["member"],
        )
    )
    db.commit()
    db.set_identity(Identity.anonymous())
    expected = db.keyword_search_sql("quasar nebula pulsar", "desired", 1)
    actual = lc.keyword_leg(db, "quasar nebula pulsar", "desired", 1)
    assert [r["id"] for r in expected] == ["md::target"]
    assert _pairs(actual) == _pairs(expected)
    assert lc.keyword_leg(db, "quasar", "missing", 1) == []
    assert lc.keyword_leg(db, "quasar", "desired' OR '1'='1", 1) == []
