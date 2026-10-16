"""
Load FastAPI commit history into Oracle AI Database 26ai with vector embeddings.

Prerequisites:
  1. ../fastapi_commits.txt  (delimited commit metadata, one block per commit)
  2. ../diffs/all_diffs.txt  (git log --stat dump, delimited by ===SHA:hash===)
  3. pip install -r requirements.txt
  4. Schema created by running schema.sql

Run:
  python load_data.py
"""

import array
import os
import re
import sys

import oracledb
from sentence_transformers import SentenceTransformer

# =========================== Config ===========================
_REQUIRED_ENV = ("ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN")
_missing = [v for v in _REQUIRED_ENV if v not in os.environ]
if _missing:
    print(f"ERROR: missing environment variables: {', '.join(_missing)}")
    sys.exit(1)

DB_USER = os.environ["ORACLE_USER"]
DB_PASSWORD = os.environ["ORACLE_PASSWORD"]
DB_DSN = os.environ["ORACLE_DSN"]
DB_SCHEMA = os.getenv("ORACLE_SCHEMA", "GITHUB_SECOND_BRAIN")

COMMITS_FILE = "../fastapi_commits.txt"
DIFFS_FILE = "../diffs/all_diffs.txt"

MAX_COMMITS = 3000
BATCH_SIZE = 100
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dims
# ==============================================================


def parse_diffs(path):
    """Parse the single-file diff dump into a dict keyed by SHA."""
    diffs = {}
    if not os.path.exists(path):
        print(f"WARNING: {path} not found. Continuing without file-change info.")
        return diffs

    current_sha = None
    buffer = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"===SHA:([0-9a-f]+)===", line.strip())
            if m:
                if current_sha:
                    diffs[current_sha] = "".join(buffer).strip()
                current_sha = m.group(1)
                buffer = []
            else:
                buffer.append(line)
        if current_sha:
            diffs[current_sha] = "".join(buffer).strip()
    return diffs


def load_commits(path, limit):
    """Load commits from a delimited plain-text dump.

    Each block looks like:
        <<<COMMIT>>>
        <sha>
        <author>
        <iso_date>
        <subject>
        <<<BODY>>>
        <body lines, possibly multiple>
        <<<END>>>
    """
    commits = []
    with open(path, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    blocks = raw.split("<<<COMMIT>>>")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if len(commits) >= limit:
            break

        try:
            header, rest = block.split("<<<BODY>>>", 1)
        except ValueError:
            continue

        body, _, _ = rest.partition("<<<END>>>")
        header_lines = header.strip().splitlines()
        if len(header_lines) < 4:
            continue

        commits.append(
            {
                "sha": header_lines[0].strip(),
                "author": header_lines[1].strip(),
                "date": header_lines[2].strip(),
                "subject": header_lines[3].strip(),
                "body": body.strip(),
            }
        )

    return commits


def build_content(commit, files_changed):
    """Combine commit fields into a single string for embedding."""
    body = (commit.get("body") or "").strip() or "(no body)"
    files = (files_changed or "").strip()[:1500] or "(unknown)"
    return (
        f"Subject: {commit.get('subject', '')}\n"
        f"Author: {commit.get('author', '')}\n"
        f"Date: {commit.get('date', '')}\n"
        f"Body: {body}\n"
        f"Files changed:\n{files}"
    )


def normalize_date(raw):
    """Turn a git ISO date like 2024-03-12T10:15:30+01:00 into a clean string."""
    if not raw:
        return "1970-01-01T00:00:00"
    # Strip timezone suffix, keep first 19 chars
    cleaned = raw.split("+")[0].split("Z")[0][:19]
    return cleaned if "T" in cleaned else "1970-01-01T00:00:00"


def flush_batch(cursor, sql, batch, model):
    """Encode texts in batch, insert via executemany."""
    texts = [item[1] for item in batch]
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    rows = []
    for (commit, content, files_changed), vec in zip(batch, vectors, strict=True):
        rows.append(
            (
                commit.get("sha"),
                (commit.get("author") or "")[:200],
                normalize_date(commit.get("date", "")),
                (commit.get("subject") or "")[:1000],
                commit.get("body") or "",
                files_changed,
                content,
                array.array("f", vec.tolist()),
            )
        )

    try:
        cursor.executemany(sql, rows)
    except oracledb.IntegrityError:
        # Retry one-by-one so a duplicate SHA does not kill the whole batch
        inserted = 0
        for row in rows:
            try:
                cursor.execute(sql, row)
                inserted += 1
            except oracledb.IntegrityError:
                pass
        return inserted

    return len(rows)


def main():
    if not os.path.exists(COMMITS_FILE):
        print(f"ERROR: {COMMITS_FILE} not found in current directory.")
        sys.exit(1)

    print("Loading embedding model (first run downloads ~90 MB)...")
    model = SentenceTransformer(EMBED_MODEL)

    print(f"Parsing {DIFFS_FILE} ...")
    diffs = parse_diffs(DIFFS_FILE)
    print(f"  parsed {len(diffs)} diffs")

    print(f"Loading {COMMITS_FILE} ...")
    commits = load_commits(COMMITS_FILE, MAX_COMMITS)
    print(f"  loaded {len(commits)} commits")

    print(f"Connecting to Oracle AI Database 26ai at {DB_DSN} ...")
    conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
    cursor = conn.cursor()

    # Point all unqualified object references at the target schema.
    # Schema names cannot be parameterised in DDL; validate against a strict
    # allowlist pattern to prevent SQL injection.
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$#]{0,127}", DB_SCHEMA):
        print(f"ERROR: ORACLE_SCHEMA value '{DB_SCHEMA}' is not a valid Oracle identifier.")
        sys.exit(1)

    cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {DB_SCHEMA}")

    insert_sql = f"""
        INSERT INTO {DB_SCHEMA}.FASTAPI_COMMITS
          (sha, author, commit_date, subject, body,
           files_changed, content_for_embedding, embedding)
        VALUES
          (:1, :2,
           TO_TIMESTAMP(:3, 'YYYY-MM-DD"T"HH24:MI:SS'),
           :4, :5, :6, :7, :8)
    """

    batch = []
    total = 0
    for commit in commits:
        sha = commit.get("sha")
        if not sha:
            continue
        files_changed = diffs.get(sha, "")
        content = build_content(commit, files_changed)
        batch.append((commit, content, files_changed))

        if len(batch) >= BATCH_SIZE:
            total += flush_batch(cursor, insert_sql, batch, model)
            conn.commit()
            batch = []
            print(f"  inserted {total} commits...")

    if batch:
        total += flush_batch(cursor, insert_sql, batch, model)
        conn.commit()

    print(f"Done. Inserted {total} commits.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
