"""Record what users and tools can observe, to compare master with the branch on the same database (research R10).

    baseline.py --out DIR [--steps tools,tables,cli,parse,rows]   record (all steps by default)
    baseline.py --compare A B                                     print the differences between two recordings

Run master's code with PYTHONPATH pointing at a master worktree's src, then the branch's, one after the other, so
both see the same database state: first `--steps tools,tables,cli,parse` for each, then `--steps rows` for each. The
rows step ingests a repository, which shifts the text index's statistics and so the search scores of a later run. The script imports whichever layout it finds (chunker.py or parsing/), so the same
file records both. Durations, timestamps and memory facts are masked or left out; NOISE lists what two runs of
the same code were seen to disagree on (T006).
"""

import asyncio
import contextlib
import dataclasses
import hashlib
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STEPS = ["tools", "tables", "cli", "parse", "rows"]
REPO = "t-baseline"  # a throwaway copy of flask's package, ingested by the rows step
NOISE: dict[str, set[str]] = {}  # step -> item keys two runs of master disagreed on (filled after T006)

DURATION = re.compile(r"(?<![\w.])\d+(\.\d+)?\s?(s|ms)(?!\w)")
STAMP = re.compile(r"\d{4}-\d\d-\d\d[ T]\d\d:\d\d(:\d\d(\.\d+)?)?([+-]\d\d:?\d\d|Z)?")
SECONDS = re.compile(r'"(seconds|ms)": [0-9.]+')  # the JSON log records of ingest, wiki build and consolidate
# Which of several same-named definitions a call's caller, or a citation, points to varies between ingests of the same
# code (moves.md, Bugs found): these columns are left out of the stored rows.
UNSTABLE = {"call_refs": {"caller_line"}, "calls": {"caller_line"}, "wiki_citations": {"symbol_line"}}


def mask(text: str) -> str:
    return SECONDS.sub(r'"\1": <duration>', STAMP.sub("<time>", DURATION.sub("<duration>", text)))


def first(*names):
    """The first of these `module:attribute` paths that imports: the master or the branch location."""
    for name in names:
        module, _, attr = name.partition(":")
        try:
            found = importlib.import_module(module)
        except ImportError:
            continue
        return getattr(found, attr) if attr else found
    raise ImportError(f"none of {names}")


@contextlib.contextmanager
def quiet_memory():
    """No fact hits in searches (they change with every recorded run), and nothing recorded by this script."""
    patched = []
    for owner, attr, value in [(("golestan_code_mcp.memory", "golestan_code_mcp.memory.recall"), "search_facts",
                                lambda *a, **k: []),
                               (("golestan_code_mcp.memory", "golestan_code_mcp.memory.runs"), "record",
                                lambda *a, **k: None)]:
        for name in owner:
            module = importlib.import_module(name)
            if hasattr(module, attr):
                patched.append((module, attr, getattr(module, attr)))
                setattr(module, attr, value)
                break
    try:
        yield
    finally:
        for module, attr, old in patched:
            setattr(module, attr, old)


def describe(value):
    """A comparable description of a table value: functions by name, containers by content."""
    if callable(value):
        return getattr(value, "__qualname__", repr(value))
    if isinstance(value, dict):
        return {str(k): describe(v) for k, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(map(str, value))
    if isinstance(value, (list, tuple)):
        return [describe(v) for v in value]
    return repr(value)


def step_tools() -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def listing():
        params = StdioServerParameters(command=sys.executable, args=["-m", "golestan_code_mcp.server"],
                                       env=dict(os.environ))
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            init = await session.initialize()
            tools = (await session.list_tools()).tools
            return {"server": init.serverInfo.name, "instructions": init.instructions,
                    "tools": [t.model_dump(mode="json", exclude_none=True) for t in tools]}

    return asyncio.run(listing())


def step_tables() -> dict:
    tables = first("golestan_code_mcp.parsing.tables", "golestan_code_mcp.chunker")
    names = ["GRAMMARS", "EXTENSIONS", "NAMES", "WALKERS", "CALLS", "IMPORTS", "SYMBOL_DOCS", "FILE_DOCS",
             "NAMESPACES", "LEADING"]
    found = {n: [[k, describe(v)] for k, v in getattr(tables, n).items()] for n in names}
    found["search LANGUAGES"] = list(first("golestan_code_mcp.search.query:LANGUAGES",
                                           "golestan_code_mcp.semantic:LANGUAGES"))
    return found


def cli_commands(conn) -> list[list[str]]:
    """Help for every command, each argument error, and read-only commands against the indexed repositories."""
    parser = first("golestan_code_mcp.cli.parser:parser", "golestan_code_mcp.cli:parser")()
    helps = [["--help"]]

    def walk(p, path):
        for action in p._actions:
            if action.__class__.__name__ == "_SubParsersAction":
                for name, sub in action.choices.items():
                    helps.append([*path, name, "--help"])
                    walk(sub, [*path, name])

    walk(parser, [])
    with conn.cursor() as cur:
        cur.execute("select r.name, p.name from ccctx_wiki_pages p join ccctx_repos r on r.id = p.repo_id "
                    "where r.name not like 't-%' order by r.name, p.name")
        pages = cur.fetchall()
    questions = ["url_for", "how are routes registered", "JSON encoding of responses", "Context.JSON",
                 "middleware chain", "render a template", "session cookie signing", "the json module",
                 "package binding", "login page object", "ServeHTTP", "Blueprint", "error handler", "abort"]
    errors = [["search", ""], ["search", "x", "--mode", "bad"], ["search", "x", "--limit", "0"],
              ["search", "x", "--limit", "abc"], ["search", "x", "--language", "cobol"], ["callers", ""],
              ["impact", "x", "--depth", "9"], ["impact", "x", "--depth", "x"], ["repo", "add", ".", "--name", "Bad!"],
              ["symbols", "--repo", "nope"], ["ingest", "nope"], ["wiki", "show", "nope", "--repo", "flask"],
              ["eval", "--gold", "missing.json"], ["feedback", "list", "--repo", "nope"], ["memory", "list",
              "--limit", "0"], ["feedback", "add", "x", "--repo", "flask", "--count", "0"], ["stats"], ["bogus"]]
    reads = [["repo", "list"], ["stats", "--by-language"], ["stats", "--by-language", "--repo", "gin"],
             ["wiki", "list"], ["wiki", "list", "--repo", "gin"], ["feedback", "list", "--repo", "flask"],
             ["eval", "--gold", "gold.json"], ["eval", "--gold", "gold.json", "--limit", "5"]]
    reads += [["symbols", "--repo", r, "--limit", "5"] for r in ("flask", "gin", "selenium-e2e")]
    reads += [["symbols", "--repo", "gin", "--kind", k, "--limit", "3"]
              for k in ("function", "method", "class", "type", "interface", "chunk")]
    for q in questions:
        reads += [["search", q, "--mode", m, "--no-feedback"] for m in ("hybrid", "text", "vector")]
    reads += [["search", "url_for"], ["search", "routing", "--repo", "flask,gin", "--no-feedback"],
              ["search", "Context", "--language", "go", "--limit", "5", "--no-feedback"]]
    for name in ("url_for", "Flask.url_for", "Context.JSON", "render_template", "New"):
        reads += [["callers", name], ["calls", name], ["impact", name, "--depth", "2"]]
    for repo, page in pages[::max(1, len(pages) // 8)]:
        reads += [["wiki", "show", page, "--repo", repo], ["wiki", "citations", page, "--repo", repo]]
    return helps + errors + reads


def run_cli(argv: list[str]) -> dict:
    main = first("golestan_code_mcp.cli:main")
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as e:
            code = e.code
    return {"exit": code, "out": mask(out.getvalue()), "err": mask(err.getvalue())}


def connect():
    db, config = first("golestan_code_mcp.db"), first("golestan_code_mcp.config")
    return db.connect(config.load())


def step_cli() -> dict:
    conn = connect()
    commands = cli_commands(conn)
    conn.close()
    os.chdir(ROOT)  # gold.json is read from the current directory
    with quiet_memory():
        return {" ".join(c) or "(none)": run_cli(c) for c in commands}


def step_parse() -> dict:
    chunks = first("golestan_code_mcp.parsing.chunks", "golestan_code_mcp.chunker")
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("select name, path from ccctx_repos where name in ('flask', 'gin', 'selenium-e2e')")
        roots = {name: Path(path) for name, path in cur.fetchall()}
    conn.close()
    roots["fixtures"] = ROOT / "tests" / "fixtures"

    def plain(value):
        if dataclasses.is_dataclass(value):
            return dataclasses.asdict(value)
        if hasattr(value, "_asdict"):
            return value._asdict()
        return value

    found = {}
    for repo, root in sorted(roots.items()):
        listed = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True).stdout.splitlines()
        paths = listed if repo != "fixtures" else [p.relative_to(root).as_posix() for p in root.rglob("*")
                                                   if p.is_file()]
        for rel in sorted(paths):
            path = root / rel
            if not path.is_file():
                continue
            text = path.read_bytes().decode("utf-8", errors="replace")
            language = chunks.detect_language(rel)
            parsed = chunks.parse(language, text)
            value = [language, "windows", chunks.windows(rel, text)] if parsed is None else [language, *parsed]
            dumped = json.dumps(value, default=plain, sort_keys=True)
            found[f"{repo}/{rel}"] = hashlib.sha256(dumped.encode()).hexdigest()
    return found


ROWS = {
    "repos": "select extract_version, indexed_commit, indexed_dirty from ccctx_repos r where r.name = :n",
    "files": "select f.* from ccctx_files f join ccctx_repos r on r.id = f.repo_id where r.name = :n",
    "symbols": "select f.path file_path, s.* from ccctx_symbols s join ccctx_files f on f.id = s.file_id "
               "join ccctx_repos r on r.id = f.repo_id where r.name = :n",
    "call_refs": "select f.path file_path, cs.name caller_name, cs.start_line caller_line, c.* "
                 "from ccctx_call_refs c join ccctx_files f on f.id = c.file_id "
                 "left join ccctx_symbols cs on cs.id = c.caller_id join ccctx_repos r on r.id = f.repo_id "
                 "where r.name = :n",
    "import_refs": "select f.path file_path, i.* from ccctx_import_refs i join ccctx_files f on f.id = i.file_id "
                   "join ccctx_repos r on r.id = f.repo_id where r.name = :n",
    "calls": "select af.path caller_path, a.name caller, a.start_line caller_line, bf.path callee_path, "
             "b.name callee, b.start_line callee_line, c.line from ccctx_calls c "
             "join ccctx_symbols a on a.id = c.caller_id join ccctx_files af on af.id = a.file_id "
             "join ccctx_symbols b on b.id = c.callee_id join ccctx_files bf on bf.id = b.file_id "
             "join ccctx_repos r on r.id = af.repo_id where r.name = :n",
    "file_calls": "select f.path file_path, bf.path callee_path, b.name callee, b.start_line callee_line, c.line "
                  "from ccctx_file_calls c join ccctx_files f on f.id = c.file_id "
                  "join ccctx_symbols b on b.id = c.callee_id join ccctx_files bf on bf.id = b.file_id "
                  "join ccctx_repos r on r.id = f.repo_id where r.name = :n",
    "imports": "select a.path importer, b.path imported from ccctx_imports i join ccctx_files a "
               "on a.id = i.importer_id join ccctx_files b on b.id = i.imported_id "
               "join ccctx_repos r on r.id = a.repo_id where r.name = :n",
    "wiki_pages": "select p.* from ccctx_wiki_pages p join ccctx_repos r on r.id = p.repo_id where r.name = :n",
    "wiki_citations": "select p.directory, sf.path symbol_path, s.name symbol, s.start_line symbol_line, "
                      "cf.path cited_file, c.* from ccctx_wiki_citations c join ccctx_wiki_pages p "
                      "on p.id = c.page_id left join ccctx_symbols s on s.id = c.symbol_id "
                      "left join ccctx_files sf on sf.id = s.file_id left join ccctx_files cf on cf.id = c.file_id "
                      "join ccctx_repos r on r.id = p.repo_id where r.name = :n",
}


def rows(conn) -> dict:
    """Each table's rows for the throwaway repository: ids dropped, long text hashed, times masked, sorted."""
    import oracledb

    oracledb.defaults.fetch_lobs = False
    found = {}
    with conn.cursor() as cur:
        for table, sql in ROWS.items():
            cur.execute(sql, n=REPO)
            columns = [d[0].lower() for d in cur.description]
            keep = [i for i, c in enumerate(columns)
                    if c != "id" and not c.endswith("_id") and c not in UNSTABLE.get(table, ())]
            listed = []
            for row in cur.fetchall():
                record = {}
                for i in keep:
                    value = row[i]
                    if hasattr(value, "isoformat"):
                        value = "<time>"
                    elif isinstance(value, (bytes, bytearray)):
                        value = hashlib.sha256(value).hexdigest()
                    elif isinstance(value, str) and len(value) > 200:
                        value = "sha256:" + hashlib.sha256(value.encode()).hexdigest()
                    elif not isinstance(value, (str, int, float, bool, type(None))):
                        value = str(value)
                    record[columns[i]] = value
                listed.append(record)
            found[table] = sorted(listed, key=lambda r: json.dumps(r, sort_keys=True, default=str))
    return found


def step_rows() -> dict:
    """Ingest a fixed copy of flask's package from scratch, build its wiki, and record every stored row."""
    flask = None
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("delete from ccctx_repos where name = :n", n=REPO)
        cur.execute("select path from ccctx_repos where name = 'flask'")
        flask = Path(cur.fetchone()[0])
    conn.commit()
    conn.close()
    copy = Path(tempfile.gettempdir()) / "ccctx-baseline-repo"
    shutil.rmtree(copy, ignore_errors=True)
    shutil.copytree(flask / "src" / "flask", copy / "src" / "flask")
    fixed = {**os.environ, "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "baseline"]):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "core.autocrlf=false", *args],
                       cwd=copy, check=True, env=fixed)
    os.chdir(ROOT)
    with quiet_memory():
        printed = {" ".join(c): run_cli(c) for c in (["repo", "add", str(copy), "--name", REPO],
                                                     ["ingest", REPO, "--full"], ["wiki", "build", "--repo", REPO])}
    conn = connect()
    found = {"printed": printed, **rows(conn)}
    with conn.cursor() as cur:
        cur.execute("delete from ccctx_repos where name = :n", n=REPO)
    conn.commit()
    conn.close()
    return found


def retrying(step):
    """One retry for ORA-51815, the stale vector index snapshot of the rebuilt database (research R10)."""
    try:
        return step()
    except Exception as e:
        if "ORA-51815" not in str(e):
            raise
        print(f"{step.__name__}: ORA-51815, retrying once", file=sys.stderr)
        return step()


def record(out: Path, steps: list[str]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name in steps:
        found = retrying(globals()[f"step_{name}"])
        (out / f"{name}.json").write_text(json.dumps(found, indent=1, sort_keys=True, default=str), encoding="utf-8")
        print(f"{name}: {len(found)} items")


def masked(value):
    """The masks applied again, so recordings made before a mask was added still compare."""
    if isinstance(value, str):
        return mask(value)
    if isinstance(value, dict):
        return {k: masked(v) for k, v in value.items()}
    if isinstance(value, list):
        return [masked(v) for v in value]
    return value


def compare(a: Path, b: Path) -> int:
    differences = 0
    for name in STEPS:
        if not (a / f"{name}.json").exists() or not (b / f"{name}.json").exists():
            continue
        left = masked(json.loads((a / f"{name}.json").read_text(encoding="utf-8")))
        right = masked(json.loads((b / f"{name}.json").read_text(encoding="utf-8")))
        for key in sorted(set(left) | set(right)):
            if key in NOISE.get(name, set()) or left.get(key) == right.get(key):
                continue
            differences += 1
            print(f"{name} / {key}:")
            print("  before:", json.dumps(left.get(key), sort_keys=True)[:600])
            print("  after: ", json.dumps(right.get(key), sort_keys=True)[:600])
    print("no differences" if not differences else f"{differences} differences")
    return 1 if differences else 0


def main(argv: list[str]) -> int:
    if argv[0] == "--compare":
        return compare(Path(argv[1]), Path(argv[2]))
    out = Path(argv[argv.index("--out") + 1])
    steps = argv[argv.index("--steps") + 1].split(",") if "--steps" in argv else STEPS
    record(out, steps)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
