"""Prove the split moved code without changing it (research R9).

    movecheck.py MASTER BRANCH            compare the source definitions of two checkouts
    movecheck.py --tests MASTER BRANCH    compare the test functions, fixtures and helpers
    movecheck.py --report MASTER BRANCH   also print where each definition went, for moves.md
    movecheck.py --imports [BRANCH]       import every module alone in a fresh interpreter

Every top-level function, class and assignment is compared by its syntax tree, after two normalizations: docstrings
are dropped, and references to project modules are made module-free (`semantic.search`, `query.search` and `search`
all become `search`; a module passed as an argument becomes `<module>`). Definitions are matched by name, as multisets,
so a name defined in several files (`_plural`, `log`) matches each copy. Statements that define no name (a
registration call, a loop) are compared as a multiset of their own.
"""

import ast
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PACKAGE = "golestan_code_mcp"

# Differences reviewed and accepted (data-model.md Section 3): name -> (reason, old files, new files). Only the
# copies in those files are excused; a copy of the same name elsewhere is still compared.
CHUNKER, LANGUAGES = "src/golestan_code_mcp/chunker.py", "src/golestan_code_mcp/languages.py"
TABLES = "src/golestan_code_mcp/parsing/tables.py"
# test_memory.py's tests, wherever they are now: the old file, the memory folder's files and helpers, or a conftest
MEMORY_TESTS = ({"tests/test_memory.py"},
                {"tests/test_memory.py", "tests/conftest.py", "tests/memory/conftest.py", "tests/memory/helpers.py"}
                | {f"tests/memory/test_{f}.py" for f in ("store", "runs", "findings", "consolidate", "distill", "recall",
                                                          "recheck")})
ANY_TEST_FILE = None  # the copies in every test file are excused: the shared setup replaced them all (T033)
EXPECTED: dict[str, tuple[str, set[str] | None, set[str] | None]] = {
    **{name: (f"T033: the copies of {name} that were the same are now one, in tests/{where}; a file whose copy "
              "differed keeps its own", ANY_TEST_FILE, ANY_TEST_FILE)
       for name, where in (("conn", "conftest.py"), ("git", "support.py"), ("write", "support.py"),
                           ("commit", "support.py"))},
    **{name: ("Section 3.1: the table starts empty, or with only the languages without rules, and each language file "
              "registers itself; the second, empty copy in languages.py is gone", {CHUNKER, LANGUAGES}, {TABLES})
       for name in ("GRAMMARS", "EXTENSIONS", "NAMES", "WALKERS", "CALLS", "IMPORTS", "SYMBOL_DOCS", "FILE_DOCS",
                    "NAMESPACES", "LEADING")},
    "test_new_grammars_load_only_when_used": ("imports golestan_code_mcp.parsing.chunks, named in its code string, "
                                              "in place of golestan_code_mcp.chunker",
                                              {"tests/test_chunker.py"}, {"tests/test_chunker.py",
                                                                          "tests/parsing/test_chunks.py"}),
    "_boosts": ("its late import of feedback is now an ordinary import: ranking.py has no cycle with feedback.py and "
                "no `feedback` parameter to dodge (research R5)",
                {"src/golestan_code_mcp/semantic.py"}, {"src/golestan_code_mcp/search/ranking.py"}),
    "evaluate": ("its late import of semantic is now an ordinary import of search.query: the cycle it avoided is gone",
                 {"src/golestan_code_mcp/feedback.py"}, {"src/golestan_code_mcp/search/evaluation.py"}),
    "log": ("each memory file that logs gets the area's logger, golestan_code_mcp.memory (research R7)",
            {"src/golestan_code_mcp/memory.py"},
            {f"src/golestan_code_mcp/memory/{f}.py" for f in ("store", "runs", "distill", "consolidate")}),
    "ask": ("finds the tool by name in the server's tool registry (app.mcp) instead of on the old server module: the "
            "nine tools are now in five files", *MEMORY_TESTS),
    "test_search_without_facts_never_loads_the_package": (
        "its code string searches through golestan_code_mcp.search.query, the new home of semantic.search", *MEMORY_TESTS),
    "test_importing_memory_does_not_import_the_package": (
        "imports memory's modules by their new paths; importing the memory package alone now loads only its docstring",
        *MEMORY_TESTS),
    "JS_CALLS": ("reads tables.CALLS by its name instead of chunker's `CALLS as _BASE_CALLS` alias",
                 {LANGUAGES}, {"src/golestan_code_mcp/parsing/languages/typescript.py"}),
}
RENAMED = {"_register": "register"}  # old name -> new name (research R8)


def modules(src: Path) -> set[str]:
    """Dotted names of the package's modules and subpackages, without the package prefix."""
    found = set()
    for path in (src / PACKAGE).rglob("*.py"):
        parts = path.relative_to(src / PACKAGE).with_suffix("").parts
        found.add(".".join(parts[:-1]) if parts[-1] == "__init__" else ".".join(parts))
    return found - {""}


def aliases(tree: ast.Module, known: set[str]) -> set[str]:
    """Local names a file binds to project modules, wherever the import is (late imports included)."""
    bound = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == PACKAGE:
            base = node.module[len(PACKAGE) + 1:]
            for name in node.names:
                if (f"{base}.{name.name}" if base else name.name) in known:
                    bound.add(name.asname or name.name)
        elif isinstance(node, ast.Import):
            for name in node.names:
                if name.name.startswith(PACKAGE + ".") and name.asname:
                    bound.add(name.asname)
    return bound


class Normalize(ast.NodeTransformer):
    def __init__(self, bound: set[str], rename: dict[str, str]):
        self.bound, self.rename = bound, rename

    def _module_attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id in self.bound:
            return ast.Name(id=self.rename.get(node.attr, node.attr), ctx=node.ctx)
        return self.generic_visit(node)

    def visit_Name(self, node):
        return ast.Name(id=self.rename.get(node.id, node.id), ctx=node.ctx)

    def visit_Call(self, node):
        # a module passed as an argument (monkeypatch.setattr(memory, ...), getattr(graph, ...)) names its new home
        node.args = [ast.Name(id="<module>", ctx=a.ctx) if isinstance(a, ast.Name) and a.id in self.bound else a
                     for a in node.args]
        return self.generic_visit(node)

    def _drop_doc(self, node):
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
        return self.generic_visit(node)

    def _definition(self, node):
        node.name = self.rename.get(node.name, node.name)
        return self._drop_doc(node)

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = _definition

    def visit_ImportFrom(self, node):  # a late import of a project module: retargeted, checked by --imports
        return ast.Pass() if (node.module or "").split(".")[0] == PACKAGE else node

    def visit_Import(self, node):
        return ast.Pass() if any(a.name.split(".")[0] == PACKAGE for a in node.names) else node

    def visit_Attribute(self, node):
        if self._from_here(node):
            return ast.Name(id="<this file's folder>", ctx=ast.Load())
        return self._module_attribute(node)

    def visit_Subscript(self, node):
        if self._from_here(node):
            return ast.Name(id="<this file's folder>", ctx=ast.Load())
        return self.generic_visit(node)

    @staticmethod
    def _from_here(node) -> bool:
        """Path(__file__).parent, Path(__file__).resolve().parents[n]: a test file's folder, one level deeper after
        the move, so `.parent` became `.parents[1]` or `.parents[2]`."""
        text = ast.unparse(node)
        return text.startswith("Path(__file__)") and text.endswith(("parent", "]")) and "/" not in text

    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value in self.rename:  # set_defaults, getattr by name
            return ast.Constant(self.rename[node.value])
        return node


def names_of(node) -> list[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)] or \
               [e.id for t in node.targets if isinstance(t, ast.Tuple) for e in t.elts if isinstance(e, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def skipped(node) -> bool:
    """Imports, the module docstring and the `python -m` guard are not definitions."""
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return True
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
        return True
    return isinstance(node, ast.If) and "__name__" in ast.unparse(node.test)


def collect(root: Path, folder: str, rename: dict[str, str]):
    """{name: [(file, dump)]} and [(file, dump)] for statements without a name, plus private cross-file uses."""
    src = root / "src"
    known = modules(src)
    defined, unnamed = defaultdict(list), []
    for path in sorted((root / folder).rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if "/fixtures/" in rel:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        norm = Normalize(aliases(tree, known), rename)
        for node in tree.body:
            if skipped(node):
                continue
            dump = ast.dump(norm.visit(node))
            names = [rename.get(n, n) for n in names_of(node)]
            for name in names:
                defined[name].append((rel, dump))
            if not names:
                unnamed.append((rel, dump))
    return defined, unnamed


def private_uses(root: Path) -> list[tuple[str, str]]:
    """(file, `module._name`) for each underscore name a file takes from another project file."""
    src, uses = root / "src", set()
    known = modules(src)
    for path in sorted((src / PACKAGE).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        bound, rel = aliases(tree, known), path.relative_to(src).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in bound \
                    and node.attr.startswith("_") and not node.attr.startswith("__"):
                uses.add((rel, f"{node.value.id}.{node.attr}"))
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(PACKAGE):
                uses.update((rel, f"{node.module}.{a.name}") for a in node.names
                            if a.name.startswith("_") and not a.name.startswith("__"))
    return sorted(uses)


def _in(path: str, files) -> bool:
    """files is a set of paths, or ANY_TEST_FILE."""
    return files is ANY_TEST_FILE or path in files


def compare(master: Path, branch: Path, folder: str, report: bool) -> int:
    old, old_unnamed = collect(master, folder, RENAMED)
    new, new_unnamed = collect(branch, folder, RENAMED)
    missing = changed = duplicated = 0
    for name in sorted(set(old) | set(new)):
        olds, news = old.get(name, []), new.get(name, [])
        if name in EXPECTED:
            reason, old_files, new_files = EXPECTED[name]
            excused = [f for f, _ in olds if _in(f, old_files)] + [f for f, _ in news if _in(f, new_files)]
            olds = [(f, d) for f, d in olds if not _in(f, old_files)]
            news = [(f, d) for f, d in news if not _in(f, new_files)]
            if excused and folder == "src":
                print(f"expected  {name}: {reason}")
        before, after = Counter(d for _, d in olds), Counter(d for _, d in news)
        if before == after:
            continue
        where_old = sorted({f for f, _ in olds})
        where_new = sorted({f for f, _ in news})
        if not after:
            missing += 1
            print(f"MISSING   {name} (was in {', '.join(where_old)})")
        elif not before:
            if folder == "src":  # new code: __init__ helpers, new files; listed for review
                print(f"new       {name} in {', '.join(where_new)}")
        elif not (before - after):
            extra = after - before
            if any(d in before for d in extra):
                duplicated += 1
                print(f"DUPLICATE {name}: {', '.join(where_new)}")
            else:
                print(f"new       {name} also in {', '.join(where_new)}")
        else:
            changed += 1
            print(f"CHANGED   {name}: {', '.join(where_old)} -> {', '.join(where_new)}")
    lost = Counter(d for _, d in old_unnamed) - Counter(d for _, d in new_unnamed)
    added = Counter(d for _, d in new_unnamed) - Counter(d for _, d in old_unnamed)
    for dump in lost:
        print("unnamed statement removed:", next(f for f, d in old_unnamed if d == dump),
              dump[:160])
    for dump in added:
        print("unnamed statement added:  ", next(f for f, d in new_unnamed if d == dump), dump[:160])
    if report:
        print_report(old, new)
    print(f"{missing} missing, {changed} changed, {duplicated} duplicated")
    return 1 if missing or changed or duplicated else 0


def print_report(old, new):
    """Markdown rows: old file | definitions | new file."""
    moves = defaultdict(list)
    for name, places in old.items():
        targets = {d: f for f, d in new.get(name, [])}
        for was, dump in places:
            now = targets.get(dump) or next((f"{f} (changed: {EXPECTED[name][0].split(':')[0]})"
                                              for f, _ in new.get(name, []) if name in EXPECTED), "(not found)")
            moves[(was, now)].append(name)
    print("\n| Old file | Definitions | New file |\n|---|---|---|")
    for (was, now), names in sorted(moves.items()):
        print(f"| `{was}` | {', '.join(f'`{n}`' for n in sorted(names))} | `{now}` |")


def import_each(branch: Path) -> int:
    src = branch / "src"
    # a package's __main__ runs the program when imported, so it is left out
    dotted = sorted(f"{PACKAGE}.{m}" for m in modules(src) if not m.endswith("__main__")) + [PACKAGE]
    env_code = "import sys; sys.path.insert(0, {!r}); import {}"

    def run(name):
        done = subprocess.run([sys.executable, "-c", env_code.format(str(src), name)], capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=120)
        return name, done.returncode, done.stderr.strip().splitlines()[-1:] if done.returncode else []

    failed = 0
    with ThreadPoolExecutor(8) as pool:
        for name, code, err in pool.map(run, dotted):
            if code:
                failed += 1
                print(f"FAILED {name}: {err}")
    if (src / PACKAGE / "parsing" / "tables.py").exists():
        check = ("import sys; sys.path.insert(0, {!r}); from golestan_code_mcp.parsing import tables; "
                 "assert all([tables.GRAMMARS, tables.WALKERS, tables.CALLS, tables.IMPORTS]), 'empty tables'")
        done = subprocess.run([sys.executable, "-c", check.format(str(src))], capture_output=True, text=True)
        if done.returncode:
            failed += 1
            print("FAILED parsing.tables loaded alone has empty tables")
    print(f"{len(dotted)} modules imported alone, {failed} failed")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    flags = {a for a in argv if a.startswith("--")}
    paths = [Path(a).resolve() for a in argv if not a.startswith("--")]
    if "--imports" in flags:
        return import_each(paths[0] if paths else Path.cwd())
    master, branch = paths
    folder = "tests" if "--tests" in flags else "src"
    code = compare(master, branch, folder, "--report" in flags)
    if "--report" in flags and folder == "src":
        print("\nUnderscore names used from another file:")
        for rel, name in private_uses(branch):
            print(f"- `{rel}` uses `{name}`")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
