"""Ingest, writing: store a parse's symbols, calls and imports, and keep the rows of unchanged symbols."""

import hashlib
import json

import oracledb

from golestan_code_mcp.graph import build

EXTRACT_VERSION = 3  # the call, import and doc extraction rules; a repository stored under others is re-read


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _insert_symbols(cur, rows: list[dict]) -> None:
    """Store each symbol with its searchable text; the hybrid index vectorizes it when the ingest commits."""
    if not rows:
        return
    cur.setinputsizes(search_text=oracledb.DB_TYPE_CLOB, source=oracledb.DB_TYPE_CLOB)
    # The two LOB binds must come last, or long sources fail with ORA-24816.
    cur.executemany(
        "insert into ccctx_symbols (file_id, name, kind, start_line, end_line, content_hash, commit_sha, doc,"
        " exported, search_text, source) values (:file_id, :name, :kind, :start_line, :end_line, :content_hash,"
        " :commit_sha, :doc, :exported, :search_text, :source)",
        [{k: v for k, v in row.items() if k != "path"}
         | {"search_text": f"{row['kind']} {row['name']} in {row['path']}\n{row['source']}"} for row in rows],
    )


def _keep_unchanged(cur, file_id: int, commit: str, rows: list[dict]) -> list[dict]:
    """Keep a changed file's symbols whose code is identical, at their new lines; return the rows to insert.

    A kept symbol keeps its search text, so the hybrid index does not embed it again. Its doc and visibility are
    rewritten: a Go doc comment and a Ruby `private` line sit outside the symbol's source and can change on their own.
    """
    old: dict[tuple, list[int]] = {}
    for sid, name, kind, digest in cur.execute(
            "select id, name, kind, content_hash from ccctx_symbols where file_id = :f", f=file_id):
        old.setdefault((name, kind, digest), []).append(sid)
    moved, new = [], []
    for row in rows:
        ids = old.get((row["name"], row["kind"], row["content_hash"]))
        if ids:
            moved.append({"i": ids.pop(), "s": row["start_line"], "e": row["end_line"], "c": commit, "d": row["doc"],
                          "x": row["exported"]})
        else:
            new.append(row)
    stale = [{"i": sid} for ids in old.values() for sid in ids]
    if stale:
        cur.executemany("delete from ccctx_symbols where id = :i", stale)
    if moved:
        cur.executemany("update ccctx_symbols set start_line = :s, end_line = :e, commit_sha = :c, doc = :d,"
                        " exported = :x where id = :i", moved)
    return new


def _write(cur, repo_id: int, commit: str, dirty: bool, prepared: list[tuple], delete: list[str] | None,
           changed: set[str]) -> int:
    """Delete the given paths (all of them for None), store the prepared files and their refs, record the
    revision and rebuild the repository's edges.

    Files in `changed` are updated in place. Returns the number of symbols inserted, which the index embeds.
    """
    if delete is None:
        cur.execute("delete from ccctx_files where repo_id = :i", i=repo_id)
    elif delete:
        cur.executemany("delete from ccctx_files where repo_id = :r and path = :p",
                        [{"r": repo_id, "p": rel} for rel in delete])  # symbols go with them (on delete cascade)
    rows, fids = [], {}
    for rel, language, text, chunks, _, _, doc, namespaces in prepared:
        file_id = cur.var(int)
        spaces = json.dumps(namespaces) if namespaces else None
        if rel in changed:
            cur.execute("update ccctx_files set language = :l, content_hash = :h, doc = :d, namespaces = json(:n)"
                        " where repo_id = :r and path = :p returning id into :i",
                        r=repo_id, p=rel, l=language, h=_sha(text), d=doc, n=spaces, i=file_id)
        else:
            cur.execute(
                "insert into ccctx_files (repo_id, path, language, content_hash, doc, namespaces)"
                " values (:r, :p, :l, :h, :d, json(:n)) returning id into :i",
                r=repo_id, p=rel, l=language, h=_sha(text), d=doc, n=spaces, i=file_id,
            )
        fid = fids[rel] = file_id.getvalue()[0]
        file_rows = [
            dict(file_id=fid, name=c.name[:512], kind=c.kind, start_line=c.start_line, end_line=c.end_line,
                 source=c.source, content_hash=_sha(c.source), commit_sha=commit, doc=c.doc, exported=c.exported,
                 path=rel)
            for c in chunks
        ]
        rows += _keep_unchanged(cur, fid, commit, file_rows) if rel in changed else file_rows
    _insert_symbols(cur, rows)
    _insert_refs(cur, repo_id, prepared, fids, changed)
    cur.execute("update ccctx_repos set indexed_commit = :c, indexed_dirty = :d, indexed_at = systimestamp,"
                " extract_version = :v where id = :i", c=commit, d=dirty, v=EXTRACT_VERSION, i=repo_id)
    build.rebuild(cur, repo_id)
    return len(rows)


def _insert_refs(cur, repo_id: int, prepared: list[tuple], fids: dict[str, int], changed: set[str]) -> None:
    """Replace the call and import refs of every file read, each caller mapped to its kept or inserted symbol."""
    gone = [{"f": fids[rel]} for rel in changed if rel in fids]
    if gone:
        cur.executemany("delete from ccctx_call_refs where file_id = :f", gone)
        cur.executemany("delete from ccctx_import_refs where file_id = :f", gone)
    ids = {(fid, name): sid for sid, fid, name in cur.execute(
        "select s.id, s.file_id, s.name from ccctx_symbols s join ccctx_files f on f.id = s.file_id"
        " where f.repo_id = :r and s.kind <> 'chunk'", r=repo_id)}
    calls, imports = [], []
    for rel, _, _, _, file_calls, file_imports, _, _ in prepared:
        fid = fids[rel]
        calls += [{"f": fid, "c": ids.get((fid, c.caller[:512])) if c.caller else None, "n": c.name[:512],
                   "o": c.form, "r": c.receiver and c.receiver[:512], "l": c.line} for c in file_calls]
        imports += [{"f": fid, "m": i.module[:1024], "v": i.rel_level, "b": i.bound and i.bound[:512]}
                    for i in file_imports]
    if calls:
        cur.executemany("insert into ccctx_call_refs (file_id, caller_id, name, form, receiver, line)"
                        " values (:f, :c, :n, :o, :r, :l)", calls)
    if imports:
        cur.executemany("insert into ccctx_import_refs (file_id, module, rel_level, bound) values (:f, :m, :v, :b)",
                        imports)
