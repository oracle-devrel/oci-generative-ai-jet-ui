"""Identity registry for the "Use As:" selector.

The AGENT database user is always the actual session principal. Identities here
are *application-layer personas* layered on top: each one carries a clearance
level, a list of authorized ocean regions, and a set of columns that should be
masked when read. The Data Explorer applies these filters server-side; the
agent loop receives the identity in its system prompt **and** in `tool_run_sql`
so any SQL the model constructs is also gated.

This is the same shape DDS (notebook §14.4) implements at the kernel level.
The production app simulates it in Python rather than wiring full
`CREATE DATA SECURITY POLICY` DDL — same trust contract, less moving parts for
the demo.

Personas in this file are tuned so that *every* commonly-viewed table changes
visibly when you switch identities. That makes the security model legible at a
glance: pick `agent` and you see masks; pick `cfo` and they vanish; pick a
regional analyst and rows drop too.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Identity:
    """One persona the user can act as.

    `regions`     — None means "all regions"; a list narrows voyage / cargo /
                    port / vessel visibility to those `ocean_region` values.
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
_FINANCIAL_MASKS = [
    "SUPPLYCHAIN.CARGO_ITEMS.UNIT_VALUE_CENTS",
    "SUPPLYCHAIN.CARGO_ITEMS.WEIGHT_KG",
]
_PII_PARTY_MASKS = [
    "SUPPLYCHAIN.CONTAINERS.CONSIGNOR",
    "SUPPLYCHAIN.CONTAINERS.CONSIGNEE",
]
_VESSEL_IDENTIFIER_MASKS = [
    "SUPPLYCHAIN.VESSELS.IMO_NUMBER",
]
_VESSEL_OPERATIONAL_MASKS = [
    "SUPPLYCHAIN.VESSELS.CAPACITY_TEU",
    "SUPPLYCHAIN.VESSEL_POSITIONS.SPEED_KNOTS",
    "SUPPLYCHAIN.VESSEL_POSITIONS.HEADING_DEG",
]
_PORT_INFRA_MASKS = [
    "SUPPLYCHAIN.PORTS.TERMINAL_COUNT",
]
_AGENT_ADMIN_TABLES = [
    "AGENT.AGENT_AUTHORIZATIONS",
    "AGENT.AGENT_CLEARANCES",
    "AGENT.SCHEMA_ACL",
]


# Registry. Order is the order they show up in the UI dropdown.
IDENTITIES: dict[str, Identity] = {
    "agent": Identity(
        id="agent",
        label="Agent (default)",
        description=(
            "Default low-privilege application persona. Sees operational data "
            "but commercial values (cargo declared values, weights), vessel "
            "IMO numbers, and the agent's own admin tables are masked. "
            "Use cfo for unrestricted access."
        ),
        clearance="STANDARD",
        regions=None,
        mask_cols=[
            *_FINANCIAL_MASKS,
            *_VESSEL_IDENTIFIER_MASKS,
        ],
        forbid_tables=_AGENT_ADMIN_TABLES,
    ),
    "cfo": Identity(
        id="cfo",
        label="CFO — Executive",
        description=(
            "Executive clearance. Sees every row in every region and every "
            "column unmasked — the only persona that does. Use this when you "
            "want to compare a redacted view against the truth."
        ),
        clearance="EXECUTIVE",
        regions=None,
        mask_cols=[],
        forbid_tables=[],
    ),
    "analyst.east": Identity(
        id="analyst.east",
        label="Analyst — East",
        description=(
            "Standard clearance, eastern regions only. Voyages, ports, vessels, "
            "containers, and cargo restricted to ATLANTIC + MEDITERRANEAN. "
            "Cargo financials, container parties, vessel IMO, and port "
            "terminal counts are all masked."
        ),
        clearance="STANDARD",
        regions=["ATLANTIC", "MEDITERRANEAN"],
        mask_cols=[
            *_FINANCIAL_MASKS,
            *_PII_PARTY_MASKS,
            *_VESSEL_IDENTIFIER_MASKS,
            *_PORT_INFRA_MASKS,
        ],
        forbid_tables=_AGENT_ADMIN_TABLES,
    ),
    "analyst.west": Identity(
        id="analyst.west",
        label="Analyst — West",
        description=(
            "Standard clearance, western regions only. Voyages, ports, vessels, "
            "containers, and cargo restricted to PACIFIC + INDIAN. Same column "
            "masks as analyst.east."
        ),
        clearance="STANDARD",
        regions=["PACIFIC", "INDIAN"],
        mask_cols=[
            *_FINANCIAL_MASKS,
            *_PII_PARTY_MASKS,
            *_VESSEL_IDENTIFIER_MASKS,
            *_PORT_INFRA_MASKS,
        ],
        forbid_tables=_AGENT_ADMIN_TABLES,
    ),
    "ops.viewer": Identity(
        id="ops.viewer",
        label="Ops Viewer",
        description=(
            "Operations-only persona. Sees fleet/route metadata (carriers, "
            "vessels, ports, voyages, positions) but is forbidden from cargo "
            "and container tables entirely. Vessel capacity/speed/heading and "
            "port terminal counts are masked too — useful for dispatch screens "
            "that should never leak commercial info."
        ),
        clearance="STANDARD",
        regions=None,
        mask_cols=[
            *_VESSEL_OPERATIONAL_MASKS,
            *_PORT_INFRA_MASKS,
        ],
        forbid_tables=[
            "SUPPLYCHAIN.CONTAINERS",
            "SUPPLYCHAIN.CARGO_ITEMS",
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
    """Return (sql_fragment, binds) restricting rows by ocean_region for this
    identity and table. Empty fragment when no restriction applies.

    Tables that carry a region (directly or via FK) get a WHERE arm; tables
    without one are unaffected.
    """
    if identity.regions is None:
        return "", {}
    s, t = schema.upper(), table.upper()

    region_marks = ",".join(f":region_{i}" for i in range(len(identity.regions)))
    binds = {f"region_{i}": r for i, r in enumerate(identity.regions)}

    if (s, t) == ("SUPPLYCHAIN", "VOYAGES"):
        return f" ocean_region IN ({region_marks})", binds
    if (s, t) == ("SUPPLYCHAIN", "PORTS"):
        return f" ocean_region IN ({region_marks})", binds
    if (s, t) == ("SUPPLYCHAIN", "CONTAINERS"):
        return (
            f" voyage_id IN (SELECT voyage_id FROM SUPPLYCHAIN.voyages "
            f" WHERE ocean_region IN ({region_marks}))",
            binds,
        )
    if (s, t) == ("SUPPLYCHAIN", "CARGO_ITEMS"):
        return (
            f" container_id IN (SELECT c.container_id FROM SUPPLYCHAIN.containers c "
            f"   JOIN SUPPLYCHAIN.voyages v ON v.voyage_id = c.voyage_id "
            f"   WHERE v.ocean_region IN ({region_marks}))",
            binds,
        )
    if (s, t) == ("SUPPLYCHAIN", "VESSELS"):
        return (
            f" vessel_id IN (SELECT vessel_id FROM SUPPLYCHAIN.voyages "
            f" WHERE ocean_region IN ({region_marks}))",
            binds,
        )
    if (s, t) == ("SUPPLYCHAIN", "VESSEL_POSITIONS"):
        return (
            f" vessel_id IN (SELECT vessel_id FROM SUPPLYCHAIN.voyages "
            f" WHERE ocean_region IN ({region_marks}))",
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


_OWNER_OBJECT_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\.([A-Za-z][A-Za-z0-9_]*)\b")


def referenced_tables(sql: str) -> set[str]:
    """Pull every `OWNER.OBJECT` reference out of a SQL string, uppercased.

    Used by `tool_run_sql` to check whether the agent's SQL touches a table
    the current identity is forbidden from. False positives (column or alias
    references that look like `OWNER.OBJECT`) are tolerated — the check is
    deliberately conservative, refusing rather than risking a leak.
    """
    out: set[str] = set()
    for owner, obj in _OWNER_OBJECT_RE.findall(sql):
        out.add(f"{owner.upper()}.{obj.upper()}")
    return out


def forbid_check_for_sql(identity: Identity, sql: str) -> str | None:
    """Return a denial message if `sql` references any table this identity is
    forbidden from. None when the SQL is allowed.
    """
    refs = referenced_tables(sql)
    hit = sorted(t for t in refs if t in set(identity.forbid_tables))
    if not hit:
        return None
    return (
        f"Authorization denied: identity {identity.id!r} ({identity.label}, "
        f"clearance={identity.clearance}) is not permitted to read "
        f"{', '.join(hit)}. Switch to an identity with the required "
        f"clearance (e.g. 'cfo' has EXECUTIVE clearance and no table forbids), "
        f"or query a different table."
    )


def mask_indices_for(identity: Identity, columns: list[str]) -> dict[int, str]:
    """Given an ordered list of column names produced by a cursor, return a
    map of column-index → fully-qualified mask name for every column the
    identity is told to redact.

    Caller is expected to know the schema/table ahead of time and pre-prefix
    the column names (e.g. 'SUPPLYCHAIN.CARGO_ITEMS.UNIT_VALUE_CENTS').
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
    OCEAN_REGION column (if present) isn't in the identity's authorized list.

    For identities with no region restriction, returns a constant-True filter.
    Used as a post-fetch sieve in tool_run_sql so the agent can run free-form
    SQL like `SELECT v.* FROM SUPPLYCHAIN.voyages v` and still get filtered
    rows back.
    """
    if identity.regions is None:
        return lambda row, columns: True
    allowed = set(identity.regions)

    def keep(row, columns):
        for i, c in enumerate(columns):
            cn = c.upper()
            if cn == "OCEAN_REGION" or cn.endswith(".OCEAN_REGION"):
                v = row[i]
                if v is None:
                    return True
                return str(v).upper() in allowed
        return True

    return keep
