"""Code graph, queries: callers, calls, impact and definitions, with GRAPH_TABLE ... MATCH over ccctx_graph."""

from dataclasses import dataclass

from golestan_code_mcp.registry import repo_id as registered

MAX_DEPTH = 5


@dataclass(frozen=True)
class Caller:
    repo: str
    kind: str  # 'file' for a module-level call
    name: str  # '(module)' for a module-level call
    path: str
    line: int
    callee: str  # the qualified name of the definition called


@dataclass(frozen=True)
class Callee:
    caller: str  # the matched definition making the call
    line: int
    repo: str
    kind: str
    name: str
    path: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class Impact:
    hops: int
    repo: str
    kind: str
    name: str
    path: str
    start_line: int
    end_line: int


@dataclass(frozen=True)
class Definition:
    name: str  # the qualified name
    kind: str
    repo: str
    path: str
    start_line: int
    end_line: int  # the full definition's, even when source is cut
    source: str  # the stored source, at most its first MAX_SOURCE_LINES lines
    cut: bool  # true when the stored source had more lines


MAX_DEFINITIONS = 5
MAX_SOURCE_LINES = 400

JOIN = ("join ccctx_symbols s on s.id = g.{} join ccctx_files f on f.id = s.file_id"
        " join ccctx_repos r on r.id = f.repo_id")


def check_depth(depth) -> int:
    if type(depth) is not int or not 1 <= depth <= MAX_DEPTH:
        raise ValueError(f"depth must be between 1 and {MAX_DEPTH}")
    return depth


def _targets(conn, cur, name: str, repos: list[str] | None) -> tuple[dict[int, str], set[int] | None]:
    """id -> qualified name of the definitions matching the name in the chosen repositories, and those repo ids.

    Case-sensitive. A qualified name matches exactly; a bare name matches x and *.x.
    """
    wanted = {registered(conn, n) for n in repos} if repos else None  # unknown names refused first
    cur.execute(
        """select s.id, f.repo_id, s.name from ccctx_symbols s join ccctx_files f on f.id = s.file_id
            where s.kind <> 'chunk'
              and (s.name = :n or (:bare = 1 and substr(s.name, -length(:n) - 1) = '.' || :n))""",
        n=name, bare=int("." not in name),
    )
    targets = {sid: qualified for sid, rid, qualified in cur if wanted is None or rid in wanted}
    if not targets:
        raise ValueError(f"no symbol named '{name}'")
    return targets, wanted


def check_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        raise ValueError("the name is empty")
    return name


def _match(cur, sql: str, ids: list[int]) -> list[tuple]:
    """Run a graph query whose `{ids}` is the target id list, 500 ids at a time (Oracle allows 1000)."""
    rows = []
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        cur.execute(sql.replace("{ids}", ", ".join(f":{n + 1}" for n in range(len(chunk)))), chunk)
        rows += cur.fetchall()
    return rows


def definitions(conn, name: str, repos: list[str] | None = None) -> tuple[list[Definition], int]:
    """The first MAX_DEFINITIONS definitions matching the name, by repository, path, then start line, with their
    stored source cut at MAX_SOURCE_LINES lines, and the number of matches."""
    name = check_name(name)
    with conn.cursor() as cur:
        targets, _ = _targets(conn, cur, name, repos)
        found = _match(cur, """select s.id, r.name, f.path, s.start_line from ccctx_symbols s
              join ccctx_files f on f.id = s.file_id join ccctx_repos r on r.id = f.repo_id
             where s.id in ({ids})""", list(targets))
        first = sorted(found, key=lambda row: (row[1], row[2], row[3], targets[row[0]]))[:MAX_DEFINITIONS]
        rows = _match(cur, """select s.id, s.kind, r.name, f.path, s.start_line, s.end_line, s.source
              from ccctx_symbols s join ccctx_files f on f.id = s.file_id join ccctx_repos r on r.id = f.repo_id
             where s.id in ({ids})""", [row[0] for row in first])
        by_id = {sid: (kind, repo, path, start, end, source.read() if hasattr(source, "read") else source or "")
                 for sid, kind, repo, path, start, end, source in rows}  # read each CLOB while the cursor is open
    result = []
    for sid, *_ in first:
        kind, repo, path, start, end, source = by_id[sid]
        lines = source.split("\n")
        cut = len(lines) - (lines[-1] == "") > MAX_SOURCE_LINES  # a trailing newline ends a line, not starts one
        result.append(Definition(targets[sid], kind, repo, path, start, end,
                                 "\n".join(lines[:MAX_SOURCE_LINES]) if cut else source, cut))
    return result, len(targets)


def callers(conn, name: str, repos: list[str] | None = None) -> list[Caller]:
    """Every call to a definition matching the name, by repository, path, then line."""
    name = check_name(name)
    with conn.cursor() as cur:
        targets, wanted = _targets(conn, cur, name, repos)
        found = _match(cur, f"""select r.id, r.name, s.kind, s.name, f.path, g.line, g.callee_id
              from graph_table (ccctx_graph
                match (c is symbol) -[e is calls]-> (t is symbol)
                where t.id in ({{ids}})
                columns (c.id as caller_id, e.line as line, t.id as callee_id)) g {JOIN.format("caller_id")}""",
                       list(targets))
        found += _match(cur, """select r.id, r.name, 'file', '(module)', f.path, g.line, g.callee_id
              from graph_table (ccctx_graph
                match (c is code_file) -[e is calls]-> (t is symbol)
                where t.id in ({ids})
                columns (c.id as file_id, e.line as line, t.id as callee_id)) g
              join ccctx_files f on f.id = g.file_id join ccctx_repos r on r.id = f.repo_id""", list(targets))
    rows = [Caller(repo, kind, caller, path, line, targets[callee])
            for rid, repo, kind, caller, path, line, callee in found if wanted is None or rid in wanted]
    return sorted(rows, key=lambda c: (c.repo, c.path, c.line, c.name, c.callee))


def calls(conn, name: str, repos: list[str] | None = None) -> list[Callee]:
    """Every indexed symbol called from a definition matching the name, by calling definition, then line."""
    name = check_name(name)
    with conn.cursor() as cur:
        targets, wanted = _targets(conn, cur, name, repos)
        found = _match(cur, f"""select g.caller_id, g.line, r.id, r.name, s.kind, s.name, f.path, s.start_line,
                     s.end_line
              from graph_table (ccctx_graph
                match (t is symbol) -[e is calls]-> (c is symbol)
                where t.id in ({{ids}})
                columns (t.id as caller_id, e.line as line, c.id as callee_id)) g {JOIN.format("callee_id")}""",
                       list(targets))
    rows = [Callee(targets[caller], line, repo, *rest)
            for caller, line, rid, repo, *rest in found if wanted is None or rid in wanted]
    return sorted(rows, key=lambda c: (c.caller, c.line, c.repo, c.path, c.name))


def impact(conn, name: str, depth: int = 3, repos: list[str] | None = None) -> list[Impact]:
    """Every symbol reaching a definition matching the name in at most `depth` call hops, once, nearest first."""
    name = check_name(name)
    depth = check_depth(depth)  # written into the SQL: a quantifier cannot be a bind variable
    # simplified: {1,N} enumerates every path, so a heavily called name costs seconds at depth 3 (gin New: 2.4 s);
    # walk one hop per level from the frontier if that binds
    with conn.cursor() as cur:
        targets, wanted = _targets(conn, cur, name, repos)
        found = _match(cur, f"""select g.hops, r.id, r.name, s.kind, s.name, f.path, s.start_line, s.end_line, s.id
              from (select id, min(hops) as hops
                      from graph_table (ccctx_graph
                        match (c is symbol) -[e is calls]->{{1,{depth}}} (t is symbol)
                        where t.id in ({{ids}})
                        columns (c.id as id, count(e.line) as hops))
                     group by id) g {JOIN.format("id")}""", list(targets))
    nearest: dict[int, tuple] = {}
    for row in found:  # a symbol may come back from several 500-id batches
        if (wanted is None or row[1] in wanted) and (row[-1] not in nearest or row[0] < nearest[row[-1]][0]):
            nearest[row[-1]] = row
    rows = [Impact(hops, repo, *rest) for hops, _, repo, *rest, _ in nearest.values()]
    return sorted(rows, key=lambda i: (i.hops, i.repo, i.path, i.start_line, i.name))
