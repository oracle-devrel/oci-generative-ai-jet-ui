# Feature Specification: Language Coverage

**Feature Branch**: `012-language-coverage`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "I want the project to cover other programming languages too, like TypeScript, C++, C#
and so on."

## Clarifications

### Session 2026-10-13

- Q: Which languages should this feature add, beyond Python, Go and JavaScript? → A: The broad set: TypeScript
  (including TSX), C#, C, C++, Java, Kotlin, Rust, PHP, Ruby and Swift.
- Q: How deep should each new language be supported? → A: Full parity with Python: named definitions, doc comments,
  calls and file dependencies. Dependencies are best effort where a language imports namespaces or modules rather than
  files.

## Context

Today three languages are understood: Python, Go and JavaScript. Their files are split into named definitions
(functions, methods, classes, types), with their documentation, the calls they make and the files they import. Every
other file, a C# or TypeScript file included, is cut into unnamed 60-line windows. Such a file can still be found by
search, but nothing in it can be read by name, followed through calls, or described on a wiki page. A C# test-automation
repository indexed this way (130 files, 46 of them C#) gave search hits like `DriverFixture.cs:1-60` and nothing for
`get_symbol`, `find_callers` or `impact_of`.

This feature brings ten more languages to the same level.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - C# code is understood by name (Priority: P1)

A developer indexes a C# solution (a web application, its API, and its test projects). They search for "how is the
browser driver created", read a class by name, ask who calls a method, and ask what a change to it would affect, as
they already can for Python. The wiki has a page for each C# project folder, naming its key classes and the folders it
depends on.

**Why this priority**: C# is the language of the repository the user is indexing now, and it gets the least today: all
of its code is unnamed windows.

**Independent Test**: Ingest a C# repository. `ccctx symbols --repo <it>` lists its classes, interfaces, records,
structs, enums, methods and constructors by qualified name (`DriverFixture.GetWebDriver`). `get_symbol` returns a
named class's full source. `find_callers` on a method lists the methods that call it, with lines. `read_wiki` shows a
page for a project folder that names its key types.

**Acceptance Scenarios**:

1. **Given** a C# file declaring a namespace, block-scoped (`namespace N { }`) or file-scoped (`namespace N;`), with
   a class, its constructor, methods and properties, **When** the repository is ingested, **Then** the class and each
   method and constructor are definitions named after their enclosing types (`DriverFixture`,
   `DriverFixture.GetWebDriver`), and the namespace is not part of the name.
2. **Given** a method called from two other methods, one with `obj.Method()` and one through a `new Class().Method()`
   chain, **When** a client asks who calls it, **Then** both callers are listed with the lines of their calls, and a
   mention of the method's name in a comment or a string is not.
3. **Given** a method with an XML doc comment (`/// <summary>Starts the browser.</summary>`), **When** the wiki page of
   its folder is compiled, **Then** the page describes the method with that sentence, without the markup.
4. **Given** two files, one with `using EATestFramework.Driver;` and one declaring `namespace EATestFramework.Driver`,
   **When** the wiki page of the first file's folder is compiled, **Then** it lists the second file's folder under the
   modules it depends on.
5. **Given** a class split across two files with `partial`, **When** a client reads it by name, **Then** both parts are
   returned, each with its own path and lines.

---

### User Story 2 - TypeScript, C and C++ code is understood by name (Priority: P1)

A developer indexes a TypeScript front end and a C++ library. Searching, reading by name, following calls, and the
wiki work for both as they do for JavaScript and Python today.

**Why this priority**: TypeScript and C++ are the other two languages the user named. C comes with C++, because C++
projects include C headers, and C++ rules read most C.

**Independent Test**: Ingest a fixture with TypeScript (`.ts` and `.tsx`), C (`.c`, `.h`) and C++ (`.cpp`, `.hpp`, `.cc`,
`.h`). Each file's functions, classes, interfaces, type aliases, enums, structs and methods are listed by qualified
name, and calls and imports are recorded.

**Acceptance Scenarios**:

1. **Given** a TypeScript file exporting an interface, a type alias, an enum, a class with methods, a function, and an
   arrow function bound to a constant, **When** it is ingested, **Then** each is a definition of the matching kind, and
   the methods are named `Class.method`.
2. **Given** a TSX component file, **When** it is ingested, **Then** its component functions are definitions, and its
   markup does not stop the file from being understood.
3. **Given** a TypeScript file importing `./api/client`, **When** dependencies are resolved, **Then** it depends on
   `api/client.ts` (or `.tsx`, or `api/client/index.ts`), as JavaScript imports resolve today.
4. **Given** a C++ header declaring `class Engine` with a method, and a source file defining `void Engine::start() {
   ... }` inside a namespace, **When** they are ingested, **Then** `Engine` is a definition in the header and
   `Engine.start` a definition in the source file, and the namespace is not part of either name.
5. **Given** a C++ source file with `#include "engine.h"`, **When** dependencies are resolved, **Then** it depends on
   the `engine.h` it names, found relative to the including file first, then anywhere in the repository. `#include
   <vector>` is recorded as an outside dependency.
6. **Given** a C function `parse_config` called from two functions, **When** a client asks for its callers, **Then**
   both are listed.

---

### User Story 3 - Existing indexes pick up the new languages (Priority: P1)

An operator upgrades the server. The repositories they already indexed, flask, gin and the C# one, are not re-indexed
from scratch. The next ordinary ingest turns each newly understood file from line windows into definitions, and leaves
everything else as it was.

**Why this priority**: Without it, every newly supported file stays as windows until its content changes, and the
operator gets nothing from the upgrade.

**Independent Test**: With a repository ingested before the upgrade (its C# files indexed as windows), run `ccctx ingest
<repo>` without `--full`. Its C# files become definitions. Its unchanged files of the old languages are not parsed
again, and their definitions, memory facts and feedback are unchanged.

**Acceptance Scenarios**:

1. **Given** a repository indexed before the upgrade, with its newly supported files stored as windows, **When** it is
   ingested again with no file changed, **Then** exactly those files are re-indexed as definitions, and the summary
   says how many files changed language support.
2. **Given** flask and gin indexed before the upgrade, **When** they are ingested again, **Then** their symbol counts,
   search results and retrieval evaluation are exactly as before.
3. **Given** facts and usage feedback recorded about a newly supported file's windows, **When** the file becomes
   definitions, **Then** facts about removed windows go stale as for any removed code, and feedback on the windows
   boosts nothing, as for any result that is gone.

---

### User Story 4 - Java, Kotlin and Rust code is understood by name (Priority: P2)

A developer indexes a Java service, a Kotlin Android module and a Rust crate, and uses search, reading by name, calls
and the wiki on them.

**Why this priority**: These are widely used compiled languages with clear file and module structure, so their
dependencies resolve well. They were not named by the user.

**Independent Test**: Ingest a fixture with Java, Kotlin and Rust files. Classes, interfaces, records, enums, objects,
traits, structs, functions and methods are listed by qualified name. Calls and dependencies are recorded.

**Acceptance Scenarios**:

1. **Given** a Java file `com/acme/Order.java` with `import com.acme.util.Money;` and a file `com/acme/util/Money.java`
   under the same source root, **When** dependencies are resolved, **Then** `Order.java` depends on `Money.java`.
2. **Given** a Kotlin file with a class, a companion object, an `object`, top-level functions and an extension
   function `fun String.slug()`, **When** it is ingested, **Then** each is a definition. The companion object's
   functions are named after its class (`Order.create`), and the extension function is the method `String.slug`.
3. **Given** a Rust file with a struct, a trait, `impl Shape for Circle { fn area(&self) ... }` and `mod geometry;`,
   **When** it is ingested, **Then** `Circle.area` is a method definition, and the file depends on `geometry.rs` or
   `geometry/mod.rs`.

---

### User Story 5 - PHP, Ruby and Swift code is understood by name (Priority: P3)

A developer indexes a PHP web application, a Ruby gem and a Swift package, and uses search, reading by name, calls and
the wiki on them.

**Why this priority**: Requested as part of the broad set. Their imports are the loosest (PHP namespaces and include
paths, Ruby load paths, Swift modules with no file imports), so they deliver the least dependency information.

**Independent Test**: Ingest a fixture with PHP, Ruby and Swift files. Classes, interfaces, traits, modules, protocols,
structs, enums, extensions, functions and methods are listed by qualified name, and calls are recorded.

**Acceptance Scenarios**:

1. **Given** a PHP file with `require_once __DIR__ . '/lib/db.php';` and a class in a namespace, **When** it is
   ingested, **Then** the class and its methods are definitions without the namespace in their names, and the file
   depends on `lib/db.php`.
2. **Given** a Ruby file with `require_relative "parser"` and `module Acme; class Parser; def parse ... end; end; end`,
   **When** it is ingested, **Then** `Acme`, `Acme.Parser` and `Acme.Parser.parse` are definitions, and the file
   depends on `parser.rb` beside it.
3. **Given** a Swift file with a struct, a protocol, and an `extension Circle { func area() ... }`, **When** it is
   ingested, **Then** `Circle.area` is a method definition. Swift has no file imports, so the file's dependencies come
   only from what it calls.

---

### Edge Cases

- **A file that does not parse** (a syntax error, or newer syntax than the language rules know) is indexed as line
  windows and flagged as a parse failure, as today. The ingest summary counts it.
- **`.h` files** belong to C and C++ alike. They are read with C++ rules, which read most C. A header that only C reads
  correctly falls back to windows like any file that does not parse.
- **Same name, several definitions**: overloads in one file, `partial` classes, Ruby classes reopened in several files,
  Swift and Kotlin extensions in other files. Each is its own definition with its own lines; reading by name returns
  all of them, as for any repeated name today.
- **Declarations without bodies** (C and C++ prototypes, abstract methods, interface and protocol members) are part of
  their enclosing type's source, not separate definitions. A function is indexed where its body is.
- **Properties, fields and constants** are part of their type's source, not separate definitions, as Python class
  attributes are today. A property or accessor with a body is no exception; its calls count as calls from its type.
- **Nested types**: a nested class is named after every enclosing type (`Outer.Inner.method`). Namespaces, packages
  and modules that only group code (C# and C++ namespaces, Java and Kotlin packages, PHP namespaces) are left out of
  names, as Go packages are today. Ruby modules and Kotlin objects hold code of their own and are definitions.
- **Generated and bundled code**: a minified or bundled file is handled by the existing size limit and vendored-folder
  settings. Nothing about it is language-specific.
- **A repository mixing languages** gets each file read by its own language's rules. A wiki page about a folder of
  several languages is labeled with the language most of its definitions are in, as today.
- **An import that names no file in the repository** (a system header, a NuGet or Maven package, a gem, a crate) is
  recorded as an outside dependency, as Python and Go imports of outside packages are today.
- **Ambiguous resolution**: a C# `using` names a namespace declared in several folders, or an `#include "util.h"`
  matches several files. The dependency goes to every match in the repository. A miss is never guessed.

## Requirements *(mandatory)*

### Functional Requirements

#### Recognizing languages

- **FR-001**: Files MUST be assigned these languages by extension: TypeScript (`.ts`, `.mts`, `.cts`), TSX (`.tsx`),
  C# (`.cs`), C (`.c`), C++ (`.cpp`, `.cc`, `.cxx`, `.c++`, `.hpp`, `.hh`, `.hxx`, `.h`), Java (`.java`), Kotlin
  (`.kt`, `.kts`), Rust (`.rs`), PHP (`.php`), Ruby (`.rb`, `.rake`, and files named `Rakefile` or `Gemfile`) and
  Swift (`.swift`). Languages already recognized keep their extensions.
- **FR-002**: Search's language filter (CLI and MCP) MUST accept every new language, and list them among its valid
  values.

#### Definitions

- **FR-003**: For each new language, a file that parses MUST be indexed as named definitions at syntactic boundaries,
  with the existing kinds: `function` for free functions; `method` for methods, constructors and functions inside a
  type, object or module; `class` for classes, records, objects and modules (Ruby). A companion object is not a
  definition of its own: its members are named after its class; `interface` for
  interfaces, protocols and traits; `type` for structs, enums, unions, type aliases and typedefs.
- **FR-004**: A definition's name MUST be qualified by its enclosing types, joined with dots (`Engine.start`,
  `Outer.Inner.run`), never by namespaces or packages. A member defined outside its type MUST be named after the type
  it belongs to: C++ `Engine::start` (after the last qualifier, since a namespace and a class cannot be told apart by
  syntax), Rust `impl` blocks, Swift `extension` blocks, Kotlin extension functions (`fun String.slug()` is the method
  `String.slug`), and C# `partial` parts.
- **FR-005**: A definition's chunk MUST include its attributes or annotations directly above it, as Python
  decorators are today, and MUST carry its line range. Its documentation comment is read into its documentation
  (FR-007) and, as for Go and JavaScript today, is not part of the chunk.
- **FR-006**: A file that does not parse MUST fall back to line windows, flagged as a fallback, and counted as a parse
  error in the ingest summary (constitution II).

#### Documentation

- **FR-007**: Each definition's documentation MUST be read from its language's doc comment form and reduced to its
  first paragraph without markup, as for the existing languages:
  - **`///` and `/** */` comments**: C# XML (only the text inside `<summary>` and similar tags), Javadoc and KDoc,
    JSDoc and TSDoc, Doxygen for C and C++, Rust `///` and `//!`, Swift `///`, PHPDoc.
  - **Ruby**: the `#` comment block above a definition.
- **FR-008**: A file's own documentation MUST be read where the language has one: a leading file or module doc comment
  (Rust `//!`, a leading block comment in C and C++, a PHP file docblock). Wiki pages use it as for Python and Go.

#### Calls

- **FR-009**: For each new language, calls MUST be recorded with the calling definition, the called name, its form (a
  bare call or a call on a receiver) and its line. This includes constructor calls (`new Order(...)`, Kotlin and Swift
  `Order(...)`, Rust `Order::new(...)`), method calls on a receiver, and calls through a type or module (`Math.max`,
  `Vec::new`, `Foo::bar`).
- **FR-010**: Text in comments and strings MUST NOT count as calls, as today.
- **FR-011**: Calls MUST resolve to definitions by the existing rules, so `find_callers`, `find_callees` and `impact_of`
  work across files and across languages in one repository.

#### Dependencies

- **FR-012**: Imports MUST be recorded and resolved to files of the same repository wherever the language names a
  file or a path that maps to one:
  - **TypeScript**: relative imports and `require`, as JavaScript, also trying `.ts`, `.tsx`, `.d.ts` and an `index`
    file.
  - **C and C++**: `#include "..."`, relative to the including file first, then by path anywhere in the repository.
  - **Java and Kotlin**: `import a.b.C` to `a/b/C.java` or `a/b/C.kt` under any folder of the repository. A wildcard
    import goes to the folder's files.
  - **Rust**: `mod x;` to `x.rs` or `x/mod.rs`; `use crate::a::b` to the file of module `a::b`.
  - **PHP**: `require`, `include` and their `_once` forms with a literal or `__DIR__`-relative path.
  - **Ruby**: `require_relative`, and `require` of a path that exists under the repository.
- **FR-013**: Namespace imports MUST resolve best effort: a C# `using N;` depends on every file of the repository that
  declares namespace `N`, and a PHP `use A\B\C;` on the file at `A/B/C.php` by the PSR-4 convention, matched by the longest path suffix
  that names a file (`A/B/C.php`, then `B/C.php`, then `C.php`).
- **FR-014**: An import that resolves to no file of the repository MUST be recorded as an outside dependency by its
  module or package name. Swift imports are modules and always count as outside.

#### Wiki

- **FR-015**: Wiki pages MUST be compiled for folders of the new languages by the existing rules. Each language's
  name MUST be shown in plain words ("a C# directory"). "Exported" MUST follow each language's notion of public when
  key symbols are ranked:
  - an explicit `public` (C#, Java, PHP)
  - not `private` or `internal` (Kotlin, Swift)
  - `pub` (Rust)
  - `export` (TypeScript)
  - not `static`, in headers (C and C++)
  - not under `private` (Ruby)

#### Re-indexing existing repositories

- **FR-016**: After the upgrade, the next ingest of a repository MUST re-index every file whose language gained support
  (or whose rules changed), even if its content did not change, and only those among the unchanged files. The ingest
  summary MUST report how many files that was.
- **FR-017**: Files of Python, Go and JavaScript MUST be indexed exactly as before: the same definitions, names, kinds,
  lines, documentation, calls and dependencies.

#### Interfaces

- **FR-018**: No MCP tool and no CLI command MUST change shape. The new languages appear only as new values in the
  existing `language` fields and filters, and as new definitions in existing results. Tool descriptions that list
  languages MUST be updated.
- **FR-019**: Every new language MUST be read on the server, with no network access while parsing, no third-party
  service, and nothing sent off the machine (constitution I).

### Key Entities

- **Language**: a name (for example `csharp`) with its file extensions, its rules for definitions, documentation,
  calls and imports, and its notion of public. A language either has rules (its files become definitions) or does not
  (its files become windows).
- **Indexed language**: the language each file was indexed under. The ingest compares it with the language the file
  is assigned now, to find unchanged files whose language gained rules (FR-016). A change to an existing language's
  rules re-reads every file, as today.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For each of the ten new languages, a fixture repository that uses that language's common constructs
  (listed in the acceptance scenarios) is indexed with 100% of the fixture's expected definitions present, under the
  expected qualified names and kinds, and no file of it falls back to windows.
- **SC-002**: In the user's C# repository (Selenium-E2E, 46 C# files), at least 95% of the C# files are indexed as
  definitions rather than windows. `get_symbol` returns the full source for 5 of its classes named by hand.
  `find_callers` on 3 of its methods named by hand lists every caller a reader finds with a text search, excluding
  comments and strings.
- **SC-003**: In each fixture, `find_callers` on each function or method that the fixture calls lists 100% of its
  direct call sites, and lists nothing from comments or strings.
- **SC-004**: In each fixture whose language resolves imports to files (all but Swift), 100% of the fixture's
  in-repository imports resolve to the expected files, and every outside import is recorded as outside.
- **SC-005**: For flask and gin, symbol counts, call edges and dependencies are identical before and after the
  upgrade. The retrieval evaluation stays at recall@10 0.90 (18/20) on the gold set, and identifier top-1 at 10/10.
- **SC-006**: Ingesting flask and gin from scratch takes at most 10% longer than before.
- **SC-007**: After the upgrade, one ordinary ingest of Selenium-E2E converts its C# files to definitions without
  `--full`. A second ingest right after it re-indexes nothing.

## Assumptions

- **Parsers**: grammars for all ten languages exist as installable packages that run locally, like the existing three.
  No language needs a compiler, a build, or the project's dependencies to be read.
- **Precision**: names, calls and imports come from syntax alone, as today. Overload resolution, type inference, macro
  expansion, C/C++ preprocessor conditionals, and build-system include paths are out of scope. A call resolves by name
  through the existing rules, and an `#include` is found by path within the repository only.
- **Kinds**: the existing kinds cover the new constructs (FR-003), so the stored kinds, the `--kind` filter and every
  result shape stay as they are. Struct and enum are `type`, as Go's structs are today.
- **Namespaces**: Go packages are not part of definition names today, and neither are the new languages' namespaces
  and packages. Two classes of the same name in different namespaces are two definitions of that name, told apart by
  path, as two Go functions of the same name in different packages are today.
- **`.h` files**: read as C++, the language most projects with headers use. A repository of pure C loses nothing that
  C++ rules read.
- **Fixtures**: each language is tested with a small fixture repository in the test suite. The C# repository
  Selenium-E2E is the one real-world check, and is the user's own, not a cloned sample. No new sample repository is
  cloned.
- **Priority order**: US1 (C#), then US2 (TypeScript, C, C++), and US3 (existing indexes) are the first delivery. US4
  (Java, Kotlin, Rust) and US5 (PHP, Ruby, Swift) follow, each usable on its own.
- **Embedding**: definitions of the new languages are embedded and searched like any other. The embedding model is
  unchanged.
