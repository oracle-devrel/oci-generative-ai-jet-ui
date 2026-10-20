"""Wiki compiler: write one directory's page from the index alone, with a citation for every record it names.

A page says what its directory is for, names its key symbols and the modules it depends on and is used by.
Every record it names is a citation: a foreign key to the symbol or file, with the commit and content hash it
had at compile time. Locations are read through those keys and never written into the text.
"""

import posixpath
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from golestan_code_mcp.graph import imports as graph_imports
from golestan_code_mcp.parsing import tables
from golestan_code_mcp.wiki import text as wiki_text

COMPILER = "ccctx-wiki/1"  # bump when the page rules change
THRESHOLD = 10

MAX_TEXT = 8000
MAX_KEYS = 10
MAX_TYPES = 4
MAX_CALLED = 5  # named symbols per depended-on module
MAX_PURPOSE = 3

TYPES = ("class", "interface", "type")
ROLES = ("key", "file", "depends", "uses", "calls")  # the citation order
SYMBOL_ROLES = ("key", "calls")
LANGUAGE_NAMES = {"python": "Python", "go": "Go", "javascript": "JavaScript", "csharp": "C#",
                  "typescript": "TypeScript", "tsx": "TSX", "c": "C", "cpp": "C++", "java": "Java", "kotlin": "Kotlin",
                  "rust": "Rust", "php": "PHP", "ruby": "Ruby", "swift": "Swift"}
NO_DOC = "Its code has no documentation; the sections below come from its structure."


@dataclass
class _Index:
    """What a repository's pages are compiled from, read once."""
    repo: str
    commit: str
    files: dict[int, tuple]  # id -> (path, language, doc, content_hash)
    symbols: dict[int, tuple]  # id -> (file id, name, kind, doc, commit_sha, content_hash, exported), named only
    calls: list[tuple[int, int]]  # (calling file id, callee symbol id), one per call edge
    imports: list[tuple[int, int]]  # (importer file id, imported file id)
    external: dict[int, set[str]]
    folder: dict[int, str] = field(default_factory=dict)  # file id -> directory
    names: dict[str, str] = field(default_factory=dict)  # directory -> module name
    outside: Counter = field(default_factory=Counter)  # symbol id -> calls from other directories
    total: Counter = field(default_factory=Counter)  # symbol id -> all calls


@dataclass
class _Draft:
    directory: str
    name: str
    language: str
    symbols: int
    text: str
    citations: list[dict]


# --- compiling -----------------------------------------------------------------------------------------------


def _plain_name(directory: str, repo: str) -> str:
    return repo if directory == "." else directory.removeprefix("src/")


def _names(directories, repo: str) -> dict[str, str]:
    """Each directory's name: one leading src/ dropped, the root named after the repository, a clash by full path."""
    plain = {d: _plain_name(d, repo) for d in directories}
    clashes = Counter(plain.values())
    return {d: d if clashes[n] > 1 else n for d, n in plain.items()}


def _load(cur, repo_id: int, repo: str) -> _Index:
    r = {"r": repo_id}
    commit = cur.execute("select indexed_commit from ccctx_repos where id = :r", r).fetchone()[0]
    index = _Index(
        repo, commit,
        {fid: rest for fid, *rest in cur.execute(
            "select id, path, language, doc, content_hash from ccctx_files where repo_id = :r", r)},
        {sid: tuple(rest) for sid, *rest in cur.execute(
            "select s.id, s.file_id, s.name, s.kind, s.doc, s.commit_sha, s.content_hash, s.exported"
            " from ccctx_symbols s"
            " join ccctx_files f on f.id = s.file_id where f.repo_id = :r and s.kind <> 'chunk'", r)},
        cur.execute(
            "select s.file_id, c.callee_id from ccctx_calls c join ccctx_symbols s on s.id = c.caller_id"
            " join ccctx_files f on f.id = s.file_id where f.repo_id = :r"
            " union all select c.file_id, c.callee_id from ccctx_file_calls c"
            " join ccctx_files f on f.id = c.file_id where f.repo_id = :r", r).fetchall(),
        cur.execute("select i.importer_id, i.imported_id from ccctx_imports i"
                    " join ccctx_files f on f.id = i.importer_id where f.repo_id = :r", r).fetchall(),
        graph_imports.external_imports(cur, repo_id),
    )
    index.folder = {fid: posixpath.dirname(f[0]) or "." for fid, f in index.files.items()}
    for caller, callee in index.calls:
        index.total[callee] += 1
        if index.folder[caller] != index.folder[index.symbols[callee][0]]:
            index.outside[callee] += 1
    return index


def _symbol_citation(index: _Index, role: str, sid: int) -> dict:
    _, name, kind, _, commit, digest, _ = index.symbols[sid]
    return {"s": sid, "f": None, "role": role, "name": name, "kind": kind, "sha": commit, "hash": digest}


def _file_citation(index: _Index, role: str, fid: int) -> dict:
    path, _, _, digest = index.files[fid]
    return {"s": None, "f": fid, "role": role, "name": path, "kind": "file", "sha": index.commit, "hash": digest}


TEST_SUFFIXES = ("_test.go", "_test.py", "Test.cs", "Tests.cs", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx",
                 "_test.c", "_test.cpp", "Test.java", "Tests.java", "Test.kt", "Tests.kt", "Test.php", "_test.rb", "_spec.rb",
                 "Tests.swift")  # a language's test files, ranked last (012 R11)


def _is_test(path: str) -> bool:
    base = posixpath.basename(path)
    return (base.startswith("test_") or base.endswith(TEST_SUFFIXES) or base == "conftest.py"
            or (base.endswith(".rs") and "tests" in path.split("/")[:-1]))  # Rust integration tests


def _page(index: _Index, directory: str) -> _Draft:
    name, sym = index.names[directory], index.symbols
    files = sorted((fid for fid, d in index.folder.items()
                    if d == directory and index.files[fid][1] in tables.GRAMMARS), key=lambda fid: index.files[fid][0])
    own = [sid for sid, s in sym.items() if index.folder[s[0]] == directory]
    language = min(Counter(index.files[sym[s][0]][1] for s in own).items(), key=lambda kv: (-kv[1], kv[0]))[0]
    package = language == "go" or any(posixpath.basename(index.files[f][0]) == "__init__.py" for f in files)
    kinds = sorted(Counter(sym[s][2] for s in own).items(), key=lambda kv: (-kv[1], kv[0]))
    structure = (f"`{name}` is a {LANGUAGE_NAMES.get(language, language)} {'package' if package else 'directory'}"
                 f" of {wiki_text._plural(len(files), 'file')} and {len(own)} definitions:"
                 f" {wiki_text._and([wiki_text._plural(n, kind) for kind, n in kinds])}.")

    def rank(s):  # code before its tests, then what other modules call, then what is exported and documented
        short = sym[s][1].rpartition(".")[2]
        exported = sym[s][6]  # set at parse time by the symbol's own language (012 research R9)
        if exported is None:  # simplified: rows from before migration 10's backfill
            exported = short[:1].isupper() if language == "go" else not short.startswith("_")
        return (_is_test(index.files[sym[s][0]][0]), -index.outside[s], not exported, not sym[s][3],
                -index.total[s], sym[s][1])

    seen: set[str] = set()  # a name defined twice (Go build tags) is listed once, at its best place
    ranked = [s for s in sorted(own, key=rank) if not (sym[s][1] in seen or seen.add(sym[s][1]))]
    types = [s for s in ranked if sym[s][2] in TYPES][:MAX_TYPES]
    keys = types + [s for s in ranked if s not in types][:MAX_KEYS - len(types)]

    base = index.repo if directory == "." else posixpath.basename(directory)
    first = sorted(files, key=lambda f: (posixpath.splitext(posixpath.basename(index.files[f][0]))[0]
                                         not in ("__init__", base), index.files[f][0]))
    purpose = [p for p in (" ".join(wiki_text._sentences(index.files[f][2])) for f in first) if p][:MAX_PURPOSE]
    if not purpose:
        purpose = [p for p in (" ".join(wiki_text._sentences(sym[s][3])) for s in types[:2]) if p]

    depends, users, called = defaultdict(set), defaultdict(set), defaultdict(Counter)
    for importer, imported in index.imports:
        if index.folder[importer] == directory and index.folder[imported] != directory:
            depends[index.folder[imported]].add(imported)
        elif index.folder[imported] == directory and index.folder[importer] != directory:
            users[index.folder[importer]].add(importer)
    for caller, callee in index.calls:
        target = index.folder[sym[callee][0]]
        if index.folder[caller] == directory and target in depends:
            called[target][callee] += 1

    citations = [_symbol_citation(index, "key", s) for s in keys] + [_file_citation(index, "file", f) for f in files]
    depends_lines = []
    for other in sorted(depends, key=index.names.get):
        top = sorted(called[other], key=lambda s: (-called[other][s], sym[s][1]))[:MAX_CALLED]
        depends_lines.append(f"- `{index.names[other]}`"
                             + (f": {wiki_text._ticked(sym[s][1] for s in top)}" if top else ""))
        citations += [_file_citation(index, "depends", f) for f in sorted(depends[other])]
        citations += [_symbol_citation(index, "calls", s) for s in top]
    outside = sorted(set().union(*(index.external.get(f, set()) for f in files)))
    if outside:
        depends_lines.append(f"- Outside the index: {wiki_text._ticked(outside)}")
    for other in users:
        citations += [_file_citation(index, "uses", f) for f in sorted(users[other])]
    used_by = wiki_text._ticked(sorted(index.names[u] for u in users))

    lines = [f"# {name}", "", structure, *(purpose or [NO_DOC]), "", "## Key symbols"]
    for s in keys:
        said = wiki_text._sentences(sym[s][3])
        lines.append(f"- `{sym[s][1]}` ({sym[s][2]}): {said[0] if said else 'no documentation'}")
    lines += ["", "## Depends on", *(depends_lines or ["- none"]), "", "## Used by", f"- {used_by or 'none'}"]
    text = "\n".join(lines) + "\n"
    if len(text) > MAX_TEXT:  # simplified: cut at a line; the citations of what was cut stay, which is harmless
        text = text[:text.rfind("\n", 0, MAX_TEXT) + 1]
    return _Draft(directory, name, language, len(own), text, citations)


def _compile(cur, repo_id: int, repo: str) -> dict[str, _Draft]:
    """A draft page for every qualifying directory of the repository, by directory."""
    index = _load(cur, repo_id, repo)
    counts = Counter(index.folder[s[0]] for s in index.symbols.values())
    qualifying = sorted(d for d, n in counts.items() if n >= THRESHOLD)
    pages = _names(qualifying, repo)
    index.names = {**_names(set(index.folder.values()), repo), **pages}
    return {d: _page(index, d) for d in qualifying}
