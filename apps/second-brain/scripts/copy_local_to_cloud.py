"""Copy the brain from the local Oracle container to the cloud Autonomous DB.

Fast migration: copies the content tables (content, chunks, memory types, the compiled wiki)
INCLUDING precomputed embeddings — so no re-ingest, no embedding recomputation, no re-hitting
source APIs. db.connect() is the CLOUD target (oracle/.env); local is explicit.

  python scripts/copy_local_to_cloud.py

PRIVACY DEFAULT: private scopes stay local. Only visibility='content' rows are copied, and the
private business tables are skipped entirely — the cloud (internet-reachable) brain never holds
them. `--include-private` overrides for a fully-private cloud copy you have deliberately chosen.

Idempotent: clears the target tables first. Run after apply_schema.py + load_model_cloud.py.
"""
import argparse
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "oracle" / "agent"))
import db          # noqa: E402  (cloud target, from oracle/.env)
import oracledb    # noqa: E402

# FK-safe order: parents before children.
TABLES = ["platforms", "posts", "media", "content_chunks",
          "agent_memory", "semantic_memory", "conversations", "procedural_memory",
          "wiki_pages", "page_links", "page_sources", "wiki_meta"]
PRIVATE_TABLES = ["brands", "deals"]   # private business data — local vault only, by default

# content-scope filters (applied unless --include-private): the cloud copy carries ONLY the
# searchable content scope, so private/business/archived rows never leave the local vault.
CONTENT_ONLY = {
    "posts": "WHERE NVL(visibility,'content') = 'content'",
    "media": ("WHERE post_id IN (SELECT post_id FROM posts "
              "WHERE NVL(visibility,'content') = 'content')"),
    "content_chunks": ("WHERE post_id IN (SELECT post_id FROM posts "
                       "WHERE NVL(visibility,'content') = 'content')"),
}
BATCH = 500


def cols_of(cur, table):
    cur.execute("SELECT column_name FROM user_tab_columns WHERE table_name = :t "
                "ORDER BY column_id", t=table.upper())
    return [r[0] for r in cur.fetchall()]


def vector_cols(cur, table):
    cur.execute("SELECT column_name FROM user_tab_columns WHERE table_name = :t "
                "AND data_type = 'VECTOR'", t=table.upper())
    return {r[0] for r in cur.fetchall()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-private", action="store_true",
                    help="ALSO copy private scopes + business tables to the cloud "
                         "(default: content only — private data stays local)")
    ap.add_argument("--allow-untagged", action="store_true",
                    help="proceed even if some rows were never classified (untagged rows "
                         "count as public content — only use after reviewing them)")
    args = ap.parse_args()
    tables = (["platforms"] + PRIVATE_TABLES + TABLES[1:]) if args.include_private else TABLES
    preds = {} if args.include_private else CONTENT_ONLY
    if not args.include_private:
        print("privacy default ON: copying visibility='content' only; "
              f"skipping {', '.join(PRIVATE_TABLES)} (use --include-private to override)")

    # no password fallback, ever — same rule as oracle/agent/db.py: a hardcoded default
    # silently "works" against a DB that happens to use the demo password
    local_pwd = os.environ.get("LOCAL_APP_PWD")
    if not local_pwd:
        sys.exit("LOCAL_APP_PWD is not set — export it (the LOCAL database's app-user "
                 "password) before copying to the cloud brain.")
    local = oracledb.connect(
        user=os.environ.get("LOCAL_DB_USER", "CCC"),
        password=local_pwd,
        dsn=os.environ.get("LOCAL_DB_DSN", "localhost:1521/FREEPDB1"))
    cloud = db.connect()
    lc, cc = local.cursor(), cloud.cursor()

    # PREFLIGHT (fail closed): the content-only filter treats NULL visibility as 'content',
    # so rows that were never classified would ship to the internet-reachable cloud brain.
    # Refuse until classify_private.py has run (or the operator explicitly accepts).
    if not args.include_private:
        lc.execute("SELECT COUNT(*) FROM posts WHERE visibility IS NULL")
        untagged = lc.fetchone()[0]
        if untagged and not args.allow_untagged:
            sys.exit(
                f"REFUSING to copy: {untagged} post(s) have no visibility tag yet, and "
                "untagged rows count as public 'content'. Run\n"
                "    python scripts/classify_private.py --apply\n"
                "first (then re-run this copy), or pass --allow-untagged if you have "
                "reviewed them and they are all safe to publish to the cloud brain.")

    print("clearing target tables...")
    for t in reversed(tables):
        cc.execute(f"DELETE FROM {t}")
    if not args.include_private:
        # actively PURGE private tables from the cloud too (an earlier full copy may have put
        # them there) — the default run leaves the cloud with zero private business rows.
        for t in reversed(PRIVATE_TABLES):
            cc.execute(f"DELETE FROM {t}")
            print(f"  purged cloud {t}")
    # NO commit yet: the clear + full copy is ONE transaction, so a mid-copy
    # failure leaves the previous cloud brain intact.

    for t in tables:
        cols = cols_of(lc, t)
        vcols = vector_cols(lc, t)
        col_list = ", ".join(cols)
        binds = ", ".join(f":{i+1}" for i in range(len(cols)))
        insert = f"INSERT INTO {t} ({col_list}) VALUES ({binds})"
        sizes = [oracledb.DB_TYPE_VECTOR if c in vcols else None for c in cols]

        lc.execute(f"SELECT {col_list} FROM {t} {preds.get(t, '')}")
        total = 0
        while True:
            rows = lc.fetchmany(BATCH)
            if not rows:
                break
            if any(sizes):
                cc.setinputsizes(*sizes)
            cc.executemany(insert, rows)
            total += len(rows)
        print(f"  {t}: {total} rows")

    cloud.commit()   # the whole clear+copy lands atomically here

    # Critical after a bulk copy with explicit IDs: advance each identity sequence past the
    # copied max, so new auto-generated IDs don't collide (ORA-00001) on the next insert.
    print("advancing identity sequences (START WITH LIMIT VALUE)...")
    cc.execute("SELECT table_name, column_name FROM user_tab_identity_cols")
    for t, col in cc.fetchall():
        try:
            cc.execute(f"ALTER TABLE {t} MODIFY {col} "
                       "GENERATED BY DEFAULT AS IDENTITY (START WITH LIMIT VALUE)")
        except Exception as e:
            print(f"  {t}.{col} skip:", str(e).split(chr(10))[0][:50])
    cloud.commit()

    local.close()
    cloud.close()
    print("done — brain copied to the cloud.")


if __name__ == "__main__":
    main()
