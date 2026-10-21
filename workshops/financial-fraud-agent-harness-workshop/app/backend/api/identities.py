"""Identity registry for the "Use As:" selector.

The AGENT database user is always the actual session principal. Identities here
are *application-layer personas* layered on top: each one carries a clearance
level, a list of authorized regions (AMERICAS / EUROPE / MIDDLE_EAST /
ASIA_PACIFIC), and a set of columns that should be masked when read.

This module is the **single source of truth** for those rules. It is consumed
by:

  * `api/data_routes.py` and `agent/tools.py` — which push the persona into the
    database session via `db/deep_security.py` before every read, so the kernel
    enforces the rules, and keep the Python filters as defence in depth.
  * `scripts/setup_deep_security.py` — which projects the same registry into
    either Oracle Deep Data Security data grants (26ai Enterprise-class) or
    `DBMS_RLS` policies driven by the `EDA_CTX` application context (26ai Free,
    which is what the shipped Codespace runs).

So there are two enforcement layers, and they cannot disagree: both are derived
from the data below. See `docs/reference/deep-data-security.md` and
`db/deep_security.py` (the installer lives in `scripts/setup_deep_security.py`).

Personas in this file are tuned so that *every* commonly-viewed table changes
visibly when you switch identities. That makes the security model legible at a
glance: pick `agent` and you see masks; pick `cfo` and they vanish; pick a
regional analyst and rows drop too. Only `compliance.officer` can read the
SAR_REPORTS table.

NOTE: every entry in `mask_cols` must name a column that actually exists. A
mask naming a nonexistent column is a silent no-op in Python and an ORA-23607
the moment it reaches the database; this file previously shipped
`FINANCE.ACCOUNTS.ACCOUNT_NUMBER`, which never existed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Identity:
    """One persona the user can act as.

    `regions`     — None means "all regions"; a list narrows transaction /
                    account / customer / branch / merchant / loan visibility
                    to those `region` values.
    `mask_cols`   — fully-qualified `SCHEMA.TABLE.COLUMN` strings that should
                    come back as `[REDACTED]` (the value is dropped after fetch).
    `forbid_tables` — fully-qualified table names the persona cannot read.
    """

    id: str
    label: str
    description: str
    clearance: str
    regions: list[str] | None = None
    mask_cols: list[str] = field(default_factory=list)
    forbid_tables: list[str] = field(default_factory=list)

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


# Common mask sets, named so identities can share them without duplication.
_PII_CUSTOMER_MASKS = [
    "FINANCE.CUSTOMERS.SSN",
]
_ACCOUNT_IDENTIFIER_MASKS = [
    # ACCOUNTS has no ACCOUNT_NUMBER column; the sensitive value that exists is
    # the balance. Masking a column that does not exist is a silent no-op, so
    # this list is kept honest — every entry must resolve to a real column.
    "FINANCE.ACCOUNTS.BALANCE_CENTS",
    "FINANCE.CARDS.CARD_NUMBER",
]
_FINANCIAL_VALUE_MASKS = [
    "FINANCE.TRANSACTIONS.AMOUNT_CENTS",
]
_SAR_NARRATIVE_MASKS = [
    "FINANCE.SAR_REPORTS.NARRATIVE",
]
_AGENT_ADMIN_TABLES = [
    "AGENT.AGENT_AUTHORIZATIONS",
    "AGENT.AGENT_CLEARANCES",
    "AGENT.SCHEMA_ACL",
]
_SAR_TABLE = [
    "FINANCE.SAR_REPORTS",
]


# Registry. Order is the order they show up in the UI dropdown.
IDENTITIES: dict[str, Identity] = {
    "agent": Identity(
        id="agent",
        label="Analyst (default)",
        description=(
            "Default low-privilege application persona. Sees operational bank "
            "data but customer SSNs, account balances and card numbers, "
            "transaction amounts, and SAR narratives are masked, and the "
            "SAR_REPORTS table is out of reach. Use cfo for unrestricted "
            "financials, or compliance.officer for SAR access."
        ),
        clearance="STANDARD",
        regions=None,
        mask_cols=[
            *_PII_CUSTOMER_MASKS,
            *_ACCOUNT_IDENTIFIER_MASKS,
            *_FINANCIAL_VALUE_MASKS,
            *_SAR_NARRATIVE_MASKS,
        ],
        forbid_tables=[*_SAR_TABLE, *_AGENT_ADMIN_TABLES],
    ),
    "cfo": Identity(
        id="cfo",
        label="CFO — Executive",
        description=(
            "Executive clearance. Sees every row in every region and every "
            "financial column unmasked — the persona to use when you want to "
            "compare a redacted view against the truth. The one thing even "
            "the CFO cannot open is the SAR_REPORTS table: that is "
            "compliance-only."
        ),
        clearance="EXECUTIVE",
        regions=None,
        mask_cols=[],
        forbid_tables=[*_SAR_TABLE, *_AGENT_ADMIN_TABLES],
    ),
    "compliance.officer": Identity(
        id="compliance.officer",
        label="Compliance Officer",
        description=(
            "Executive clearance with the ONLY read access to FINANCE."
            "SAR_REPORTS — the AML investigation table. Sees everything, "
            "unmasked, in every region. Use this persona for the fraud "
            "investigation storylines."
        ),
        clearance="EXECUTIVE",
        regions=None,
        mask_cols=[],
        forbid_tables=_AGENT_ADMIN_TABLES,
    ),
    "analyst.east": Identity(
        id="analyst.east",
        label="Analyst — Europe & Middle East",
        description=(
            "Standard clearance, EUROPE + MIDDLE_EAST only. Transactions, "
            "accounts, cards, branches, merchants, and loans restricted to "
            "those regions. Customer SSNs, account balances and card numbers, "
            "transaction amounts, and SAR narratives are all masked."
        ),
        clearance="STANDARD",
        regions=["EUROPE", "MIDDLE_EAST"],
        mask_cols=[
            *_PII_CUSTOMER_MASKS,
            *_ACCOUNT_IDENTIFIER_MASKS,
            *_FINANCIAL_VALUE_MASKS,
            *_SAR_NARRATIVE_MASKS,
        ],
        forbid_tables=[*_SAR_TABLE, *_AGENT_ADMIN_TABLES],
    ),
    "analyst.west": Identity(
        id="analyst.west",
        label="Analyst — Americas & Asia-Pacific",
        description=(
            "Standard clearance, AMERICAS + ASIA_PACIFIC only. Same column "
            "masks as analyst.east; rows outside the two authorized regions "
            "are dropped."
        ),
        clearance="STANDARD",
        regions=["AMERICAS", "ASIA_PACIFIC"],
        mask_cols=[
            *_PII_CUSTOMER_MASKS,
            *_ACCOUNT_IDENTIFIER_MASKS,
            *_FINANCIAL_VALUE_MASKS,
            *_SAR_NARRATIVE_MASKS,
        ],
        forbid_tables=[*_SAR_TABLE, *_AGENT_ADMIN_TABLES],
    ),
    "ops.viewer": Identity(
        id="ops.viewer",
        label="Risk Ops Viewer",
        description=(
            "Read-only operations persona. Sees branch, merchant, and "
            "transaction traffic but customer records and SAR investigations "
            "are off-limits entirely; account balances, card numbers and "
            "transaction amounts stay masked. Useful for dashboards that must "
            "never leak customer PII."
        ),
        clearance="STANDARD",
        regions=None,
        mask_cols=[
            *_ACCOUNT_IDENTIFIER_MASKS,
            *_FINANCIAL_VALUE_MASKS,
        ],
        forbid_tables=[
            "FINANCE.CUSTOMERS",
            "FINANCE.SAR_REPORTS",
            *_AGENT_ADMIN_TABLES,
        ],
    ),
}


DEFAULT_IDENTITY = "agent"


def get_identity(identity_id: str | None) -> Identity:
    """Return the identity with this id, falling back to AGENT on miss."""
    if not identity_id:
        return IDENTITIES[DEFAULT_IDENTITY]
    return IDENTITIES.get(identity_id, IDENTITIES[DEFAULT_IDENTITY])


def list_identities() -> list[dict[str, Any]]:
    """Return every identity in registration order, JSON-serializable."""
    return [i.as_json() for i in IDENTITIES.values()]


# ----- Filter helpers used by data_routes ------------------------------------


def region_filter_clause(identity: Identity, schema: str, table: str) -> tuple[str, dict]:
    """Return (sql_fragment, binds) restricting rows by region for this
    identity and table. Empty fragment when no restriction applies.

    Tables that carry a region (directly or via FK) get a WHERE arm; tables
    without one are unaffected.
    """
    if identity.regions is None:
        return "", {}
    s, t = schema.upper(), table.upper()

    region_marks = ",".join(f":region_{i}" for i in range(len(identity.regions)))
    binds = {f"region_{i}": r for i, r in enumerate(identity.regions)}

    if (s, t) in (("FINANCE", "TRANSACTIONS"), ("FINANCE", "BRANCHES"),
                  ("FINANCE", "MERCHANTS")):
        return f" region IN ({region_marks})", binds
    if (s, t) == ("FINANCE", "ACCOUNTS"):
        return (
            f" branch_id IN (SELECT branch_id FROM FINANCE.branches "
            f" WHERE region IN ({region_marks}))",
            binds,
        )
    if (s, t) == ("FINANCE", "CARDS"):
        return (
            f" account_id IN (SELECT a.account_id FROM FINANCE.accounts a "
            f"   JOIN FINANCE.branches b ON b.branch_id = a.branch_id "
            f"   WHERE b.region IN ({region_marks}))",
            binds,
        )
    if (s, t) == ("FINANCE", "CUSTOMERS"):
        return (
            f" customer_id IN (SELECT a.customer_id FROM FINANCE.accounts a "
            f"   JOIN FINANCE.branches b ON b.branch_id = a.branch_id "
            f"   WHERE b.region IN ({region_marks}))",
            binds,
        )
    if (s, t) == ("FINANCE", "LOANS"):
        return (
            f" branch_id IN (SELECT branch_id FROM FINANCE.branches "
            f" WHERE region IN ({region_marks}))",
            binds,
        )
    if (s, t) == ("FINANCE", "SAR_REPORTS"):
        return (
            f" customer_id IN (SELECT a.customer_id FROM FINANCE.accounts a "
            f"   JOIN FINANCE.branches b ON b.branch_id = a.branch_id "
            f"   WHERE b.region IN ({region_marks}))",
            binds,
        )
    return "", {}


def is_table_forbidden(identity: Identity, schema: str, table: str) -> bool:
    """Whether the identity is allowed to view this table at all."""
    qualified = f"{schema.upper()}.{table.upper()}"
    return qualified in identity.forbid_tables


def column_is_masked(identity: Identity, schema: str, table: str, column: str) -> bool:
    qualified = f"{schema.upper()}.{table.upper()}.{column.upper()}"
    return qualified in identity.mask_cols


# ----- Helpers used by the chat agent (tools.py) ----------------------------


import re

from config import AGENT_USER


_OWNER_OBJECT_RE = re.compile(
    r"(?<![\w$#])([A-Za-z][A-Za-z0-9_$#]*)\s*\.\s*([A-Za-z][A-Za-z0-9_$#]*)(?![\w$#])"
)

# One left-to-right pass so a comment marker inside a string literal is not
# mistaken for a comment (and vice versa): literals are kept (a dynamic
# `'SELECT ... FROM finance.sar_reports'` still counts as a reference),
# "quoted identifiers" lose their quotes, comments become a space.
_SQL_LEXEME_RE = re.compile(
    r"""[nN]?[qQ]'(?:\[.*?\]|\{.*?\}|\(.*?\)|<.*?>|([^\s\w\[\{(<]).*?\1)'"""
    r"""|'(?:[^']|'')*'|"([^"]*)"|/\*.*?\*/|--[^\n]*""",
    re.S,
)


def normalize_sql(sql: str) -> str:
    """Strip comments and identifier quotes so `"FINANCE"."SAR_REPORTS"`,
    `FINANCE . SAR_REPORTS` and `FINANCE/**/.SAR_REPORTS` all read as
    `FINANCE.SAR_REPORTS` to the table checks below."""
    def repl(m: "re.Match[str]") -> str:
        text = m.group(0)
        if m.group(2) is not None:
            return m.group(2)
        if text.startswith(("/*", "--")):
            return " "
        return text
    return _SQL_LEXEME_RE.sub(repl, sql)


def referenced_tables(sql: str) -> set[str]:
    """Pull every `OWNER.OBJECT` reference out of a SQL string, uppercased.

    Used by `tool_run_sql` to check whether the agent's SQL touches a table
    the current identity is forbidden from. False positives (column or alias
    references that look like `OWNER.OBJECT`) are tolerated — the check is
    deliberately conservative, refusing rather than risking a leak.
    """
    out: set[str] = set()
    for owner, obj in _OWNER_OBJECT_RE.findall(normalize_sql(sql)):
        out.add(f"{owner.upper()}.{obj.upper()}")
    return out


def forbid_check_for_sql(identity: Identity, sql: str) -> str | None:
    """Return a denial message if `sql` references any table this identity is
    forbidden from. None when the SQL is allowed.

    Tables owned by the session schema (AGENT) resolve without a prefix, so a
    bare `SELECT * FROM agent_authorizations` is refused too.
    """
    text = normalize_sql(sql)
    refs = referenced_tables(sql)
    # Fail closed: also scan the raw text, in case the lexer misreads a literal.
    text_raw = sql
    for owner, obj in _OWNER_OBJECT_RE.findall(sql):
        refs.add(f"{owner.upper()}.{obj.upper()}")
    hit = set()
    for qualified in identity.forbid_tables:
        owner, _, name = qualified.partition(".")
        if qualified in refs:
            hit.add(qualified)
        elif owner == AGENT_USER.upper() and any(
            re.search(rf"(?<![\w$#.]){re.escape(name)}(?![\w$#])", t, re.I)
            for t in (text, text_raw)
        ):
            hit.add(qualified)
    if not hit:
        return None
    hit = sorted(hit)
    return (
        f"Authorization denied: identity {identity.id!r} ({identity.label}, "
        f"clearance={identity.clearance}) is not permitted to read "
        f"{', '.join(hit)}. Switch to an identity with the required "
        f"clearance (e.g. 'cfo' has EXECUTIVE clearance, or "
        f"'compliance.officer' for SAR access), or query a different table."
    )


def mask_indices_for(identity: Identity, columns: list[str]) -> dict[int, str]:
    """Given an ordered list of column names produced by a cursor, return a
    map of column-index → fully-qualified mask name for every column the
    identity is told to redact.

    Caller is expected to know the schema/table ahead of time and pre-prefix
    the column names (e.g. 'FINANCE.TRANSACTIONS.AMOUNT_CENTS').
    Names already prefixed are matched verbatim against `identity.mask_cols`.
    """
    masked = set(identity.mask_cols)
    out: dict[int, str] = {}
    for i, c in enumerate(columns):
        if c.upper() in masked:
            out[i] = c
    return out


def region_drop_predicate(identity: Identity):
    """Return a callable(row, columns) -> keep_bool that drops rows whose
    REGION column (if present) isn't in the identity's authorized list.

    For identities with no region restriction, returns a constant-True filter.
    Used as a post-fetch sieve in tool_run_sql so the agent can run free-form
    SQL like `SELECT * FROM FINANCE.transactions t` and still get filtered
    rows back.
    """
    if identity.regions is None:
        return lambda row, columns: True
    allowed = set(identity.regions)

    def keep(row, columns):
        for i, c in enumerate(columns):
            cn = c.upper()
            if cn == "REGION" or cn.endswith(".REGION"):
                v = row[i]
                if v is None:
                    return True
                return str(v).upper() in allowed
        return True

    return keep
