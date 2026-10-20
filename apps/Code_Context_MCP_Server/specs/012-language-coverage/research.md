# Research: Language Coverage

## R1. Grammar packages

**Decision**: add these PyPI packages, each with prebuilt wheels:

| Package | Version | Entry point | ABI |
|---|---|---|---|
| `tree-sitter-typescript` | 0.23.2 | `language_typescript()`, `language_tsx()` | 14 |
| `tree-sitter-c-sharp` | 0.23.5 | `language()` | 15 |
| `tree-sitter-c` | 0.24.2 | `language()` | 15 |
| `tree-sitter-cpp` | 0.23.4 | `language()` | 14 |
| `tree-sitter-java` | 0.23.5 | `language()` | 14 |
| `tree-sitter-kotlin` | 1.1.0 | `language()` | 14 |
| `tree-sitter-rust` | 0.24.2 | `language()` | 15 |
| `tree-sitter-php` | 0.25.1 | `language_php()` (PHP with HTML) | 15 |
| `tree-sitter-ruby` | 0.23.1 | `language()` | 14 |
| `tree-sitter-swift` | 0.7.4 | `language()` | 15 |

Each version is bounded below its next major in `pyproject.toml` (for example `tree-sitter-kotlin>=1.1,<2`). Kotlin is
the only grammar at 1.x, so its bound differs.

**How it was verified (2026-10-13)**:
- All ten installed into a scratch environment with `tree-sitter` 0.25.2, the version the project pins below 0.26.
- Each parsed a sample of the constructs the acceptance scenarios name. Nine of them produced no errors.
- **Kotlin limit**: Kotlin fails on a one-line class or interface body that holds a function, when another
  declaration follows (`interface Shape { fun area(): Double }` then `data class P(...)`). Written over several
  lines, the same code parses. A file that hits this falls back to windows and is counted as a parse error (FR-006).
- **Swift**: two declarations on one line with no separator failed too, but that isn't valid Swift.

**Rationale**: these are the same family as the existing three: tree-sitter grammars running in-process, read-only,
with no network (constitution I, VII).

**Alternatives considered**:
- **Language servers** (Roslyn, clangd, rust-analyzer): they give type-resolved calls, but need a build, the project's
  dependencies, and a running process per language. That breaks "no compiler, no build" (spec Assumptions) and VII.
- **`tree-sitter-language-pack`** (one package, about 160 grammars): one dependency instead of ten, but a large
  download, and its tree-sitter version moves with it, against the 0.25 pin.
- **Regex extraction**: rejected by constitution II.

## R2. Language names and extensions

**Decision**: these language values, as stored in `ccctx_files.language` and accepted by `--language`:

| Value | Extensions and file names |
|---|---|
| `typescript` | `.ts`, `.mts`, `.cts` |
| `tsx` | `.tsx` |
| `csharp` | `.cs` |
| `c` | `.c` |
| `cpp` | `.cpp`, `.cc`, `.cxx`, `.c++`, `.hpp`, `.hh`, `.hxx`, `.h` |
| `java` | `.java` |
| `kotlin` | `.kt`, `.kts` |
| `rust` | `.rs` |
| `php` | `.php` |
| `ruby` | `.rb`, `.rake`, `Rakefile`, `Gemfile` |
| `swift` | `.swift` |

- **File names**: `detect_language` checks a small `NAMES` map (`Rakefile`, `Gemfile`) before the extension.
- **`.h` is `cpp`**: C++ rules read most C headers. A C-only header that doesn't parse as C++ falls back to windows.
- **`tsx` is its own language**: the TypeScript grammar can't read JSX, and the TSX grammar misreads `<T>x` type
  assertions in `.ts` files. Search treats them as two values, as `javascript` covers `.jsx` with one grammar today.

**Rationale**: values are short, lowercase and stable, like `python` and `go`. The wiki shows plain names (R11).

## R3. Loading grammars

**Decision**: `GRAMMARS` maps each language to a module name and an entry-point function, imported on the first
parse of that language (`importlib.import_module`, cached with `_parser`). The three existing grammars stay imported at
the top of `chunker.py`, unchanged.

**Rationale**:
- **Startup and ingest time** (SC-006): a repository without Swift never loads the Swift grammar.
- **The 011 lesson**: on Windows, loading an extension module while the stdio server's reader blocks on stdin hangs
  the process. The server never parses (only ingest calls the chunker, verified by grep), so lazy loading is safe. A
  test asserts that importing `server` loads no new grammar.

## R4. Definition names

**Decision**:
- **Qualified names**: a definition's name joins its enclosing types with dots.
- **Grouping-only containers are left out**, as Go packages are: C# and C++ namespaces (both block and file-scoped
  forms), Java and Kotlin packages, PHP namespaces, and Rust `mod` blocks.
- **Containers that hold code are part of names**: classes, structs, interfaces, records, enums, Kotlin `object`s, and
  Ruby modules.

| Case | Name |
|---|---|
| C++ `void app::Engine::start() {}` outside its class | `Engine.start`: the last qualifier only, since a namespace and a class can't be told apart by syntax |
| Rust `impl Shape for Circle { fn area }`, `impl<T> Stack<T> { fn push }` | `Circle.area`, `Stack.push` (generics removed) |
| Swift `extension Circle: Shape { func area }` | `Circle.area` |
| Kotlin `fun String.slug()` | `String.slug`, a method, so `"x".slug()` resolves like any method call |
| Kotlin `companion object { fun create() }` inside `Order` | `Order.create`: the companion is transparent |
| C# `partial class P` in two files | `P` twice, each with its members |
| Ruby `module Acme; class Parser; def parse` | `Acme`, `Acme.Parser`, `Acme.Parser.parse`; `def self.create` is `Acme.Parser.create` |
| C# and Java constructors | `Order.Order`; Swift `init` is `Engine.init`; Kotlin primary constructors are part of the class |
| TypeScript `export const f = () => ...` | `f`, a function, as in JavaScript |

**Rationale**: `get_symbol url_for` already matches every `X.url_for`, so short, type-qualified names are what clients
use. Leaving namespaces out keeps names readable and matches Go.

**Alternatives considered**: keeping namespaces in names (`EATestFramework.Driver.DriverFixture.GetWebDriver`). Exact,
but unlike the existing languages, and every name would need its namespace typed.

## R5. Kinds

**Decision**: the existing seven kinds, with this mapping (FR-003):

| Kind | Constructs |
|---|---|
| `function` | free functions; C/C++ functions outside a class; Kotlin and Swift top-level `fun`/`func`; PHP and Ruby top-level functions |
| `method` | methods, constructors, Swift `init`, Rust `impl` functions, Kotlin extension functions, Ruby `def` inside a class or module (including `def self.x`) |
| `class` | classes, records, Kotlin `object`, Ruby modules |
| `interface` | interfaces, Swift protocols, Rust and PHP traits |
| `type` | structs, enums, unions, type aliases, typedefs, C++ `enum class` |

- **Not separate definitions**: bodiless declarations (C/C++ prototypes, abstract and interface members), properties,
  fields and constants. They stay in their type's chunk, as Go interface methods and Python attributes do.
- **Templates and generics**: a template is named after what it declares (`maxof`).

**Rationale**: no schema change to the kind check, the `--kind` choices, or any result. Go already calls structs `type`.

## R6. Imports and their resolution

**Decision**: extraction stores each import as today's `Import(module, rel_level, bound)`. Resolution lives in
`graph._imports`, beside the existing Python, Go and JavaScript rules.

| Language | Extracted | Resolved to | Outside when |
|---|---|---|---|
| typescript, tsx | `import ... from "./x"`, `require("./x")`, `export ... from "./x"` (relative only, as JS) | `./x` + `.ts`, `.tsx`, `.d.ts`, `/index.ts`, `/index.tsx`, then the JS suffixes; `./x.js` also tries `./x.ts` | never: non-relative imports aren't stored, as for JS |
| c, cpp | `#include "p"` stored as `p`; `#include <p>` stored as `<p>` | `"p"`: the including file's folder + `p`, then any file whose path ends with `/p` or is `p` | `<p>`, or a `"p"` that matches nothing |
| java, kotlin | `import a.b.C`, `import a.b.*`, `import static a.b.C.m` | files ending `a/b/C.java` or `a/b/C.kt`; a wildcard (or a Kotlin function import that names no file) goes to files in a folder ending `a/b` | no file and no folder matches: recorded as `a.b` |
| rust | `mod x;` (without a body), `use crate::a::b::...`, `use self::`/`super::` | `mod x;`: `x.rs` or `x/mod.rs` beside a `mod.rs`, `lib.rs` or `main.rs`, else in a folder named after the file. `use`: the longest module path that names a file (`a/b.rs`, `a/b/mod.rs`, then `a.rs`) | `use std::...` or any other crate: recorded as its first segment |
| php | `require`/`include`(`_once`) with a literal or `__DIR__ . '/x'` path; `use A\B\C;` | a path relative to the file; `use`: longest suffix `A/B/C.php`, then `B/C.php`, then `C.php` (PSR-4) | nothing matches |
| ruby | `require_relative "x"`, `require "a/b"` | `x.rb` beside the file; `require`: a file ending `a/b.rb` | `require` of no file (a gem) |
| swift | `import M` | — | always (FR-014) |
| csharp | `using N;`, `using static N.T;`, `global using N;` | every file whose declared namespaces include `N` (`ccctx_files.namespaces`) | no file declares `N` |

- **C# needs declared namespaces**: a C# file says which namespaces it declares (block or file-scoped), and only
  that tells where `using N` points. `parse()` returns them, ingest stores them in `ccctx_files.namespaces`, and the
  graph reads them with the file list. Folder-name guessing was rejected: C# allows any folder layout, and FR-013
  asks for the declaring files.
- **`bound`**: set only for imports that bind a module object, where rule 2 of call resolution
  (`module.function()`) applies: TypeScript namespace and default imports, as for JS, and Rust `use crate::a::b`
  binding `b`. Java, Kotlin, C# and PHP imports bind types, so `Money.of()` resolves as a method call through
  `by_method`; binding `Money` as a module would send it to rule 2 and look for a function `of`.

**Alternatives considered**: build-system include paths (CMake, `tsconfig` paths, Maven source sets). Out of scope by
the spec's Assumptions. Path suffix matching covers the common layouts.

## R7. Calls

**Decision**: one extractor per language returns today's `Call(caller, name, form, receiver, line)`:

| Language | Bare call | Call on a receiver | Constructor |
|---|---|---|---|
| typescript, tsx | `call_expression` with an identifier | `member_expression` (`object`, `property`) | `new_expression` |
| csharp | `invocation_expression` with an identifier | `member_access_expression` (`expression`, `name`) | `object_creation_expression` (`type`) |
| c, cpp | `call_expression` with an identifier | `field_expression` (`argument`, `field`), `qualified_identifier` (`scope`, `name`) | — |
| java | `method_invocation` without `object` | `method_invocation` (`object`, `name`) | `object_creation_expression` (`type`) |
| kotlin | `call_expression` with a `simple_identifier` | `call_expression` over a `navigation_expression` | a call to a capitalized name is bare, and resolves to a class |
| rust | `call_expression` with an identifier | `field_expression` (`value`, `field`), `scoped_identifier` (`path`, `name`) | `Type::new(...)` is a scoped call |
| php | `function_call_expression` | `member_call_expression` (`object`, `name`), `scoped_call_expression` (`scope`, `name`) | `object_creation_expression` |
| ruby | `call` without a receiver, with arguments or parentheses | `call` (`receiver`, `method`) | `X.new` is a call of `new` on `X` |
| swift | `call_expression` with a `simple_identifier` | `call_expression` over a `navigation_expression` | `Circle(r:)` is bare, and resolves to a type |

- **Receivers are normalized**: `::` and `->` become `.`, and a leading `$` is dropped (PHP `$this`), so the
  existing dotted-receiver rule applies.
- **`self`-style receivers**: `SELF` gains `this` (already there), `self` (already there), `$this` (normalized to
  `this`), `Self`, and C# `base`.
- **What is not a call**: a bare Ruby identifier with no arguments could be a local variable, so it isn't one. Macro
  calls (Rust `println!`, C preprocessor macros) are not calls either.
- **Comments and strings** are never walked as calls (FR-010), as today.
- **Implicit receivers** (found while implementing US1): in C#, Java, Kotlin, Swift, C++ and Ruby a bare call inside a
  type, such as `GetWebDriver()`, is a call of that type's own method. For those languages (`graph.IMPLICIT_SELF`), a
  bare call first looks for `<enclosing type>.<name>` among the methods, then falls back to the bare-call kinds. Python,
  Go, JavaScript, TypeScript, Rust and PHP need an explicit `self`/`this`, so their bare calls are unchanged.

**Rationale**: the graph's four resolution rules and `BARE_KINDS` (function, class, type) already cover constructor
calls that resolve to classes and structs.

## R8. Documentation

**Decision**: each language's doc reader returns raw text for the existing `_clean` (first paragraph, at most 1000
characters):
- **`///`** (C#, Rust, Swift, C/C++ Doxygen): the comment run just above the definition.
  - C# XML: the text inside `<summary>`; `<see cref="X"/>` becomes `X`; other tags are dropped.
- **`/** ... */`** (Javadoc, KDoc, TSDoc, PHPDoc, Doxygen): the block comment just above. Lines starting with an
  `@` tag end the description.
- **Ruby**: the run of `#` comments just above `def`, `class` or `module`.
- **Rust**: outer doc comments are `line_comment` nodes carrying an `outer_doc_comment_marker`.
- **File docs**: Rust `//!` lines at the top; a leading `/** */` or `/* */` block in C and C++ that isn't a license
  header (one starting with "Copyright" or "SPDX" is skipped); a PHP file docblock before the first declaration.
  TypeScript, like JavaScript, has no file doc.

Doc comments stay out of the chunk, as for Go and JavaScript today, because they sit above the definition node. FR-005
was reworded to match.

## R9. Visibility (`exported`)

**Decision**: `Chunk.exported` is set by the walker. It is stored in `ccctx_symbols.exported` and read by the wiki's
key-symbol ranking instead of today's name rule.

| Language | Exported when |
|---|---|
| python, javascript | the last name part doesn't start with `_` (today's rule, unchanged) |
| go | the last name part starts with an upper-case letter (today's rule) |
| csharp, java, php | an explicit `public` modifier (PHP methods without a modifier are public) |
| kotlin, swift | not `private`, `internal` or `fileprivate` |
| rust | `pub` (any form, such as `pub(crate)`) |
| typescript, tsx | top level: under `export`; class members: not `private` and not a `#name` |
| c, cpp | not `static`; in a class, under a `public:` section (`struct` members default to public) |
| ruby | not after a bare `private` or `protected` in the same class body, and not named by `private :x` |

- **Backfill**: migration 10 sets `exported` for existing symbols by today's name rule, keyed by file language. Flask
  and gin pages rank exactly as before (SC-005), and they are re-read only when their content changes.
- **Moved symbols**: `_keep_unchanged` updates `exported`, like `doc`, because Ruby's `private` line sits outside the
  method's source.

## R10. Re-reading files whose language gained rules

**Decision**:
- **Lock**: `_lock` returns each stored file's language along with its hash.
- **Candidates**: a file is a candidate when its stored language differs from `detect_language` now. Every newly
  supported extension was stored as `text`, so exactly those files are re-read.
- **Read set**: for these files, the read condition becomes `stale or hash differs or language differs`.
- **Counts**: they count as changed files.
- **Summary**: `Summary.reparsed` counts them by new language, and the CLI prints a `Reparsed` line (contracts/cli.md).
- **`EXTRACT_VERSION` stays 3**: a bump re-reads every file of every repository, and Python, Go and JavaScript rules
  don't change (FR-017). A future change to an existing language's rules still bumps it, as today.

**What happens to the old windows**: `_keep_unchanged` deletes the file's windows and inserts its definitions, which
the hybrid index embeds at commit. Memory and feedback see removed code (US3 scenario 3) through their existing
rules, with no new code.

## R11. Wiki

**Decision**:
- **`LANGUAGE_NAMES`**: TypeScript, TSX, C#, C, C++, Java, Kotlin, Rust, PHP, Ruby, Swift.
- **"package"**: the word stays for Go and Python only. Rust crates and modules are directories in the page's wording.
- **`_is_test` patterns** (tests rank last among key symbols):
  - TypeScript: `*.test.ts(x)`, `*.spec.ts(x)`
  - C#: `*Test.cs`, `*Tests.cs`
  - Java and Kotlin: `*Test.java` and `*Tests.java`, `*Test.kt` and `*Tests.kt`
  - Rust: files under `tests/`
  - Ruby: `*_test.rb`, `*_spec.rb`
  - PHP: `*Test.php`
  - Swift: `*Tests.swift`
  - C and C++: `test_*.c(pp)`, `*_test.c(pp)`
- **Directory pages**: built by the existing rules, now counting files of every language with rules (`GRAMMARS`).
- **Page wording**: unchanged, except the language name.

## R12. Testing

**Decision**:
- **`tests/test_languages.py`**: for each language, an inline source with the acceptance scenarios' constructs. It
  asserts the definitions (name, kind, lines), docs, calls (caller, name, form, receiver) and imports. One parse-failure
  case per language checks the window fallback.
- **Fixture repository** in `test_ingest.py`: one small file set per language, in a throwaway `t-` git repository. It
  asserts that ingest gives no fallback files, `find_callers` across files, resolved imports and outside imports, and a
  wiki page for one folder per language.
- **US3**:
  - A repository ingested before migration 10's rules is simulated by storing a `.cs` file as `text` windows, then
    ingesting with no change: exactly that file is re-read, and `Summary.reparsed == {"csharp": 1}`.
  - Flask and gin symbol, edge and import counts are captured before the change, then asserted equal afterwards
    (SC-005). Their pages' text must also be unchanged.
- **Live checks** (quickstart): Selenium-E2E (SC-002) and the timing of a full flask and gin ingest (SC-006).

## R13. Attributes and annotations in the chunk

**Decision**:
- **Included already**: when a grammar puts attributes inside the declaration node, the chunk includes them with no
  extra work. That covers C# `attribute_list`, Java and Kotlin annotations in `modifiers`, PHP `attribute_list`, Swift
  attributes in `modifiers`, and TypeScript decorators on class members.
- **Siblings above the definition** extend the chunk's start line, as a Python `decorated_definition` does: Rust
  `attribute_item`s, and TypeScript decorators before an `export`ed class.

## R14. Known limits (documented, not fixed)

- **Kotlin one-line bodies**: the grammar fails on some one-line class bodies (R1). Such files fall back to windows,
  flagged.
- **C/C++ preprocessor**: `#ifdef` branches are all parsed as written. A file whose branches don't parse as one
  program falls back. Macros are not expanded.
- **Resolution by name only**: overloads, templates and generics resolve by name, as today.
- **Swift**: files have no file-level dependencies.
- **Ruby**: classes reopened across files are several definitions of one name.
