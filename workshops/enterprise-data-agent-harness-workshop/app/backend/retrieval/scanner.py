"""Schema scanner: §5.2 of the notebook condensed into a single module.

Mines Oracle's catalog views, turns each finding into a `Fact`, and OAMP
stores each fact as a memory with appropriate kind metadata.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, field
from typing import Any

from config import AGENT_ID, USER_ID


@dataclass
class Fact:
    kind: str
    subject: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _hash_body(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def _scan_tables(conn, owner: str) -> list[Fact]:
    facts: list[Fact] = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT t.table_name, c.comments "
            "  FROM all_tables t "
            "  LEFT JOIN all_tab_comments c "
            "         ON c.owner = t.owner AND c.table_name = t.table_name "
            " WHERE t.owner = :o ORDER BY t.table_name",
            o=owner.upper(),
        )
        for table, comment in cur:
            subj = f"{owner}.{table}"
            body = f"Table {subj}."
            if comment:
                body += f" Documented purpose: {comment}"
            facts.append(Fact("table", subj, body, {"owner": owner, "table": table}))
    return facts


def _scan_columns(conn, owner: str) -> list[Fact]:
    facts: list[Fact] = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT c.table_name, c.column_name, c.data_type, c.data_length, "
            "       c.nullable, m.comments "
            "  FROM all_tab_columns c "
            "  LEFT JOIN all_col_comments m "
            "         ON m.owner = c.owner AND m.table_name = c.table_name "
            "        AND m.column_name = c.column_name "
            " WHERE c.owner = :o ORDER BY c.table_name, c.column_id",
            o=owner.upper(),
        )
        for table, col, dt, dl, null, comm in cur:
            subj = f"{owner}.{table}.{col}"
            type_str = dt + (f"({dl})" if dt in ("VARCHAR2", "CHAR") and dl else "")
            null_str = "nullable" if null == "Y" else "NOT NULL"
            body = f"Column {subj} of type {type_str} ({null_str})."
            if comm:
                body += f" Meaning: {comm}"
            facts.append(Fact(
                "column", subj, body,
                {"owner": owner, "table": table, "column": col, "type": dt},
            ))
    return facts


def _scan_relationships(conn, owner: str) -> list[Fact]:
    facts: list[Fact] = []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT a.constraint_name, a.table_name, ac.column_name, "
            "       r.table_name r_table, rc.column_name r_column "
            "  FROM all_constraints a "
            "  JOIN all_cons_columns ac "
            "       ON ac.owner = a.owner AND ac.constraint_name = a.constraint_name "
            "  JOIN all_constraints r "
            "       ON r.owner = a.r_owner AND r.constraint_name = a.r_constraint_name "
            "  JOIN all_cons_columns rc "
            "       ON rc.owner = r.owner AND rc.constraint_name = r.constraint_name "
            "      AND rc.position = ac.position "
            " WHERE a.owner = :o AND a.constraint_type = 'R' "
            " ORDER BY a.table_name, ac.position",
            o=owner.upper(),
        )
        for cn, t, c, rt, rc in cur:
            subj = f"{owner}.{t}.{c}->{owner}.{rt}.{rc}"
            body = (
                f"{owner}.{t}.{c} references {owner}.{rt}.{rc} "
                f"(constraint {cn}). Use this column for joins between the two tables."
            )
            facts.append(Fact(
                "relationship", subj, body,
                {"from": f"{owner}.{t}", "to": f"{owner}.{rt}", "via": c},
            ))
    return facts


def scan_schema(conn, owner: str) -> list[Fact]:
    """Top-level scanner — table, column, and relationship facts only.
    (Workload + view scans live in the notebook §5.2.4 and §5.2.5; we keep
    this module focused on the common path.)
    """
    return [
        *_scan_tables(conn, owner),
        *_scan_columns(conn, owner),
        *_scan_relationships(conn, owner),
    ]


def write_facts(memory_client, facts: list[Fact], thread_id: str | None = None) -> dict:
    """Idempotent upsert into OAMP. Skips facts whose body hashes match what's
    already stored under the same subject.

    `thread_id`, when supplied, is stamped both into the OAMP record's
    thread_id field AND into metadata['origin_thread_id']. The fact remains
    globally retrievable (search_knowledge ignores thread scoping) but you
    can trace which thread first wrote it.

    OAM.add_memory takes `content` as the first positional arg; metadata flows
    through `**store_kwargs`. Updates go via _store.update(record_id=..., content=...).
    """
    new = updated = skipped = 0
    for f in facts:
        h = _hash_body(f.body)
        existing = memory_client._store.list(
            "memory",
            user_id=USER_ID, agent_id=AGENT_ID,
            metadata_filter={"subject": f.subject, "kind": f.kind},
            limit=1,
        )
        if existing and (getattr(existing[0], "metadata", None) or {}).get("body_hash") == h:
            skipped += 1
            continue
        meta = dict(f.metadata)
        meta.update({"kind": f.kind, "subject": f.subject, "body_hash": h})
        if thread_id:
            meta["origin_thread_id"] = thread_id
        if existing:
            # _store.update(record_type, record_id, *, text=, metadata=, ...)
            memory_client._store.update(
                "memory",
                existing[0].id,
                text=f.body,
                metadata=meta,
            )
            updated += 1
        else:
            kwargs = dict(user_id=USER_ID, agent_id=AGENT_ID, metadata=meta)
            if thread_id:
                kwargs["thread_id"] = thread_id
            memory_client.add_memory(f.body, **kwargs)
            new += 1
    return {"new": new, "updated": updated, "skipped": skipped}


def run_scan(conn, memory_client, owner: str) -> dict:
    facts = scan_schema(conn, owner)
    summary = write_facts(memory_client, facts)
    summary["facts_total"] = len(facts)
    summary["owner"] = owner.upper()
    return summary
