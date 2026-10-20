"""Code graph, imports: resolve each file's stored import refs to the indexed files they name, per language.

Resolution is by path and module name within one repository. An import that names no indexed file is an
outside package, kept for the wiki's Depends on section.
"""

import json
import posixpath
import re
from collections import Counter
from pathlib import PurePosixPath

JS_SUFFIXES = ("", ".js", ".mjs", ".cjs", ".jsx", "/index.js")
TS_SUFFIXES = ("", ".ts", ".tsx", ".d.ts", "/index.ts", "/index.tsx", *JS_SUFFIXES[1:])


def _suffix_index(paths: dict[str, int]) -> dict[str, list[int]]:
    """Every file under each of its path suffixes (`a/b/C.java`, `b/C.java`, `C.java`): what includes, packages and
    PSR-4 names are matched against when the importing file's folder does not hold them."""
    index: dict[str, list[int]] = {}
    for path, fid in paths.items():
        parts = path.split("/")
        for i in range(len(parts)):
            index.setdefault("/".join(parts[i:]), []).append(fid)
    return index


SEPARATORS = re.compile(r"::|->")


def _normalize(receiver: str | None) -> str | None:
    """A receiver as a dotted name: `Foo::bar` and `self->x` use dots, and PHP's `$this` is `this`."""
    if receiver is None:
        return None
    return ".".join(part.lstrip("$") for part in SEPARATORS.sub(".", receiver).split("."))


def _folder_index(paths: dict[str, int], extensions: tuple[str, ...]) -> dict[str, list[int]]:
    """Every folder suffix (`src/com/acme`, `com/acme`, `acme`) -> its files with these extensions: where a Java or
    Kotlin package import that names no file points."""
    index: dict[str, list[int]] = {}
    for path, fid in paths.items():
        if path.endswith(extensions):
            parts = path.split("/")[:-1]
            for i in range(len(parts)):
                index.setdefault("/".join(parts[i:]), []).append(fid)
    return index


def _jvm(module: str, suffixes: dict[str, list[int]], folders: dict[str, list[int]]) -> list[int]:
    """`a.b.C` -> a/b/C.java or a/b/C.kt; `a.b.*`, and a Kotlin function import naming no file, -> the folder a/b."""
    if module.endswith(".*"):
        return folders.get(module[:-2].replace(".", "/"), [])
    rel = module.replace(".", "/")
    for candidate in (rel, rel.rpartition("/")[0]):  # the class, or the class of a static member
        for extension in (".java", ".kt"):
            if found := suffixes.get(candidate + extension):
                return found
    return folders.get(rel.rpartition("/")[0], [])


def _rust_crate(folder: str, paths: dict[str, int]) -> str | None:
    """The nearest folder at or above this one holding a crate root (lib.rs or main.rs)."""
    while True:
        if any(posixpath.join(folder, root) in paths for root in ("lib.rs", "main.rs")):
            return folder
        if not folder:
            return None
        folder = posixpath.dirname(folder)


def _rust_files(base: str, names: list[str], paths: dict[str, int]) -> list[int]:
    """The file of the longest module path under base: a/b.rs or a/b/mod.rs, then a.rs or a/mod.rs."""
    for k in range(len(names), 0, -1):
        stem = posixpath.join(base, *names[:k])
        for candidate in (stem + ".rs", stem + "/mod.rs"):
            if candidate in paths:
                return [paths[candidate]]
    return []


def _rust(module: str, level: int, importer: str, paths: dict[str, int]) -> list[int]:
    """`mod x;` (level 1) and `use crate::`, `self::` and `super::` paths to the files of their modules."""
    folder, base = posixpath.split(importer)
    here = folder if base in ("mod.rs", "lib.rs", "main.rs") else posixpath.join(folder, base[:-3])
    if level:
        return _rust_files(here, [module], paths)
    names = module.split("::")
    if names[0] == "crate":
        root = _rust_crate(folder, paths)
        return [] if root is None else _rust_files(root, names[1:], paths)
    if names[0] in ("self", "super"):
        while names and names[0] in ("self", "super"):
            here = posixpath.dirname(here) if names.pop(0) == "super" else here
        return _rust_files(here, names, paths)
    return []


def _python_index(paths: dict[str, int]) -> dict[str, list[int]]:
    """Every Python file under each path suffix that starts at a source root (a directory that is no package).

    `src/flask/helpers.py` is found as `flask/helpers.py` but not as `helpers.py`, so `import json` never
    reaches `src/flask/json/__init__.py`.
    """
    packages = {str(PurePosixPath(p).parent) for p in paths if p.endswith("__init__.py")}
    index: dict[str, list[int]] = {}
    for path, fid in paths.items():
        if path.endswith(".py"):
            parts = path.split("/")
            for i in range(len(parts)):
                if i == 0 or "/".join(parts[:i]) not in packages:
                    index.setdefault("/".join(parts[i:]), []).append(fid)
    return index


def _python(module: str, level: int, importer: str, paths: dict[str, int],
            index: dict[str, list[int]]) -> tuple[list[int], bool]:
    """The files a Python import names, and whether it names a module (not a member of one)."""
    names = [n for n in module.split(".") if n]
    dirs = list(PurePosixPath(importer).parent.parts)
    if level - 1 > len(dirs):
        return [], False
    base = dirs[:len(dirs) - level + 1] if level else []
    for stem, is_module in ((names, True), (names[:-1], False)):  # the module itself, then its parent package
        if not stem and not level:
            continue
        for candidate in ([f"{'/'.join(base + stem)}.py"] if stem else []) + ["/".join(base + stem + ["__init__.py"])]:
            found = ([paths[candidate]] if candidate in paths else []) if level else index.get(candidate, [])
            if found:
                return found, is_module
    return [], False


def _go_module(modules: set[str], dirs: set[str]) -> str | None:
    """The repository's Go module path: what its own package imports have in front of a repository directory."""
    votes = Counter(m[:-len(d) - 1] for m in modules for d in dirs if d and m.endswith("/" + d))
    return votes.most_common(1)[0][0] if votes else None


def _imports(files: dict[int, tuple[str, str]], refs: list[tuple]
             ) -> tuple[dict[int, set[int]], dict[int, set[str]], dict[int, set[str]]]:
    """Per importing file: the files it imports, the names it binds to a module of this repository, and the outside
    packages it imports (refs resolving to no file, by the name OUTSIDE gives them; never a relative import)."""
    paths = {path: fid for fid, (path, *_) in files.items()}
    index = _python_index(paths)
    suffixes = _suffix_index(paths)
    folders = _folder_index(paths, (".java", ".kt"))
    go_dirs: dict[str, list[int]] = {}
    declared: dict[str, list[int]] = {}  # namespace -> the files declaring it (C#)
    for fid, (path, language, spaces) in files.items():
        if language == "go":
            go_dirs.setdefault(posixpath.dirname(path), []).append(fid)
        for space in spaces or ():
            declared.setdefault(space, []).append(fid)
    go_module = _go_module({m for fid, m, _, _ in refs if files[fid][1] == "go"}, set(go_dirs))

    imported: dict[int, set[int]] = {}
    modules: dict[int, set[str]] = {}
    external: dict[int, set[str]] = {}
    for fid, module, level, bound in refs:
        path, language, _ = files[fid]
        found, is_module = [], True
        if language == "python":
            found, is_module = _python(module, level, path, paths, index)
        elif language == "go" and go_module and (module == go_module or module.startswith(go_module + "/")):
            found = go_dirs.get(module[len(go_module) + 1:], [])
        elif language == "javascript":
            target = posixpath.normpath(posixpath.join(posixpath.dirname(path), module))
            found = next(([paths[target + s]] for s in JS_SUFFIXES if target + s in paths), [])
        elif language in ("typescript", "tsx"):  # `./x` may be x.ts; `./x.js` is often written for x.ts
            target = posixpath.normpath(posixpath.join(posixpath.dirname(path), module))
            tried = [target + s for s in TS_SUFFIXES] + ([target[:-3] + ".ts", target[:-3] + ".tsx"]
                                                         if target.endswith(".js") else [])
            found = next(([paths[c]] for c in tried if c in paths), [])
        elif language in ("c", "cpp") and not module.startswith("<"):  # "p": beside the file, then by path
            beside = posixpath.normpath(posixpath.join(posixpath.dirname(path), module))
            found = [paths[beside]] if beside in paths else suffixes.get(posixpath.normpath(module), [])
        elif language in ("java", "kotlin"):
            found = _jvm(module, suffixes, folders)
        elif language == "rust":
            found = _rust(module, level, path, paths)
        elif language in ("php", "ruby") and level:  # require(_once) and require_relative: beside the file
            target = posixpath.normpath(posixpath.join(posixpath.dirname(path), module))
            found = next(([paths[c]] for c in (target, target + ".rb") if c in paths), [])
        elif language == "php":  # use A\B\C; by PSR-4: the longest path suffix naming a file
            names = module.split("\\")
            found = next((suffixes[c] for k in range(len(names)) if (c := "/".join(names[k:]) + ".php") in suffixes),
                         [])
        elif language == "ruby":  # require "a/b": a file of the repository ending a/b.rb, else a gem
            found = suffixes.get(module + ".rb", [])
        elif language == "csharp":  # `using N;`, or `using static N.T;` naming a type of N
            found = declared.get(module) or declared.get(module.rpartition(".")[0], [])
        if not found and language in OUTSIDE and not level and (package := OUTSIDE[language](module)):
            external.setdefault(fid, set()).add(package)  # stored JS refs are all relative
        found = [f for f in found if f != fid]
        if found:
            imported.setdefault(fid, set()).update(found)
            if is_module and bound:
                modules.setdefault(fid, set()).add(bound)
    return imported, modules, external


# language -> the outside package an unresolved import names
OUTSIDE = {"python": lambda m: m.split(".")[0], "go": str, "csharp": str, "c": lambda m: m.strip("<>"),
           "cpp": lambda m: m.strip("<>"),
           "java": lambda m: m[:-2] if m.endswith(".*") else m.rpartition(".")[0],
           "kotlin": lambda m: m[:-2] if m.endswith(".*") else m.rpartition(".")[0],
           "rust": lambda m: None if m.split("::")[0] in ("crate", "self", "super") else m.split("::")[0],
           "php": lambda m: m.split("\\")[0], "ruby": str, "swift": str}


def _files(cur, r: dict) -> dict[int, tuple[str, str, list[str] | None]]:
    """file id -> (path, language, the namespaces it declares or None)."""
    return {fid: (path, language, json.loads(spaces) if isinstance(spaces, str) else spaces)
            for fid, path, language, spaces in cur.execute(
                "select id, path, language, namespaces from ccctx_files where repo_id = :r", r)}


def _import_refs(cur, r: dict) -> list[tuple]:
    return cur.execute(
        "select i.file_id, i.module, i.rel_level, i.bound from ccctx_import_refs i"
        " join ccctx_files f on f.id = i.file_id where f.repo_id = :r", r).fetchall()


def external_imports(cur, repo_id: int) -> dict[int, set[str]]:
    """Per file id, the outside packages it imports: its stored import refs that resolve to no indexed file."""
    r = {"r": repo_id}
    return _imports(_files(cur, r), _import_refs(cur, r))[2]
