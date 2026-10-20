"""Helpers for the ingest tests: sample files, and readers of what an ingest stored."""

import os
import subprocess
import uuid

from golestan_code_mcp import registry
from golestan_code_mcp.indexing import ingest as indexing_ingest
from golestan_code_mcp.graph import queries

ENV = {"CCCTX_MAX_FILE_BYTES": "2048"}

APP_PY = '''import os


def helper(x):
    return x + 1


class Service:
    def run(self):
        return helper(1)
'''

MAIN_GO = '''package main

func main() {
}
'''

WEB_JS = '''function hello() {
  return 1;
}
'''


def head(path):
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True).stdout.strip()


def try_symlink(root):
    try:
        os.symlink(root / "app.py", root / "link.py")
        return True
    except OSError:  # Windows without symlink privilege
        return False


def register(conn, path):
    name = f"t-{uuid.uuid4().hex[:8]}"
    registry.add_repo(conn, path, name)
    return name


def stored(conn, name):
    with conn.cursor() as cur:
        cur.execute(
            """select f.path, f.language, f.content_hash, s.name, s.kind, s.start_line, s.end_line,
                      s.source, s.content_hash, s.commit_sha
                 from ccctx_files f join ccctx_repos r on r.id = f.repo_id
                 left join ccctx_symbols s on s.file_id = f.id
                where r.name = :n""",
            n=name,
        )
        return [tuple(v.read() if hasattr(v, "read") else v for v in row) for row in cur]


def revision(conn, name):
    with conn.cursor() as cur:
        return cur.execute("select indexed_commit, indexed_dirty from ccctx_repos where name = :n", n=name).fetchone()


def content(conn, name):
    """Stored rows without commit_sha, which unchanged files keep from the run that last read them."""
    return sorted(repr(row[:9]) for row in stored(conn, name))


def symbol_ids(conn, name, path):
    with conn.cursor() as cur:
        cur.execute(
            """select s.id from ccctx_symbols s join ccctx_files f on f.id = s.file_id
                 join ccctx_repos r on r.id = f.repo_id where r.name = :n and f.path = :p order by s.id""",
            n=name, p=path,
        )
        return [row[0] for row in cur]


def named_ids(conn, name, path):
    with conn.cursor() as cur:
        cur.execute(
            """select s.name, s.id from ccctx_symbols s join ccctx_files f on f.id = s.file_id
                 join ccctx_repos r on r.id = f.repo_id where r.name = :n and f.path = :p""",
            n=name, p=path,
        )
        return dict(cur.fetchall())


RELATIONS = {  # refs and edges by names and paths: symbol ids change when code is edited
    "call refs": """select f.path, s.name, c.name, c.form, c.receiver, c.line from ccctx_call_refs c
                      join ccctx_files f on f.id = c.file_id left join ccctx_symbols s on s.id = c.caller_id""",
    "import refs": """select f.path, i.module, i.rel_level, i.bound from ccctx_import_refs i
                        join ccctx_files f on f.id = i.file_id""",
    "calls": """select f.path, s.name, tf.path, t.name, c.line from ccctx_calls c
                  join ccctx_symbols s on s.id = c.caller_id join ccctx_files f on f.id = s.file_id
                  join ccctx_symbols t on t.id = c.callee_id join ccctx_files tf on tf.id = t.file_id""",
    "file calls": """select f.path, tf.path, t.name, c.line from ccctx_file_calls c join ccctx_files f on f.id = c.file_id
                       join ccctx_symbols t on t.id = c.callee_id join ccctx_files tf on tf.id = t.file_id""",
    "imports": """select f.path, t.path from ccctx_imports i join ccctx_files f on f.id = i.importer_id
                    join ccctx_files t on t.id = i.imported_id""",
}


def relations(conn, name):
    with conn.cursor() as cur:
        rid = cur.execute("select id from ccctx_repos where name = :n", n=name).fetchone()[0]
        return {table: sorted(map(repr, cur.execute(sql + " where f.repo_id = :r", r=rid)))
                for table, sql in RELATIONS.items()}


def assert_matches_full(conn, name):
    """FR-006, SC-005 of 006 and FR-012, SC-005 of 007: the incremental index, refs and edges included, are what
    a full rebuild of the same tree stores."""
    before, graph_before = content(conn, name), relations(conn, name)
    assert indexing_ingest.ingest(conn, name, ENV, full=True).mode == "full"
    assert content(conn, name) == before and relations(conn, name) == graph_before


# --- incremental re-ingest ----------------------------------------------------------------------------------


def write(path, text):
    path.write_text(text, encoding="utf-8", newline="\n")


# --- the code graph stays current (007 US4) ------------------------------------------------------------------

LIB_PY = '''def target():
    return 1
'''

USE_PY = '''from lib import target


def caller():
    return target()


def other():
    return target()


target()
'''


def callers_of(conn, name, symbol):
    return {c.name for c in queries.callers(conn, symbol, [name])}


def forget_graph(conn, name):
    """What an index written before step 7 looks like: no refs, no edges, no extract version."""
    with conn.cursor() as cur:
        rid = cur.execute("select id from ccctx_repos where name = :n", n=name).fetchone()[0]
        in_repo = "(select id from ccctx_files where repo_id = :r)"
        for sql in (f"delete from ccctx_call_refs where file_id in {in_repo}",
                    f"delete from ccctx_import_refs where file_id in {in_repo}",
                    f"delete from ccctx_file_calls where file_id in {in_repo}",
                    f"delete from ccctx_imports where importer_id in {in_repo}",
                    f"delete from ccctx_calls where caller_id in (select id from ccctx_symbols where file_id in {in_repo})"):
            cur.execute(sql, r=rid)
        cur.execute("update ccctx_repos set extract_version = null where id = :r", r=rid)
    conn.commit()


def extract_version(conn, name):
    with conn.cursor() as cur:
        return cur.execute("select extract_version from ccctx_repos where name = :n", n=name).fetchone()[0]


# --- docs and the module wiki (009) --------------------------------------------------------------------------

DOC_PY = '''"""Module doc."""


def documented():
    """Does a thing."""
    return 1
'''

DOC_GO = '''package main

// Run runs.
func Run() {
}
'''


def docs(conn, name):
    with conn.cursor() as cur:
        cur.execute("""select f.path, f.doc, s.name, s.doc, s.id from ccctx_files f
                         join ccctx_repos r on r.id = f.repo_id left join ccctx_symbols s on s.file_id = f.id
                        where r.name = :n""", n=name)
        rows = cur.fetchall()
    return {p: d for p, d, *_ in rows}, {s: (d, i) for _, _, s, d, i in rows if s}


def pkg_module(prefix):
    return "".join(f"def {prefix}{i}():\n    return {i}\n\n\n" for i in range(5))


def pages_of(conn, name):
    with conn.cursor() as cur:
        cur.execute("""select p.name, p.state, p.stale_reason from ccctx_wiki_pages p
                         join ccctx_repos r on r.id = p.repo_id where r.name = :n""", n=name)
        return {n: (s, why) for n, s, why in cur}


# --- language coverage (012): exported and namespaces are stored ---


def visibility(conn, name):
    with conn.cursor() as cur:
        cur.execute("""select f.path, f.language, f.namespaces, s.name, s.kind, s.exported
                         from ccctx_files f join ccctx_repos r on r.id = f.repo_id
                         left join ccctx_symbols s on s.file_id = f.id where r.name = :n""", n=name)
        return sorted(cur.fetchall(), key=repr)


CS = "namespace Shop;\n\npublic class Cart\n{\n    public int Total()\n    {\n        return 1;\n    }\n}\n"
