"""Helpers for the schema tests: the expected tables, and inserts of the rows each table holds."""

TABLES = {"CCCTX_MIGRATIONS", "CCCTX_REPOS", "CCCTX_FILES", "CCCTX_SYMBOLS"}


def insert(cur, sql, **binds):
    new_id = cur.var(int)
    cur.execute(f"{sql} returning id into :new_id", new_id=new_id, **binds)
    return new_id.getvalue()[0]


def add_file(cur, repo_id, path="a.py"):
    return insert(
        cur,
        "insert into ccctx_files (repo_id, path, language, content_hash) values (:r, :p, 'python', :h)",
        r=repo_id, p=path, h="0" * 64,
    )


SHA = "a" * 40


def add_symbol(cur, file_id, kind="function", start=1, end=2, sha=SHA):
    return insert(
        cur,
        "insert into ccctx_symbols (file_id, name, kind, start_line, end_line, source, content_hash, commit_sha)"
        " values (:f, 'f', :k, :s, :e, 'def f(): pass', :h, :c)",
        f=file_id, k=kind, s=start, e=end, h="0" * 64, c=sha,
    )


def counts(conn):
    with conn.cursor() as cur:
        return {t: cur.execute(f"select count(*) from {t}").fetchone()[0] for t in sorted(TABLES)}


GRAPH_TABLES = {"CCCTX_CALL_REFS", "CCCTX_IMPORT_REFS", "CCCTX_CALLS", "CCCTX_FILE_CALLS", "CCCTX_IMPORTS"}

WIKI_TABLES = {"CCCTX_WIKI_PAGES", "CCCTX_WIKI_CITATIONS"}

TABLES |= WIKI_TABLES  # so the re-run test counts the wiki tables too


def columns_of(cur, table):
    cur.execute("select column_name, data_type, nullable, char_length from user_tab_columns where table_name = :t", t=table)
    return {name: (kind, nullable, length) for name, kind, nullable, length in cur}


def add_page(cur, repo_id, directory="pkg", name=None, state="fresh", symbols=10):
    return insert(
        cur,
        "insert into ccctx_wiki_pages (repo_id, directory, name, language, symbols, text, search_text, state,"
        " compiled_at, compiler) values (:r, :d, :n, 'python', :s, 'text', 'search', :st, systimestamp, 'ccctx-wiki/1')",
        r=repo_id, d=directory, n=name or directory, s=symbols, st=state,
    )


def add_citation(cur, page_id, role, symbol_id=None, file_id=None):
    return insert(
        cur,
        "insert into ccctx_wiki_citations (page_id, symbol_id, file_id, role, name, kind, commit_sha, content_hash)"
        " values (:p, :s, :f, :r, 'f', 'function', :c, :h)",
        p=page_id, s=symbol_id, f=file_id, r=role, c=SHA, h="0" * 64,
    )


MEMORY_TABLES = {"CCCTX_MEMORY_RUNS", "CCCTX_MEMORY_RUN_REPOS"}

TABLES |= MEMORY_TABLES


def add_run(cur, tool="search_code", status="ok"):
    return insert(cur, "insert into ccctx_memory_runs (tool, arguments, status, ms, result_count, results)"
                       " values (:t, json('{}'), :s, 1, 0, json('[]'))", t=tool, s=status)


# --- usage feedback (specs/011-usage-feedback/data-model.md) ---

TABLES |= {"CCCTX_FEEDBACK"}


def add_use(cur, repo_id, how="cited", run_id=None):
    return insert(cur, "insert into ccctx_feedback (repo_id, path, name, kind, how, client, session_id, run_id)"
                       " values (:r, 'a.py', 'f', 'function', :h, 'c', 's', :run)", r=repo_id, h=how, run=run_id)
