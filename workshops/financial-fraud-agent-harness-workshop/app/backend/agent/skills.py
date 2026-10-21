"""Skillbox: §11.5 of the notebook. Skills are markdown playbooks indexed by
embedding; the agent gets a manifest in the system prompt and loads full bodies
on demand via `tool_load_skill`."""

from __future__ import annotations

import hashlib
import io
import json
import re
import tarfile
import urllib.request
from datetime import datetime, timezone

import oracledb

from config import ONNX_EMBED_DIM, ONNX_EMBED_MODEL


SKILLBOX_DDL = [
    (
        "CREATE TABLE skillbox ("
        "  name        VARCHAR2(160) PRIMARY KEY,"
        "  category    VARCHAR2(64),"
        "  description VARCHAR2(2000) NOT NULL,"
        "  body        CLOB NOT NULL,"
        "  source_url  VARCHAR2(2000),"
        "  source_sha  VARCHAR2(64),"
        f" embedding   VECTOR({ONNX_EMBED_DIM}, FLOAT32),"
        "  metadata    JSON,"
        "  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ")"
    ),
    (
        "CREATE VECTOR INDEX skillbox_emb_v ON skillbox(embedding) "
        "ORGANIZATION INMEMORY NEIGHBOR GRAPH DISTANCE COSINE"
    ),
]


def ensure_skillbox(agent_conn):
    with agent_conn.cursor() as cur:
        for stmt in SKILLBOX_DDL:
            try:
                cur.execute(stmt)
            except oracledb.DatabaseError as e:
                if e.args[0].code in (955, 1408, 51962):
                    continue
                raise
    agent_conn.commit()


def _parse_skill_md(text: str, fallback_name: str) -> str:
    lines = text.splitlines()
    n, i = len(lines), 0
    if i < n and lines[i].strip() == "---":
        i += 1
        while i < n and lines[i].strip() != "---":
            i += 1
        i += 1
    while i < n and not lines[i].strip():
        i += 1
    if i < n and lines[i].lstrip().startswith("# "):
        i += 1
    while i < n and not lines[i].strip():
        i += 1
    para = []
    while i < n and lines[i].strip() and not lines[i].lstrip().startswith("#"):
        para.append(lines[i].strip())
        i += 1
    description = " ".join(para).strip() or fallback_name
    if len(description) > 1800:
        description = description[:1797].rsplit(" ", 1)[0] + "..."
    return description


ORACLE_SKILLS_REPO = "oracle/skills"
ORACLE_SKILLS_BASE = "db"
SKILLS_TARBALL_URL = f"https://api.github.com/repos/{ORACLE_SKILLS_REPO}/tarball/main"


def _download_repo_tarball(url: str = SKILLS_TARBALL_URL) -> dict[str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "eda-skillbox-ingester"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        for member in tar:
            if not member.isfile():
                continue
            parts = member.name.split("/", 1)
            if len(parts) < 2:
                continue
            rel = parts[1]
            if not rel.startswith(f"{ORACLE_SKILLS_BASE}/") or not rel.endswith(".md"):
                continue
            f = tar.extractfile(member)
            if f is not None:
                files[rel] = f.read()
    return files


def ingest_skills(agent_conn) -> dict:
    """One-shot ingestion of oracle/skills. Idempotent on content SHA."""
    raw_files = _download_repo_tarball()
    new = updated = skipped = 0
    for rel_path, body_bytes in sorted(raw_files.items()):
        parts = rel_path.split("/")
        if len(parts) != 3:
            continue
        _, category, filename = parts
        if filename in {"SKILL.md", "SKILLS.md"}:
            continue
        body = body_bytes.decode("utf-8", errors="replace")
        file_stem = filename[:-3]
        full_name = f"{category}/{file_stem}"
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()[:32]

        with agent_conn.cursor() as cur:
            cur.execute("SELECT source_sha FROM skillbox WHERE name = :n", n=full_name)
            row = cur.fetchone()
        if row and row[0] == sha:
            skipped += 1
            continue

        description = _parse_skill_md(body, fallback_name=full_name)
        embed_text = f"{full_name}\n{description}"
        source_url = f"https://raw.githubusercontent.com/{ORACLE_SKILLS_REPO}/main/{rel_path}"
        meta = json.dumps({
            "category": category,
            "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_repo": ORACLE_SKILLS_REPO,
            "rel_path": rel_path,
        })
        with agent_conn.cursor() as cur:
            cur.setinputsizes(body=oracledb.DB_TYPE_CLOB, md=oracledb.DB_TYPE_JSON)
            cur.execute(
                "MERGE INTO skillbox t "
                "USING (SELECT :n AS name FROM dual) s ON (t.name = s.name) "
                "WHEN MATCHED THEN UPDATE SET "
                "  category = :cat, description = :dsc, body = :body, "
                "  source_url = :url, source_sha = :sha, "
                f" embedding = VECTOR_EMBEDDING({ONNX_EMBED_MODEL} USING :etext AS DATA), "
                "  metadata = :md, updated_at = CURRENT_TIMESTAMP "
                "WHEN NOT MATCHED THEN INSERT "
                "  (name, category, description, body, source_url, source_sha, embedding, metadata) "
                "  VALUES (:n, :cat, :dsc, :body, :url, :sha, "
                f"          VECTOR_EMBEDDING({ONNX_EMBED_MODEL} USING :etext AS DATA), :md)",
                n=full_name, cat=category, dsc=description, body=body,
                url=source_url, sha=sha, etext=embed_text, md=meta,
            )
            if row is None:
                new += 1
            else:
                updated += 1
        agent_conn.commit()
    return {"new": new, "updated": updated, "skipped": skipped, "total_in_repo": len(raw_files)}


def build_skill_manifest(agent_conn, query: str, k: int = 3) -> str:
    """Top-k skills as a one-line manifest. Empty string when skillbox is empty."""
    try:
        with agent_conn.cursor() as cur:
            cur.execute(
                "SELECT name, description FROM skillbox "
                f" ORDER BY VECTOR_DISTANCE(embedding, VECTOR_EMBEDDING({ONNX_EMBED_MODEL} USING :q AS DATA), COSINE) "
                " FETCH FIRST :k ROWS ONLY",
                q=query, k=k,
            )
            rows = list(cur)
    except oracledb.DatabaseError:
        return ""
    if not rows:
        return ""
    lines = [f"  - {n} — {(d.read() if hasattr(d, 'read') else d)[:240]}" for n, d in rows]
    return (
        "Available skills (call load_skill(name) to read the full guide and follow it):\n"
        + "\n".join(lines) + "\n\n"
    )
