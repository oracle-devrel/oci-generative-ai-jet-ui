# Indexing

## Registering codebases

`ccctx` records the codebases to index. The schema (tables `ccctx_repos`, `ccctx_files`, `ccctx_symbols` and `ccctx_migrations`) is created the first time any `ccctx` command runs, or explicitly with `uv run ccctx db migrate`.

```sh
uv run ccctx repo add ../ccctx-repos/flask --name flask
uv run ccctx repo add ../ccctx-repos/gin --name gin
uv run ccctx repo list
```

```text
NAME   PATH                         FILES  SYMBOLS
flask  /home/you/ccctx-repos/flask      0        0
gin    /home/you/ccctx-repos/gin        0        0
```

Paths are stored absolute, with `~` and `..` resolved. Names are 1 to 64 lowercase letters, digits, `-` or `_`. A name or directory can be registered only once. Registering only checks that the path is a directory; it never reads or runs anything inside it.

Exit codes: `0` ok, `1` refused input or a missing setting, `2` the database is unreachable or still starting.

## Ingesting a codebase

`ccctx ingest <name>` indexes a registered git repository as it is on disk. It needs the embedding model and the hybrid index (see [Searching code](search.md#searching-code)) and refuses to run without it. The first ingest indexes everything and prints a summary:

```sh
uv run ccctx ingest flask
```

```text
Scanned   236 files
Skipped     5 files (5 binary)
Indexed 1,353 symbols in 653.3s
Fallback  148 files as line windows (148 no grammar, 0 parse errors)
```

Almost all of that time is the database embedding every symbol for the hybrid index when the ingest commits. On the Free edition container this is CPU-limited, about half a second per symbol.

Later ingests only do the work the changes require. Each repository records the commit it was last indexed at. The next ingest asks git what differs from that commit, adds untracked files and paths that have gone, and compares each file's content hash with what is stored. Only added and changed files are parsed again, and inside a changed file only the functions and classes whose code changed are embedded again: the rest keep their rows and just move to their new lines. Files that were deleted, renamed away, newly ignored, or now too large or binary lose their symbols, so no search result can point at code that is no longer there. Everything else is left alone.

```text
Changed     9 files (2 added, 6 changed, 1 removed)
Unchanged 227 files
Skipped     0 files
Indexed    84 symbols in 6.3s
```

A rename counts as one file removed and one added. `Skipped` and `Fallback` count only the files that run read.

After an upgrade that understands a new language, the next ordinary ingest also reads again the unchanged files of that language, which were windows until then, and says so. They count as changed:

```text
Reparsed   46 files whose language is now understood (46 csharp)
```

When nothing changed:

```text
flask is already up to date at d086db856be1; run with --full to re-index anyway
```

`ccctx ingest <name> --full` throws the repository's index away and rebuilds it, like the first ingest. Use it after changing `CCCTX_VENDOR_DIRS` or `CCCTX_MAX_FILE_BYTES`, or after an upgrade that changes how code is chunked: an incremental run only looks at files whose content changed, so it will not re-apply new rules to the rest. Ingest also rebuilds in full on its own, with a note on stderr, when no revision is recorded (a repository indexed before this feature) or when the recorded commit no longer exists (history rewritten, or the clone replaced).

A failed ingest changes nothing: the index and the recorded commit stay as they were.

How files are chosen:

- **Ignored**: files matched by the repository's `.gitignore` rules, nested ones included, as git applies them. Also symbolic links. `.git` is never read.
- **Vendored**: files under a directory named in `CCCTX_VENDOR_DIRS`, comma-separated, default `vendor,node_modules,third_party`.
- **Too large**: files over `CCCTX_MAX_FILE_BYTES`, default 1048576.
- **Binary**: files that contain a NUL byte or are not valid UTF-8.

Code in thirteen languages is cut into one chunk per definition. Each chunk has its exact line range, decorators, attributes and annotations included, its doc comment's first paragraph as its documentation, and whether its language counts it as public. Its calls and imports feed the code graph and the wiki.

| Language | Files | Definitions |
|---|---|---|
| Python | `.py` | functions, classes, methods |
| Go | `.go` | functions, methods, struct and interface types |
| JavaScript | `.js`, `.mjs`, `.cjs`, `.jsx` | functions (and functions bound to a `const`), classes, methods |
| TypeScript, TSX | `.ts`, `.mts`, `.cts`; `.tsx` | the JavaScript ones, plus interfaces, type aliases and enums |
| C#  | `.cs` | classes, records, structs, interfaces, enums, methods, constructors |
| C, C++ | `.c`; `.cpp`, `.cc`, `.cxx`, `.c++`, `.hpp`, `.hh`, `.hxx`, `.h` | functions, classes, structs, unions, enums, typedefs, methods |
| Java | `.java` | classes, records, interfaces, enums, methods, constructors |
| Kotlin | `.kt`, `.kts` | classes, objects, interfaces, enums, functions, methods, extension functions |
| Rust | `.rs` | functions, structs, enums, traits, type aliases, `impl` methods |
| PHP | `.php` | classes, interfaces, traits, enums, functions, methods |
| Ruby | `.rb`, `.rake`, `Rakefile`, `Gemfile` | modules, classes, methods |
| Swift | `.swift` | classes, structs, enums, protocols, functions, methods, `init` |

How definitions are named and kinded:
- **Names**: a definition is named after the types that enclose it, joined with dots (`DriverFixture.GetWebDriver`, `Outer.Inner.run`). Namespaces and packages are left out of names, as Go packages are: C# and C++ namespaces, Java and Kotlin packages, PHP namespaces and Rust modules. Ruby modules and Kotlin objects hold code of their own, so they are part of names (`Acme.Parser.parse`).
- **Members defined outside their type** are named after it: C++ `void Engine::start()` is `Engine.start`, using the last qualifier; Rust `impl Shape for Circle { fn area }` is `Circle.area`; a Swift `extension Circle` adds `Circle.area`; a Kotlin `fun String.slug()` is the method `String.slug`; a Kotlin companion object's functions are its class's.
- **Kinds**: the existing seven. Structs, enums, unions and type aliases are `type`; interfaces, protocols and traits are `interface`; records, Kotlin objects and Ruby modules are `class`.
- **Not definitions**: declarations without a body (C and C++ prototypes, interface and abstract members), properties, fields and constants. They stay in their type's chunk.
- **`.h` files** are read as C++, which reads most C.

Other text files, and code with a syntax error, are cut into 60-line windows that overlap by 10 lines, with kind `chunk`. Every symbol records the commit the repository was at when its file was last read. A working tree with uncommitted changes is indexed as it is on disk, and a warning is printed. One JSON record per run goes to stderr, with the mode (`full`, `incremental` or `current`) and the added, changed, removed and unchanged counts.

Ingestion only reads files. Git runs with the repository's fsmonitor and hooks disabled, so nothing inside the repository is executed.

Known limits of the new languages:
- **Kotlin**: its grammar fails on some one-line class bodies that hold a function (`interface Shape { fun area(): Double }` followed by another declaration). Such a file falls back to windows and is counted as a parse error. The same code over several lines parses.
- **Syntax only, as for every language**: calls resolve by name, with no type inference or overload resolution. There is no C or C++ preprocessor, so `#ifdef` branches are parsed as written and macros aren't expanded; no build-system include paths; and Rust macro arguments aren't searched for calls.
- **Imports resolve to files by path rules**:
  - C and C++ `#include "..."`: beside the file first, then anywhere in the repository.
  - Java and Kotlin: packages map to folders.
  - Rust: `mod` and `use crate::`.
  - PHP: `require`, and PSR-4 for `use`.
  - Ruby: `require_relative`.
  - TypeScript: relative imports.
  - C#: `using N` reaches the files that declare namespace `N`.
  - Swift: imports are modules, so Swift files depend on no file.

  Anything else is an outside dependency.

Inspect the result:

```sh
uv run ccctx symbols --repo flask --limit 5      # parsed symbols first; --kind chunk shows windows
uv run ccctx stats --by-language                 # files, symbols and fallback chunks per repo and language
```
