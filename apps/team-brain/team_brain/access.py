"""Access control: identity, groups, tokens, and the row policy that enforces them.

The team brain has ONE shared knowledge base, but not everyone may see all of
it. Two things make that safe, and they are deliberately separate:

  1. LABEL at ingestion.   Every document carries `domains` (ops / marketing /
     sales / ...). A label is inert on its own. It just records "this came from
     the ops space." (See schema.Document.domains.)

  2. ENFORCE at retrieval.  The label only means something because reads are
     filtered BEFORE any row reaches an LLM.

What changed in the Oracle edition: the ENFORCE step no longer lives in the
application's SQL. It lives in the database, as a row-level policy
(`DBMS_RLS`) attached to the `documents` table. The policy reads the caller's
identity from an application context that ONLY a trusted PL/SQL package
(`tb_session`) can write. So:

  * Any session that has not established an identity sees zero rows. That
    includes the schema owner opening a SQL client without an identity. The
    owner remains trusted: it can set INGEST mode or change the policy.
  * The application cannot forge an identity by writing the context directly;
    the kernel rejects it (ORA-01031). Identity goes through `tb_session`.
  * An unknown principal or an unknown token raises inside the database
    (ORA-20401 / ORA-20402). Fail closed, never a silent narrower view.
  * Ingestion runs in a separate INGEST mode so upserts can see every row.

The three admin tables (principals, group_grants, mcp_tokens) are the inputs
the package resolves from. Tokens are stored HASHED.

Scope note (POC): tokens are static opaque strings. A production deployment
would issue short-lived, audience-bound tokens from an identity provider (MCP
spec 2025-11-25: OAuth 2.1 resource server). The enforcement model, resolve
identity in the database and filter pre-retrieval, fail closed, is unchanged.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from team_brain.config import ORACLE_DSN, ORACLE_PASSWORD, ORACLE_USER


def hash_token(token: str) -> str:
    """Stable, one-way fingerprint. Only the hash is ever stored."""
    return hashlib.sha256(token.strip().encode()).hexdigest()


# --- Identity: how a database session says who is asking -------------------

IdentityKind = Literal["token", "principal", "user", "anonymous", "ingest"]


@dataclass(frozen=True)
class Identity:
    """What a session presents to `tb_session` before it reads.

    token      -> resolved by the database from mcp_tokens (the MCP path)
    principal  -> a username the database resolves to its group grant (CLI/tests)
    user       -> a raw username with NO domain grant, ACL-checked only
                  (the workshop's legacy `--user alice` path; still fail-closed
                  on restricted docs the user is not listed on)
    anonymous  -> a real identity with no grant: public, company-wide rows only
    ingest     -> the write path; sees every row so MERGE/tombstone can work
    """

    kind: IdentityKind
    value: str = ""

    @staticmethod
    def token(token: str) -> Identity:
        return Identity("token", token)

    @staticmethod
    def principal(username: str) -> Identity:
        return Identity("principal", username)

    @staticmethod
    def user(username: str) -> Identity:
        return Identity("user", username)

    @staticmethod
    def anonymous() -> Identity:
        return Identity("anonymous")

    @staticmethod
    def ingest() -> Identity:
        return Identity("ingest")


INGEST = Identity.ingest()
ANONYMOUS_IDENTITY = Identity.anonymous()


class AccessError(RuntimeError):
    """A token or principal did not resolve. Access denied (fail closed)."""


def apply_identity(conn: Any, identity: Identity) -> None:
    """Establish `identity` on this database session via the trusted package.

    Raises AccessError when the database rejects the token/principal.
    """
    oracledb.defaults.program = "devrel-developerhub-team-brain"
    import oracledb

    cur = conn.cursor()
    try:
        if identity.kind == "token":
            cur.callproc("tb_session.set_principal_by_token", [hash_token(identity.value)])
        elif identity.kind == "principal":
            cur.callproc("tb_session.set_principal", [identity.value])
        elif identity.kind == "user":
            cur.callproc("tb_session.set_user", [identity.value])
        elif identity.kind == "anonymous":
            cur.callproc("tb_session.set_anonymous")
        elif identity.kind == "ingest":
            cur.callproc("tb_session.set_ingest")
        else:  # pragma: no cover - exhaustive
            raise ValueError(f"unknown identity kind {identity.kind!r}")
    except oracledb.DatabaseError as exc:
        (err,) = exc.args
        if getattr(err, "code", 0) in (20401, 20402):
            raise AccessError(str(err.message).splitlines()[0]) from exc
        raise


def clear_identity(conn: Any) -> None:
    conn.cursor().callproc("tb_session.clear")


# --- The resolved caller (for whoami / display) ------------------------------


@dataclass(frozen=True)
class Principal:
    """A resolved caller: their identity plus the domain grant the database enforces."""

    username: str
    display_name: str
    groups: list[str] = field(default_factory=list)
    domains: frozenset[str] = frozenset()
    all_domains: bool = False  # leadership: sees every domain, incl. future ones

    def describe(self) -> str:
        scope = "ALL domains" if self.all_domains else (", ".join(sorted(self.domains)) or "none")
        return f"{self.username} ({self.display_name}) -> {scope}"


ANONYMOUS = Principal(username="anonymous", display_name="Anonymous (no token)")


# --- DDL: the trusted package and the row policy ------------------------------


def session_package_sql(context_name: str) -> list[str]:
    """PL/SQL for the trusted session package bound to `context_name`.

    Only this package may write the context (CREATE CONTEXT ... USING tb_session),
    which is what stops a caller from granting itself a domain.
    """
    ctx = context_name.upper()
    spec = """
CREATE OR REPLACE PACKAGE tb_session AS
  PROCEDURE set_principal(p_username IN VARCHAR2);
  PROCEDURE set_principal_by_token(p_token_hash IN VARCHAR2);
  PROCEDURE set_user(p_username IN VARCHAR2);
  PROCEDURE set_anonymous;
  PROCEDURE set_ingest;
  PROCEDURE clear;
END tb_session;
"""
    body = f"""
CREATE OR REPLACE PACKAGE BODY tb_session AS
  C_CTX CONSTANT VARCHAR2(30) := '{ctx}';

  PROCEDURE reset_ IS
  BEGIN
    DBMS_SESSION.CLEAR_CONTEXT(C_CTX);
  END;

  -- Identity + group grant, resolved from the admin tables. Unknown => raise.
  PROCEDURE set_principal(p_username IN VARCHAR2) IS
    v_display   principals.display_name%TYPE;
    v_groups    principals.groups%TYPE;
    v_domains   VARCHAR2(4000) := ',';
    v_all       VARCHAR2(1) := 'N';
  BEGIN
    reset_;
    BEGIN
      SELECT display_name, groups INTO v_display, v_groups
        FROM principals WHERE username = p_username;
    EXCEPTION WHEN NO_DATA_FOUND THEN
      RAISE_APPLICATION_ERROR(-20401, 'unknown principal: ' || p_username);
    END;
    FOR g IN (
      SELECT gg.domains, gg.all_domains
        FROM group_grants gg
       WHERE gg.group_name IN (
         SELECT jt.g FROM JSON_TABLE(v_groups, '$[*]' COLUMNS (g VARCHAR2(200) PATH '$')) jt)
    ) LOOP
      IF g.all_domains = 1 THEN v_all := 'Y'; END IF;
      FOR d IN (SELECT jt.d
                  FROM JSON_TABLE(g.domains, '$[*]' COLUMNS (d VARCHAR2(200) PATH '$')) jt) LOOP
        IF INSTR(v_domains, ',' || d.d || ',') = 0 THEN
          v_domains := v_domains || d.d || ',';
        END IF;
      END LOOP;
    END LOOP;
    reset_;
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'MODE', 'READ');
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'USERNAME', p_username);
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'DISPLAY_NAME', v_display);
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'DOMAINS', v_domains);
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'ALL_DOMAINS', v_all);
  EXCEPTION WHEN OTHERS THEN
    reset_;
    RAISE;
  END;

  -- The MCP path: an opaque token, hashed by the caller, resolved here.
  PROCEDURE set_principal_by_token(p_token_hash IN VARCHAR2) IS
    v_username mcp_tokens.username%TYPE;
  BEGIN
    reset_;
    BEGIN
      SELECT username INTO v_username FROM mcp_tokens WHERE token_hash = p_token_hash;
    EXCEPTION WHEN NO_DATA_FOUND THEN
      RAISE_APPLICATION_ERROR(-20402, 'unknown token');
    END;
    set_principal(v_username);
  EXCEPTION WHEN OTHERS THEN
    reset_;
    RAISE;
  END;

  -- Raw username with NO domain grant (ACL-only). It sees company-wide rows and
  -- restricted rows whose acl names it; it never sees a domain-labelled row.
  -- The workshop's legacy path, kept for undomained knowledge bases.
  PROCEDURE set_user(p_username IN VARCHAR2) IS
  BEGIN
    reset_;
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'MODE', 'READ');
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'USERNAME', p_username);
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'DISPLAY_NAME', p_username);
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'DOMAINS', ',');
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'ALL_DOMAINS', 'N');
  END;

  PROCEDURE set_anonymous IS
  BEGIN
    reset_;
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'MODE', 'READ');
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'USERNAME', 'anonymous');
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'DISPLAY_NAME', 'Anonymous (no token)');
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'DOMAINS', ',');
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'ALL_DOMAINS', 'N');
  END;

  PROCEDURE set_ingest IS
  BEGIN
    reset_;
    DBMS_SESSION.SET_CONTEXT(C_CTX, 'MODE', 'INGEST');
  END;

  PROCEDURE clear IS
  BEGIN
    reset_;
  END;
END tb_session;
"""
    return [spec.strip(), body.strip()]


def policy_function_sql(context_name: str) -> str:
    """The row policy. Returns the predicate the kernel appends to every SELECT.

    Four gates, all AND'd (most-restrictive wins = fail-closed):
      liveness   - tombstoned rows never surface
      ACL gate   - per-document: public, or the caller is explicitly listed
      domain gate- company-wide (no label), OR the caller has all domains, OR
                   the caller's granted domains overlap the document's labels
      no identity- '1=0': a session that never said who it is sees nothing
    INGEST mode returns no predicate so the write path can see every row.
    """
    ctx = context_name.upper()
    return f"""
CREATE OR REPLACE FUNCTION tb_documents_policy(p_schema IN VARCHAR2, p_object IN VARCHAR2)
RETURN VARCHAR2 IS
  v_mode VARCHAR2(20) := SYS_CONTEXT('{ctx}', 'MODE');
BEGIN
  IF v_mode = 'INGEST' THEN
    RETURN NULL;
  END IF;
  IF v_mode IS NULL THEN
    RETURN '1=0';
  END IF;
  RETURN q'~deleted_at IS NULL
    AND (visibility = 'public'
         OR JSON_EXISTS(acl, '$[*]?(@ == $u)' PASSING SYS_CONTEXT('{ctx}', 'USERNAME') AS "u"))
    AND (JSON_VALUE(domains, '$.size()') = 0
         OR SYS_CONTEXT('{ctx}', 'ALL_DOMAINS') = 'Y'
         OR EXISTS (SELECT 1
                      FROM JSON_TABLE(domains, '$[*]' COLUMNS (d VARCHAR2(200) PATH '$')) jt
                     WHERE INSTR(SYS_CONTEXT('{ctx}', 'DOMAINS'), ',' || jt.d || ',') > 0))~';
END tb_documents_policy;
""".strip()


# --- Admin over the identity tables ------------------------------------------


class AccessControl:
    """Thin oracledb wrapper over principals / group_grants / mcp_tokens."""

    def __init__(
        self, user: str | None = None, password: str | None = None, dsn: str | None = None
    ) -> None:
        self._user = user or ORACLE_USER
        self._password = password or ORACLE_PASSWORD
        self._dsn = dsn or ORACLE_DSN
        self._conn: Any = None

    def _get_conn(self) -> Any:
        if self._conn is None:
            import oracledb

            oracledb.defaults.fetch_lobs = False
            self._conn = oracledb.connect(user=self._user, password=self._password, dsn=self._dsn)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def commit(self) -> None:
        if self._conn is not None:
            self._conn.commit()

    # --- schema -------------------------------------------------------------
    def init_schema(self) -> None:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM user_tables")
        existing = {r[0] for r in cur.fetchall()}
        if "PRINCIPALS" not in existing:
            cur.execute(
                """
                CREATE TABLE principals (
                    username     VARCHAR2(200) PRIMARY KEY,
                    display_name VARCHAR2(400) DEFAULT '' NOT NULL,
                    groups       JSON NOT NULL
                )
                """
            )
        if "GROUP_GRANTS" not in existing:
            cur.execute(
                """
                CREATE TABLE group_grants (
                    group_name  VARCHAR2(200) PRIMARY KEY,
                    domains     JSON NOT NULL,
                    all_domains NUMBER(1) DEFAULT 0 NOT NULL
                )
                """
            )
        if "MCP_TOKENS" not in existing:
            cur.execute(
                """
                CREATE TABLE mcp_tokens (
                    token_hash VARCHAR2(64) PRIMARY KEY,
                    username   VARCHAR2(200) NOT NULL,
                    label      VARCHAR2(400) DEFAULT '' NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL
                )
                """
            )
        conn.commit()

    def clear(self) -> None:
        conn = self._get_conn()
        cur = conn.cursor()
        for t in ("principals", "group_grants", "mcp_tokens"):
            cur.execute(f"DELETE FROM {t}")
        conn.commit()

    # --- writes -------------------------------------------------------------
    def upsert_group_grant(
        self, group_name: str, domains: list[str], all_domains: bool = False
    ) -> None:
        import json

        self._get_conn().cursor().execute(
            """
            MERGE INTO group_grants g USING (SELECT :name AS group_name FROM dual) s
               ON (g.group_name = s.group_name)
             WHEN MATCHED THEN UPDATE SET domains = JSON(:domains), all_domains = :all_d
             WHEN NOT MATCHED THEN INSERT (group_name, domains, all_domains)
                  VALUES (:name, JSON(:domains), :all_d)
            """,
            name=group_name,
            domains=json.dumps(list(domains)),
            all_d=1 if all_domains else 0,
        )

    def upsert_principal(self, username: str, display_name: str, groups: list[str]) -> None:
        import json

        self._get_conn().cursor().execute(
            """
            MERGE INTO principals p USING (SELECT :username AS username FROM dual) s
               ON (p.username = s.username)
             WHEN MATCHED THEN UPDATE SET display_name = :display_name, groups = JSON(:groups)
             WHEN NOT MATCHED THEN INSERT (username, display_name, groups)
                  VALUES (:username, :display_name, JSON(:groups))
            """,
            username=username,
            display_name=display_name,
            groups=json.dumps(list(groups)),
        )

    def add_token(self, token: str, username: str, label: str = "") -> None:
        self._get_conn().cursor().execute(
            """
            MERGE INTO mcp_tokens t USING (SELECT :h AS token_hash FROM dual) s
               ON (t.token_hash = s.token_hash)
             WHEN MATCHED THEN UPDATE SET username = :username, label = :label
             WHEN NOT MATCHED THEN INSERT (token_hash, username, label)
                  VALUES (:h, :username, :label)
            """,
            h=hash_token(token),
            username=username,
            label=label,
        )

    # --- reads (display only; enforcement is the database's job) -------------
    def _resolve_grant(self, groups: list[str]) -> tuple[frozenset[str], bool]:
        if not groups:
            return frozenset(), False
        cur = self._get_conn().cursor()
        binds = ", ".join(f":g{i}" for i in range(len(groups)))
        cur.execute(
            f"SELECT domains, all_domains FROM group_grants WHERE group_name IN ({binds})",
            {f"g{i}": g for i, g in enumerate(groups)},
        )
        domains: set[str] = set()
        all_domains = False
        for row_domains, row_all in cur.fetchall():
            domains.update(row_domains or [])
            all_domains = all_domains or bool(row_all)
        return frozenset(domains), all_domains

    def get_principal(self, username: str) -> Principal | None:
        cur = self._get_conn().cursor()
        cur.execute(
            "SELECT username, display_name, groups FROM principals WHERE username = :u",
            u=username,
        )
        row = cur.fetchone()
        if not row:
            return None
        groups = list(row[2] or [])
        domains, all_domains = self._resolve_grant(groups)
        return Principal(row[0], row[1], groups, domains, all_domains)

    def resolve_token(self, token: str) -> Principal | None:
        """Opaque token -> principal, or None if unknown (fail closed)."""
        if not token or not token.strip():
            return None
        cur = self._get_conn().cursor()
        cur.execute("SELECT username FROM mcp_tokens WHERE token_hash = :h", h=hash_token(token))
        row = cur.fetchone()
        if not row:
            return None
        return self.get_principal(row[0])

    def list_principals(self) -> list[Principal]:
        cur = self._get_conn().cursor()
        cur.execute("SELECT username FROM principals ORDER BY username")
        names = [r[0] for r in cur.fetchall()]
        return [p for p in (self.get_principal(n) for n in names) if p is not None]

    def current_session_identity(self, conn: Any, context_name: str) -> Principal:
        """Read back what the database resolved for this session (for whoami)."""
        cur = conn.cursor()
        cur.execute(
            f"""SELECT SYS_CONTEXT('{context_name}', 'USERNAME'),
                       SYS_CONTEXT('{context_name}', 'DISPLAY_NAME'),
                       SYS_CONTEXT('{context_name}', 'DOMAINS'),
                       SYS_CONTEXT('{context_name}', 'ALL_DOMAINS')
                  FROM dual"""
        )
        username, display, domains, all_d = cur.fetchone()
        parsed = frozenset(d for d in (domains or "").split(",") if d)
        return Principal(username or "", display or "", [], parsed, all_d == "Y")


def seed_access(ac: AccessControl, spec: dict[str, Any]) -> dict[str, str]:
    """Seed groups, principals, and tokens from a spec dict. Idempotent.

    Returns {username: token} so a `seed` command can print them for client config.
    """
    ac.init_schema()
    for name, grant in (spec.get("groups") or {}).items():
        ac.upsert_group_grant(
            name, list(grant.get("domains", [])), bool(grant.get("all_domains", False))
        )
    for username, p in (spec.get("principals") or {}).items():
        ac.upsert_principal(username, p.get("display_name", username), list(p.get("groups", [])))
    tokens: dict[str, str] = {}
    for username, token in (spec.get("tokens") or {}).items():
        ac.add_token(token, username, label=f"{username} dev token")
        tokens[username] = token
    ac.commit()
    return tokens


def load_access_spec(path: str | Path) -> dict[str, Any]:
    import yaml

    return dict(yaml.safe_load(Path(path).read_text(encoding="utf-8")))
