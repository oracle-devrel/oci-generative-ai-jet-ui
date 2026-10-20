# Tasks: Language Coverage

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Data model**: [data-model.md](./data-model.md) | **Contracts**: [cli.md](./contracts/cli.md), [tools.md](./contracts/tools.md) | **Live checks**: [quickstart.md](./quickstart.md)

**Tests come first**: constitution VI requires every test task to be written before the code it covers, and to fail
first. Database tests run against the local database, like the existing suites:
- **Fixture repositories**: `tests/test_ingest.py` and `tests/test_wiki.py` show the pattern, with `t-` names.
- **Parser cases**: `tests/test_chunker.py` shows the pattern.

**One rule shapes the order**: a language's extensions are added in the same task as its rules, never earlier.
- **Why**: if `.kt` mapped to `kotlin` before Kotlin had rules, its files would be stored as `kotlin` windows, and the
  re-read rule (research R10) would never convert them once the rules arrived.
- **Consequence**: each story adds its own extensions, and the server's language list is checked against the contract
  only at the end (Phase 8).

**Shared files**: `languages.py`, `graph.py` and `wiki.py` grow in every story, so stories run one after another.
Within a story, `[P]` marks tasks that touch different files.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1 to US5, from spec.md

## Path Conventions

Single package: `src/golestan_code_mcp/`, tests in `tests/`, per-language fixture files under
`tests/fixtures/languages/<language>/`. Every path below is from the repository root.

---

## Phase 1: Setup

**Purpose**: dependencies and version.

- [X] T001 Add the ten grammar packages to `dependencies` in pyproject.toml, with the versions and bounds of research R1:
  `tree-sitter-typescript>=0.23,<0.24`, `tree-sitter-c-sharp>=0.23,<0.24`, `tree-sitter-c>=0.24,<0.25`,
  `tree-sitter-cpp>=0.23,<0.24`, `tree-sitter-java>=0.23,<0.24`, `tree-sitter-kotlin>=1.1,<2`,
  `tree-sitter-rust>=0.24,<0.25`, `tree-sitter-php>=0.25,<0.26`, `tree-sitter-ruby>=0.23,<0.24` and
  `tree-sitter-swift>=0.7,<0.8`. Keep `tree-sitter>=0.25,<0.26`. Set the version to `1.4.0` in pyproject.toml and in
  src/golestan_code_mcp/__init__.py. Run `uv sync`, stopping every MCP client first (the `ccctx.exe` lock). Files:
  pyproject.toml, src/golestan_code_mcp/__init__.py, uv.lock

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the storage, chunker shape and plumbing every language uses, with Python, Go and JavaScript unchanged.

- [X] T002 [P] Write failing tests in tests/test_schema.py:
  - Migration 10 "language coverage" adds `ccctx_files.namespaces` (JSON, nullable) and `ccctx_symbols.exported`
    (BOOLEAN, nullable).
  - The backfill sets `exported` by the name rule: a Go name starting upper-case is exported; a Python name whose
    last part starts with `_` is not. It leaves windows null and touches only null rows.
  - The migration is re-runnable.
  - `schema.version(conn) == 10`.
- [X] T003 [P] Write failing tests in tests/test_chunker.py:
  - **The new shape**: `parse()` returns five items, the last being `namespaces` (an empty list for Python, Go and
    JavaScript).
  - **`exported`**: every Python, Go and JavaScript chunk carries it by today's rule (research R9). Windows carry None.
  - **Unchanged**: the existing cases still give the same names, kinds, lines, docs, calls and imports.
  - **Lazy loading**: importing `golestan_code_mcp.chunker`, `golestan_code_mcp.ingest` or `golestan_code_mcp.server`
    in a fresh interpreter loads no `tree_sitter_*` module beyond python, go and javascript. Check `sys.modules` from
    a subprocess, as test_memory's package check does.
- [X] T004 Add migration 10 "language coverage" to src/golestan_code_mcp/schema.py, as in data-model.md:
  - two `alter table ... add` statements, tolerating ORA-01430
  - the backfill `update`
  - Make T002 pass, and keep test_schema's version assertion at 10.

  File: src/golestan_code_mcp/schema.py
- [X] T005 Reshape src/golestan_code_mcp/chunker.py, then make T003 pass:
  - **`Chunk.exported`**: add `bool | None = None`.
  - **`GRAMMARS`**: language to `(module, function)`. Import lazily through a cached `_language(language)`; the three
    existing grammars keep their top-level imports and entries.
  - **Tables**: add `NAMES`, `FILE_DOCS` (Python and Go entries replacing `_file_doc`'s if-chain, with the same
    behavior) and `NAMESPACES`.
  - **Walkers**: yield `(name, kind, node, exported)`; `_python`, `_go` and `_javascript` compute `exported` by
    today's name rule.
  - **`CALLS`**: accept a callable for new languages, beside today's table form.
  - **`parse()`**: return `(chunks, calls, imports, doc, namespaces)`.
  - **`languages.py`**: merge its tables. Create src/golestan_code_mcp/languages.py with a module docstring and empty
    `EXTENSIONS`, `NAMES`, `GRAMMARS`, `WALKERS`, `CALLS`, `IMPORTS`, `SYMBOL_DOCS`, `FILE_DOCS` and `NAMESPACES`
    dicts that chunker merges.

  Files: src/golestan_code_mcp/chunker.py, src/golestan_code_mcp/languages.py
- [X] T006 [P] Write failing tests in tests/test_ingest.py: after ingesting a fixture repository with Python, Go and
  JavaScript files, every non-chunk symbol has `exported` set by its rule, windows have null, and every file's
  `namespaces` is null. A second `--full` ingest gives identical symbol, ref and edge rows (names, kinds, lines, docs,
  callers, imports).
- [X] T007 Update src/golestan_code_mcp/ingest.py for the new `parse()` shape, then make T006 pass:
  - **`_prepare`**: unpacks five items; windows get `[]` namespaces.
  - **`_write`**: stores `namespaces` (JSON, null when empty) on the file row and `exported` on each symbol row.
  - **`_keep_unchanged`**: updates `exported` with `doc`.

  File: src/golestan_code_mcp/ingest.py
- [X] T008 [P] Write failing tests in tests/test_graph.py, for the resolution helpers:
  - **Path suffixes**: `_suffix_index(paths)` maps every path suffix (`a/b/C.java`, `b/C.java`, `C.java`) to its files.
  - **Self receivers**: `SELF` includes `Self` and `base`.
  - **Receivers**: a receiver written with `::`, `->` or a leading `$` resolves like its dotted form
    (`_normalize("$this")` is `this`; `_normalize("Foo::bar")` is `Foo.bar`).
  - **`_files`**: returns `(path, language, namespaces)`.

  Existing graph tests stay green.
- [X] T009 Add the helpers T008 names to src/golestan_code_mcp/graph.py: `_files` with namespaces, `_suffix_index`,
  `_normalize` (applied to stored receivers before rules 2 to 4), and the extended `SELF`. Make T008 pass.
  File: src/golestan_code_mcp/graph.py
- [X] T010 [P] Write failing tests in tests/test_wiki.py:
  - Key symbols rank by the stored `exported` flag: a fixture symbol whose flag is set false by SQL ranks below an
    exported one with the same callers.
  - Existing Python and Go pages compile to exactly the same text as before.
- [X] T011 Change src/golestan_code_mcp/wiki.py, then make T010 pass:
  - The symbol query reads `s.exported`.
  - `rank` uses it, with today's name rule when it is null.
  - `_is_test` and `LANGUAGE_NAMES` are ready to take the new entries: add them per story.

  File: src/golestan_code_mcp/wiki.py

**Checkpoint**: `ccctx db migrate` applies migration 10. The full existing suite passes, and flask and gin ingest
exactly as before.

---

## Phase 3: User Story 1 - C# code is understood by name (Priority: P1) 🎯 MVP

**Goal**: C# files are definitions with names, kinds, docs, calls, `using` dependencies and visibility, and C# folders
get wiki pages.

**Independent Test**: ingest the C# fixture repository.
- `ccctx symbols` lists its classes, interfaces, records, structs, enums, methods and constructors by qualified name.
- `get_symbol` returns a class's source.
- `find_callers` lists a method's callers.
- `read_wiki` shows a page for the fixture's main folder that names its key types and the folder it `using`s.

### Tests for User Story 1

- [X] T012 [P] [US1] Write the C# fixture files under tests/fixtures/languages/csharp/, at least 10 definitions in its
  main folder:
  - **Two projects**: `App/Driver/` declares `namespace App.Driver;` file-scoped; `App/Steps/` uses block-scoped
    `namespace App.Steps { }` with `using App.Driver;` and `using System;`.
  - **Constructs**: a `partial` class split across two files, a nested class, a record, a struct, an enum and an
    interface with a bodiless member.
  - **Members**: a constructor, methods called with `obj.M()`, `this.M()`, `new T().M()` and a bare call, and a
    property with an expression body.
  - **Comments**: a method whose name appears only in a comment and a string, an `[Attribute]` on a method, and
    `/// <summary>` docs with a `<see cref="X"/>`.
  - **A file that doesn't parse**.
- [X] T013 [P] [US1] Write failing tests in tests/test_languages.py (new) for C# (`chunker.parse("csharp", ...)` on the
  fixture files):
  - **Definitions**: the expected names and kinds (research R4, R5). There is no namespace in names; constructors
    are `T.T`; the nested class is `Outer.Inner`; properties and bodiless interface members are not definitions.
  - **Attributes**: the attribute line is inside the method's chunk.
  - **`exported`**: True exactly for `public` members.
  - **Docs**: the summary's text with `X` for `<see cref="X"/>`.
  - **Calls**: the expected `(caller, name, form, receiver)` rows, with `this` and `new T()` forms. None from the
    comment or the string.
  - **Imports**: `using App.Driver;` and `using System;`.
  - **Namespaces**: `["App.Driver"]` and `["App.Steps"]`.
  - **Detection**: `detect_language("x.cs") == "csharp"`.
  - **Fallback**: the broken file returns None.
- [X] T014 [P] [US1] Write failing tests in tests/test_graph.py and tests/test_wiki.py against the C# fixture ingested
  as a `t-` repository:
  - **Callers**: `callers` of a method called from the other project lists both callers with lines.
  - **Imports**: `App/Steps` files import `App/Driver` files, through declared namespaces. `System` is an outside
    import (`external_imports`).
  - **Wiki**: the page for `App/Driver` says "a C# directory", lists its public types among the key symbols, and is
    listed as a dependency of `App/Steps`.
  - **Ingest summary**: no fallback except the broken file.

### Implementation for User Story 1

- [X] T015 [US1] Add C# to src/golestan_code_mcp/languages.py, then make T013 pass:
  - **Mapping**: `.cs` to `csharp`, with grammar `tree_sitter_c_sharp.language`.
  - **Walker**: through `compilation_unit`, `namespace_declaration`, `file_scoped_namespace_declaration` and
    `declaration_list`.
  - **Calls**: `invocation_expression`, `member_access_expression` and `object_creation_expression`.
  - **Imports**: `using_directive`, including the static and global forms.
  - **Docs**: `///` XML.
  - **Namespaces**: the declared ones.
  - **`exported`**: an explicit `public`.

  File: src/golestan_code_mcp/languages.py
- [X] T016 [US1] Resolve C# `using` in src/golestan_code_mcp/graph.py by a namespace-to-files index built from
  `_files` (research R6). Unresolved names are outside imports. Make T014's graph cases pass. File:
  src/golestan_code_mcp/graph.py
- [X] T017 [US1] Add `csharp` to `LANGUAGE_NAMES` ("C#") and the C# test patterns (`*Test.cs`, `*Tests.cs`) to
  `_is_test` in src/golestan_code_mcp/wiki.py. Make T014's wiki cases pass. File: src/golestan_code_mcp/wiki.py

**Checkpoint**: the C# fixture behaves as US1's acceptance scenarios say, through the CLI and MCP.

---

## Phase 4: User Story 3 - Existing indexes pick up the new languages (Priority: P1)

**Goal**: the next ordinary ingest re-reads exactly the unchanged files whose language gained rules, and reports them.

**Independent Test**: store a `.cs` file as `text` windows (as before the upgrade), then ingest with no change. Exactly
that file is re-read, the summary prints `Reparsed  1 files whose language is now understood (1 csharp)`, and the other
files' rows are untouched.

### Tests for User Story 3

- [X] T018 [P] [US3] Write failing tests in tests/test_ingest.py:
  - **The re-read**: ingest a fixture with Python files and one `.cs` file. Set that file's language to `text` and
    replace its symbols with windows, as before the upgrade. Ingest again with no change: only it is re-read,
    `Summary.reparsed == Counter(csharp=1)`, and the Python files' symbols keep their ids. A second ingest is `current`.
  - **The log record**: it carries `reparsed`.
  - **Full ingests** report no `reparsed`.
  - **Memory and feedback**: a fact and a use recorded on the old window. After the re-read, the fact is stale, and
    `feedback.listing` shows the window's use as not indexed.
- [X] T019 [P] [US3] Write failing tests in tests/test_cli.py: the incremental summary prints the `Reparsed` line after
  `Indexed`, with languages by count then name (contracts/cli.md), and omits it when there are none.

### Implementation for User Story 3

- [X] T020 [US3] Implement the re-read rule in src/golestan_code_mcp/ingest.py (research R10), then make T018 pass:
  - **`_lock`**: returns `{path: (hash, language)}`.
  - **Candidates**: add the stored files whose language differs from `chunker.detect_language`.
  - **The read condition**: `stale or hash differs or language differs`.
  - **`Summary.reparsed`** and its log field.

  File: src/golestan_code_mcp/ingest.py
- [X] T021 [US3] Print the `Reparsed` line in `_format_incremental` in src/golestan_code_mcp/cli.py. Make T019 pass.
  File: src/golestan_code_mcp/cli.py

**Checkpoint**: quickstart step 2 holds against the real Selenium-E2E index.

---

## Phase 5: User Story 2 - TypeScript, C and C++ code is understood by name (Priority: P1)

**Goal**: TypeScript, TSX, C and C++ files are definitions with names, kinds, docs, calls, dependencies and visibility.

**Independent Test**: ingest the TypeScript, C and C++ fixture repository.
- Each file's functions, classes, interfaces, type aliases, enums, structs and methods are listed by qualified name.
- `find_callers` works across files.
- Relative imports and `#include "..."` resolve; `#include <...>` is outside.

### Tests for User Story 2

- [X] T022 [P] [US2] Write fixture files under tests/fixtures/languages/typescript/, tsx/, c/ and cpp/:
  - **TypeScript**: an exported interface, a type alias, an enum, a class with methods, a function, and an arrow
    function bound to a `const`. A `/** */` doc. `import { get } from "./api/client"` with `api/client.ts`, and
    `api/index.ts` imported as `./api`. A `private` method.
  - **TSX**: a component calling a helper.
  - **C**: `config.h` with a prototype and a struct; `parse.c` defining `parse_config`, called from two functions, with
    `#include "config.h"` and `#include <stdio.h>`. A `static` helper and a typedef.
  - **C++**: `engine.h` with `class Engine` and a public/private section; `engine.cpp` defining
    `void app::Engine::start()` inside `namespace app`, with `#include "engine.h"`. A template function and an `enum
    class`.
  - **One file per language that doesn't parse.**
- [X] T023 [P] [US2] Write failing tests in tests/test_languages.py for typescript, tsx, c and cpp:
  - **Definitions and kinds**: `Engine.start` is defined in engine.cpp, no namespace is in any name, and prototypes are
    not definitions.
  - **`exported`**: `export`; TypeScript not `private`; C not `static`; a C++ `public:` section.
  - **Docs**: JSDoc and TSDoc stop at the `@` tag; C and C++ use `///` and `/** */`.
  - **Calls**: bare, member, `this.`, `new`, `->` and `::` forms.
  - **Imports**: the C/C++ angled include stored as `<stdio.h>`.
  - **Detection**: `.h` is `cpp` and `.tsx` is `tsx`.
  - **Fallbacks**: one per language.
- [X] T024 [P] [US2] Write failing tests in tests/test_graph.py and tests/test_wiki.py against the fixture ingested as
  a `t-` repository:
  - **Callers**: `callers parse_config` lists both callers, and `Engine.start`'s callers are listed.
  - **Imports resolve**: TypeScript relative imports to `client.ts` and `api/index.ts`; `parse.c` to `config.h`;
    `engine.cpp` to `engine.h`, relative first, then by suffix.
  - **Outside imports**: `<stdio.h>` is outside.
  - **Wiki**: a page names "a TypeScript directory" or "a C++ directory" when its folder reaches the threshold.

### Implementation for User Story 2

- [X] T025 [US2] Add TypeScript and TSX to src/golestan_code_mcp/languages.py, then make T023's typescript and tsx
  cases pass:
  - **Mappings**: `.ts`, `.mts`, `.cts` to `typescript`; `.tsx` to `tsx` (research R2).
  - **Shared rules**: one walker for both, extending the JavaScript one with interface, type alias, enum and abstract
    class.
  - **Calls**: the JavaScript form.
  - **Imports**: relative, as JavaScript.
  - **Docs**: JSDoc and TSDoc.
  - **`exported`**: `export`, and not `private` or `#`.

  File: src/golestan_code_mcp/languages.py
- [X] T026 [US2] Add C and C++ to src/golestan_code_mcp/languages.py, then make T023's c and cpp cases pass:
  - **Mappings**: the extensions of research R2 (`.h` is `cpp`).
  - **Walkers**: `function_definition` (with qualified declarators named after the last qualifier),
    `class_specifier`, `struct_specifier`, `union_specifier`, `enum_specifier`, `type_definition`, and
    `namespace_definition` passed through.
  - **Calls**: `call_expression` with `field_expression` and `qualified_identifier`.
  - **Imports**: `preproc_include`.
  - **Docs**: Doxygen and file docs (skipping license headers).
  - **`exported`**: not `static`, plus access sections.

  File: src/golestan_code_mcp/languages.py
- [X] T027 [US2] Resolve TypeScript and C/C++ imports in src/golestan_code_mcp/graph.py (research R6):
  - **TypeScript**: the TypeScript suffixes, then the JavaScript ones; `.js` also tries `.ts`.
  - **C and C++**: an include relative to the file, then by `_suffix_index`. Angled includes and misses are outside.

  Make T024's graph cases pass. File: src/golestan_code_mcp/graph.py
- [X] T028 [US2] Add TypeScript, TSX, C and C++ to `LANGUAGE_NAMES` and their test patterns to `_is_test` in
  src/golestan_code_mcp/wiki.py. Make T024's wiki cases pass. File: src/golestan_code_mcp/wiki.py

**Checkpoint**: the fixture behaves as US2's acceptance scenarios say.

---

## Phase 6: User Story 4 - Java, Kotlin and Rust code is understood by name (Priority: P2)

**Goal**: Java, Kotlin and Rust files are definitions with names, kinds, docs, calls, dependencies and visibility.

**Independent Test**: ingest the Java, Kotlin and Rust fixture repository.
- Classes, interfaces, records, enums, objects, traits, structs, functions and methods are listed by qualified name.
- Java and Kotlin imports and Rust `mod`/`use` resolve.

### Tests for User Story 4

- [X] T029 [P] [US4] Write fixture files under tests/fixtures/languages/java/, kotlin/ and rust/:
  - **Java**: `com/acme/Order.java` importing `com.acme.util.Money`, with `com/acme/util/Money.java`. A wildcard import,
    `java.util.*`, a record, an enum, a nested interface, and Javadoc with `@param`.
  - **Kotlin**: a class with a companion object, an `object`, an extension function `fun String.slug()`, top-level
    functions, a data class, an enum class and KDoc. Every body is written over several lines (research R1).
  - **Rust**: `lib.rs` with `mod geometry;` and `geometry.rs` with a struct, a trait,
    `impl Shape for Circle { fn area }`, `impl Circle { pub fn new }`, a `#[derive]` attribute, `///` and `//!` docs,
    and `use crate::geometry::Circle` from another file.
  - **One file per language that doesn't parse**, including a Kotlin one-line body (the known limit).
- [X] T030 [P] [US4] Write failing tests in tests/test_languages.py for java, kotlin and rust:
  - **Names, kinds and `exported`** (research R4, R5, R9): `Order.create` for the companion, `String.slug` a method,
    `Circle.area`, `Circle.new`. Generics are stripped from impl names.
  - **Attributes**: the `#[derive]` line is in the chunk.
  - **Docs**: they stop at `@` tags, and `//!` is the file doc.
  - **Calls**: `Type::new`, `this.`, `self.`, method and bare forms.
  - **Imports**.
  - **Fallbacks**.
- [X] T031 [P] [US4] Write failing tests in tests/test_graph.py and tests/test_wiki.py against the fixture ingested as
  a `t-` repository:
  - **Java and Kotlin imports**: `Order.java` imports `Money.java`; a wildcard goes to the folder's files; `java.util`
    is outside.
  - **Rust imports**: `lib.rs` depends on `geometry.rs`; a `use crate::...` file depends on `geometry.rs`; `std` is
    outside.
  - **Callers** across files.
  - **Wiki**: pages name the languages "Java", "Kotlin" and "Rust".

### Implementation for User Story 4

- [X] T032 [US4] Add Java and Kotlin to src/golestan_code_mcp/languages.py, then make T030's java and kotlin cases
  pass:
  - **Mappings**: `.java` to `java`; `.kt` and `.kts` to `kotlin`.
  - **Walkers**: Java's class, interface, record, enum and annotation type bodies. Kotlin's `class_declaration`
    (`interface` by its keyword), `object_declaration`, transparent `companion_object`, and receiver-typed
    `function_declaration`.
  - **Calls**: `method_invocation` and `object_creation_expression` (Java); `call_expression` over
    `navigation_expression` (Kotlin).
  - **Imports**.
  - **Docs**: Javadoc and KDoc.
  - **`exported`**.

  File: src/golestan_code_mcp/languages.py
- [X] T033 [US4] Add Rust to src/golestan_code_mcp/languages.py, then make T030's rust cases pass:
  - **Mapping**: `.rs` to `rust`.
  - **Walker**: `function_item`, `struct_item`, `enum_item`, `union_item`, `trait_item`, `type_item`, `impl_item`
    (named after its type, generics stripped), and `mod_item` passed through.
  - **Attributes**: preceding `attribute_item`s extend the chunk.
  - **Calls**: `call_expression` with `field_expression` and `scoped_identifier`; macros are not calls.
  - **Imports**: `mod_item` without a body, and `use_declaration`.
  - **Docs**: outer and inner doc comments.
  - **`exported`**: `pub`.

  File: src/golestan_code_mcp/languages.py
- [X] T034 [US4] Resolve Java, Kotlin and Rust imports in src/golestan_code_mcp/graph.py (research R6), and record
  their outside imports. Make T031's graph cases pass. File: src/golestan_code_mcp/graph.py
- [X] T035 [US4] Add Java, Kotlin and Rust to `LANGUAGE_NAMES` and their test patterns to `_is_test` in
  src/golestan_code_mcp/wiki.py. Make T031's wiki cases pass. File: src/golestan_code_mcp/wiki.py

**Checkpoint**: the fixture behaves as US4's acceptance scenarios say.

---

## Phase 7: User Story 5 - PHP, Ruby and Swift code is understood by name (Priority: P3)

**Goal**: PHP, Ruby and Swift files are definitions with names, kinds, docs, calls, dependencies (none for Swift files)
and visibility.

**Independent Test**: ingest the PHP, Ruby and Swift fixture repository.
- Classes, interfaces, traits, modules, protocols, structs, enums, extensions, functions and methods are listed by
  qualified name.
- Calls resolve, and PHP and Ruby requires resolve.

### Tests for User Story 5

- [X] T036 [P] [US5] Write fixture files under tests/fixtures/languages/php/, ruby/ and swift/:
  - **PHP**: a namespaced class with `$this->`, `Helper::` and `new` calls, and
    `require_once __DIR__ . '/lib/db.php'` with `lib/db.php`. `use App\Util\Logger;` with `App/Util/Logger.php`, an
    interface, a trait, a top-level function, a PHPDoc, and a method without a modifier.
  - **Ruby**: `module Acme` holding `class Parser` with `def parse`, `def self.create`, and methods after `private`.
    `require_relative "lexer"` with `lexer.rb`, `require "json"`, and `#` docs. A `Rakefile`.
  - **Swift**: a struct, a protocol, `extension Circle: Shape { func area() }`, a class with `init`, an enum, `///`
    docs, `import Foundation`, and a `private func`.
  - **One file per language that doesn't parse.**
- [X] T037 [P] [US5] Write failing tests in tests/test_languages.py for php, ruby and swift:
  - **Names and kinds**: `Acme`, `Acme.Parser`, `Acme.Parser.parse`, `Acme.Parser.create`, `Circle.area`,
    `Engine.init`. No namespace in PHP names.
  - **`exported`**: PHP without a modifier is public; Ruby `private` sections; Swift `private`.
  - **Docs**.
  - **Calls**: `$this->x()` stored with receiver `this`, `A::b()`, Ruby calls with and without receivers (a bare
    identifier with no arguments is not a call), Swift navigation calls.
  - **Imports**.
  - **Detection**: `Rakefile` is `ruby`.
  - **Fallbacks**.
- [X] T038 [P] [US5] Write failing tests in tests/test_graph.py and tests/test_wiki.py against the fixture ingested as
  a `t-` repository:
  - **PHP imports**: the `require_once` and the PSR-4 `use` resolve.
  - **Ruby imports**: `require_relative` resolves; `json` is outside.
  - **Swift imports**: `Foundation` is outside, and Swift files import no files.
  - **Callers** of `Acme.Parser.parse` and `Circle.area`.
  - **Wiki**: pages name "PHP", "Ruby" and "Swift".

### Implementation for User Story 5

- [X] T039 [US5] Add PHP to src/golestan_code_mcp/languages.py, then make T037's php cases pass:
  - **Mapping**: `.php` to `php`, with grammar `tree_sitter_php.language_php`.
  - **Walker**: `class_declaration`, `interface_declaration`, `trait_declaration`, `enum_declaration`,
    `function_definition` and `method_declaration`; namespaces passed through.
  - **Calls**: `function_call_expression`, `member_call_expression`, `scoped_call_expression` and
    `object_creation_expression`.
  - **Imports**: require and include with a literal or `__DIR__` path, and `namespace_use_declaration`.
  - **Docs**: PHPDoc.
  - **`exported`**: `public`, or no modifier.

  File: src/golestan_code_mcp/languages.py
- [X] T040 [US5] Add Ruby and Swift to src/golestan_code_mcp/languages.py, then make T037's ruby and swift cases pass:
  - **Ruby mapping**: `.rb` and `.rake`, plus `NAMES` `Rakefile` and `Gemfile`.
  - **Ruby walker**: `module`, `class`, `method` and `singleton_method`, with `private` and `protected` sections
    tracked.
  - **Ruby calls**: `call` nodes, and bare identifiers only with arguments.
  - **Ruby imports**: `require_relative` and `require`.
  - **Ruby docs**: `#` comments.
  - **Swift mapping**: `.swift`.
  - **Swift walker**: `class_declaration` covers class, struct, enum and extension by its keyword; also
    `protocol_declaration`, `function_declaration` and `init_declaration`.
  - **Swift calls**: `call_expression` over `navigation_expression`.
  - **Swift imports**: `import_declaration`, always outside.
  - **Swift docs**: `///`.
  - **`exported`** for both.

  File: src/golestan_code_mcp/languages.py
- [X] T041 [US5] Resolve PHP and Ruby imports in src/golestan_code_mcp/graph.py: PHP require paths and the PSR-4
  suffix for `use`; Ruby `require_relative` and the `require` suffix. Record Swift and unresolved imports as outside.
  Make T038's graph cases pass. File: src/golestan_code_mcp/graph.py
- [X] T042 [US5] Add PHP, Ruby and Swift to `LANGUAGE_NAMES` and their test patterns to `_is_test` in
  src/golestan_code_mcp/wiki.py. Make T038's wiki cases pass. File: src/golestan_code_mcp/wiki.py

**Checkpoint**: the fixture behaves as US5's acceptance scenarios say.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T043 Update the language contract checks:
  - **tests/test_server.py**: read `search_code`'s `language` parameter description from
    specs/012-language-coverage/contracts/tools.md instead of 008's. Assert an unknown language's refusal lists the
    new values, and that a C# fixture `search_code` hit matches the core.
  - **tests/test_semantic.py**: its `LANGUAGE_LIST` takes the contract's list.
  - **Server**: `search_code`'s description is built from `semantic.LANGUAGES`, so no code change is needed. Confirm
    the contract text matches it.

  Files: tests/test_server.py, tests/test_semantic.py
- [X] T044 [P] Update README.md:
  - **"Ingesting a codebase"**: the thirteen languages and what each gets.
  - **The `Reparsed` line**.
  - **Naming rules**: namespaces left out, `Engine.start`, `String.slug`, `Acme.Parser.parse`.
  - **Known limits**: Kotlin one-line bodies; no preprocessor, macros or build include paths; Swift file
    dependencies.
  - **"Changed in 1.4.0"**.
  - **The layout**: languages.py.

  File: README.md
- [X] T045 Run the full suite (`uv run pytest`) and ruff (`uvx ruff@0.14.0 check src tests --exclude
  tests/fixtures`), and fix what fails. Files: src/golestan_code_mcp/*.py, tests/*.py
- [X] T046 Walk through specs/012-language-coverage/quickstart.md live, and append a "Verified" section with the
  observed outputs:
  - **Before**: capture flask and gin stats and eval on `master` first (step 1).
  - **SC-002**: the Selenium-E2E conversion and its counts.
  - **SC-005**: flask and gin identical.
  - **SC-006**: timing, with `--full` flask and gin ingests on `master` and on the branch.
  - **Eval**: still 0.90.

  File: specs/012-language-coverage/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: needs Setup, and blocks every story. T002, T003, T006, T008 and T010 are tests,
  written first. Order: T004 after T002; T005 after T003; T007 after T005 and T006; T009 after T008; T011 after T004
  and T010.
- **US1 (Phase 3)**: needs Phase 2.
- **US3 (Phase 4)**: needs a language with rules; US1's C# is the one its test uses. It runs right after US1, so
  every language added later converts existing indexes from the start.
- **US2 (Phase 5)**: needs Phase 2. It shares `languages.py`, `graph.py` and `wiki.py` with US1, so it runs after
  US3.
- **US4 (Phase 6) and US5 (Phase 7)**: need Phase 2, and run after US2 because the files are shared.
- **Polish (Phase 8)**: needs every story. T043 needs the full language list.

### User Story Dependencies

- **US1, US2, US4, US5**: independent in behavior, each adding its languages' rules. They are sequential only
  because they edit the same files.
- **US3**: depends on US1 for a language to convert.

### Within Each User Story

Fixtures, then failing tests, then `languages.py` rules, then graph resolution, then wiki names and test patterns.

### Parallel Opportunities

- **Foundational**: T002, T003, T006, T008 and T010, five test files.
- **Each story**: the fixture task and the test tasks (T012 to T014, T018 and T019, T022 to T024, T029 to T031, T036
  to T038).
- **Polish**: T044 alongside T043 and T045.

## Parallel Example: User Story 1

```text
Task: "T012 [P] [US1] C# fixture files under tests/fixtures/languages/csharp/"
Task: "T013 [P] [US1] C# parser tests in tests/test_languages.py"
Task: "T014 [P] [US1] C# graph and wiki tests in tests/test_graph.py, tests/test_wiki.py"
# then, in order: T015 (languages.py) → T016 (graph.py) → T017 (wiki.py)
```

## Implementation Strategy

### MVP First (User Story 1, then US3)

Do Phases 1 and 2, then US1 and US3. C# is understood, and the user's Selenium-E2E index converts on its next ingest.
That is the most value for the least code: one language, plus the re-read rule.

### Incremental Delivery

1. **Foundation**: migration 10, the chunker shape and the helpers. Flask and gin are unchanged.
2. **US1**: C#.
3. **US3**: existing indexes convert. Run quickstart step 2 on Selenium-E2E.
4. **US2**: TypeScript, TSX, C and C++.
5. **US4**: Java, Kotlin and Rust.
6. **US5**: PHP, Ruby and Swift.
7. **Polish**: the contract language list, README, the suite, and the live walkthrough.

Each story's extensions arrive with its rules, and the re-read rule lands right after the first language. Stopping
after any story from US3 on leaves a consistent index: every file of a language with rules is parsed.

## Notes

- **Unchanged languages** (FR-017): Python, Go and JavaScript rules are unchanged, and `EXTRACT_VERSION` stays 3.
  Their tests must stay green at every checkpoint.
- **A failing grammar** for one construct is a fallback, not a crash: the file becomes windows and is counted (FR-006).
- **Commits**: only when the user asks.
