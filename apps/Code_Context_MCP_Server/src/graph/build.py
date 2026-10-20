"""Code graph, edges: resolve each file's stored call refs to the definitions they call, and rewrite the
repository's call and import edges.

Resolution is by name within one repository, guided by the call form and the file's imports. It is not type
inference, so dynamic calls and calls through variables are not edges.
"""

from golestan_code_mcp.graph import imports

SELF = {"self", "cls", "this", "Self", "base"}
BARE_KINDS = {"function", "class", "type"}  # what a bare call x(...) can reach; type is Go's conversion
# languages where a bare call inside a type may be a method of that type (`Start()` meaning `this.Start()`)
IMPLICIT_SELF = {"csharp", "java", "kotlin", "swift", "cpp", "ruby"}


def _enclosing(symbol: tuple) -> str:
    """The type a definition belongs to: itself for a class, else its name without the last part."""
    _, name, kind = symbol
    return name if kind == "class" else name.rpartition(".")[0]


def _resolve(call: tuple, symbols: dict[int, tuple], by_name: dict[str, list[int]], by_method: dict[str, list[int]],
             imported: dict[int, set[int]], modules: dict[int, set[str]], implicit: bool = False) -> list[int]:
    """The symbols a call reaches, by the four rules, then the same-file, imported-file, whole-repository order.

    With `implicit` (the caller's language lets a bare call reach its own type's methods), a bare call names the
    enclosing type's method first."""
    fid, caller_id, name, form, receiver, _ = call
    receiver = imports._normalize(receiver)
    head = (receiver or "").split(".")[0]
    if form == "bare" or head in modules.get(fid, ()):  # rules 1 and 2
        matches = [s for s in by_name.get(name, []) if symbols[s][2] in BARE_KINDS]
        if form == "bare" and implicit and caller_id in symbols:
            own = f"{_enclosing(symbols[caller_id])}.{name}"
            matches = [s for s in by_method.get(name, []) if symbols[s][1] == own] or matches
    else:  # rules 3 and 4
        matches = by_method.get(name, [])
        if receiver in SELF and caller_id in symbols:
            own = f"{_enclosing(symbols[caller_id])}.{name}"
            matches = [s for s in matches if symbols[s][1] == own] or matches
    for scope in ({fid}, imported.get(fid, set())):
        if near := [s for s in matches if symbols[s][0] in scope]:
            return near
    return matches


def rebuild(cur, repo_id: int) -> None:
    """Delete and rebuild the repository's import and call edges from its stored refs and symbols."""
    # simplified: whole repository rebuilt each ingest, rebuild only the affected names when it shows up in timings
    r = {"r": repo_id}
    files = imports._files(cur, r)
    symbols = {sid: (fid, name, kind) for sid, fid, name, kind in cur.execute(
        "select s.id, s.file_id, s.name, s.kind from ccctx_symbols s join ccctx_files f on f.id = s.file_id"
        " where f.repo_id = :r and s.kind <> 'chunk'", r)}
    import_refs = imports._import_refs(cur, r)
    call_refs = cur.execute(
        "select c.file_id, c.caller_id, c.name, c.form, c.receiver, c.line from ccctx_call_refs c"
        " join ccctx_files f on f.id = c.file_id where f.repo_id = :r", r).fetchall()

    by_name: dict[str, list[int]] = {}
    by_method: dict[str, list[int]] = {}
    for sid, (_, name, kind) in symbols.items():
        by_name.setdefault(name, []).append(sid)
        if kind == "method":
            by_method.setdefault(name.rpartition(".")[2], []).append(sid)
    imported, modules, _ = imports._imports(files, import_refs)

    calls, file_calls = [], []
    for call in call_refs:
        for callee in _resolve(call, symbols, by_name, by_method, imported, modules,
                               files[call[0]][1] in IMPLICIT_SELF):
            if call[1] is None:
                file_calls.append({"f": call[0], "c": callee, "l": call[5]})
            else:
                calls.append({"f": call[1], "c": callee, "l": call[5]})

    cur.execute("delete from ccctx_imports where importer_id in (select id from ccctx_files where repo_id = :r)", r)
    cur.execute("delete from ccctx_file_calls where file_id in (select id from ccctx_files where repo_id = :r)", r)
    cur.execute("delete from ccctx_calls where caller_id in (select s.id from ccctx_symbols s"
                " join ccctx_files f on f.id = s.file_id where f.repo_id = :r)", r)
    pairs = [{"a": a, "b": b} for a, targets in imported.items() for b in targets]
    if pairs:
        cur.executemany("insert into ccctx_imports (importer_id, imported_id) values (:a, :b)", pairs)
    if calls:
        cur.executemany("insert into ccctx_calls (caller_id, callee_id, line) values (:f, :c, :l)", calls)
    if file_calls:
        cur.executemany("insert into ccctx_file_calls (file_id, callee_id, line) values (:f, :c, :l)", file_calls)
