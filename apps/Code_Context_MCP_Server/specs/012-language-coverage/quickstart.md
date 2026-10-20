# Quickstart: Language Coverage

Validates the feature end to end against the local database, with flask, gin and Selenium-E2E registered.
- **Fixture checks** (SC-001, SC-003, SC-004) run in the test suite.
- **Live checks** below cover the real C# repository (SC-002), the unchanged samples (SC-005) and timing (SC-006).

## Setup

```powershell
uv sync                              # installs the ten grammar packages
uv run ccctx db migrate              # applies migration 10 (language coverage)
```

## 1. Before: record the samples (SC-005)

Run this before upgrading, on `master`:

```powershell
uv run ccctx stats --by-language > before-stats.txt
uv run ccctx eval --gold gold.json   # recall@10: 0.90 (18/20)
```

## 2. Existing indexes convert (US3, SC-007)

```powershell
uv run ccctx ingest selenium-e2e     # incremental: Reparsed  N files ... (N csharp), plus any TypeScript or C++
uv run ccctx ingest selenium-e2e     # right after: already up to date
uv run ccctx ingest flask            # already up to date: no file of a new language
uv run ccctx ingest gin
uv run ccctx stats --by-language > after-stats.txt
```

**Expect**:
- **Selenium-E2E**: its first ingest prints a `Reparsed` line. Its `.cs` files become `csharp`, its `.js` files are
  unchanged, and its windows are gone except for files that don't parse.
- **flask and gin**: identical rows in `before-stats.txt` and `after-stats.txt`.

## 3. C# by name (US1, SC-002)

```powershell
uv run ccctx stats --by-language --repo selenium-e2e        # csharp files and symbols, few or no csharp chunks
uv run ccctx symbols --repo selenium-e2e --kind class --limit 50
uv run ccctx search "how is the browser driver created" --repo selenium-e2e
uv run ccctx callers GetWebDriver --repo selenium-e2e
uv run ccctx impact DriverFixture.GetWebDriver --repo selenium-e2e
uv run ccctx wiki build --repo selenium-e2e
uv run ccctx wiki list --repo selenium-e2e
uv run ccctx wiki show EATestFramework/Driver --repo selenium-e2e
```

**Expect**:
- **Parsed files**: at least 44 of the 46 C# files (95%) are indexed as definitions.
- **Classes by name**: `get_symbol` (or `ccctx symbols`) shows 5 hand-picked classes: `DriverFixture`,
  `BrowserDriver`, `ProductController`, `ProductRepository`, `TestSettings`.
- **Callers**: for 3 hand-picked methods, every caller a `git grep` finds, outside comments and strings, is listed.
- **Wiki**: pages exist for the folders with at least 10 definitions (the wiki's threshold). `EATestFramework/Driver`
  is expected to reach it, at about 11. Its page says it is a C# directory. It names its key types and lists the folders
  whose files `using EATestFramework.Driver;` reaches.

## 4. Through MCP

In the MCP Inspector (`npx @modelcontextprotocol/inspector ccctx mcp`) or Claude Code:
1. `get_symbol` with `{"name": "DriverFixture.GetWebDriver", "repo": "selenium-e2e"}` returns its source.
2. `find_callers` with `{"name": "GetWebDriver", "repo": "selenium-e2e"}` lists its callers.
3. `search_code` with `{"query": "selenium grid", "language": "csharp"}` returns only C# hits.
4. `search_code` with `{"query": "x", "language": "cobol"}` answers `unavailable` and lists the new values.

## 5. Regression and timing (SC-005, SC-006)

```powershell
uv run ccctx eval --gold gold.json   # still recall@10: 0.90 (18/20)
uv run pytest
```

The full suite passes, including `test_eval.py` (identifier top-1 10/10) and the per-language fixture tests.

For timing, compare `--full` ingests of flask and gin on `master` and on this branch. On this branch they take at most
10% longer:

```powershell
Measure-Command { uv run ccctx ingest flask --full; uv run ccctx ingest gin --full }
```

## Verified 2026-10-13

Against the local database, with flask, gin and Selenium-E2E, server 1.4.0.

**1 and 5. flask and gin unchanged (SC-005, SC-006).** Discovery and parsing ran on both versions over the same
363 inputs (361 files plus the two repositories' fallback counts): `master` code (1.3.0, from a git worktree) and
this branch.
- **Identical output**: every file's language, doc, chunks (name, kind, lines, source hash, doc), calls and imports
  are the same, before and after the trailing-newline fix below.
- **Same time**: parsing took 0.52 to 0.56 s per run on `master` and 0.47 to 0.56 s on the branch, over three runs
  each. Embedding is the rest of an ingest's time and is unchanged per symbol, so a `--full` ingest takes the same
  time too.
- **Ordinary ingests**: `ccctx ingest flask` and `ccctx ingest gin` are `already up to date`, since neither has a file
  of a new language.

**Evaluation**: `recall@10: 0.95 (19/20)`, up from 0.90 on 2026-10-12.
- **The change**: "how is HTTP basic authentication checked?" now hits, with `BasicAuthForRealm` (auth.go) at rank
  8. The remaining miss is "how do tests send requests to the app without running a server?".
- **Not from this feature's code**: gin's parse output is identical to `master`'s, and gin has no feedback.
- **Likely cause**: the hybrid index's keyword scores changed (the top hit went from 82.14 to 79.69). Oracle Text
  weighs terms across the whole index, and this session added Selenium-E2E's documents. `test_eval.py`'s floor
  (18/20) holds.

**2. Existing indexes convert (US3, SC-007).**
- **Before the upgrade**: registered `selenium-e2e` and ingested it with the `master` code. 116 files fell back
  (116 no grammar); its 46 `.cs` files were among the 88 `text` files.
- **One ordinary ingest on the branch**:

```text
Changed    46 files (0 added, 46 changed, 0 removed)
Unchanged  83 files
Skipped     0 files
Indexed   161 symbols in 16.7s
Reparsed   46 files whose language is now understood (46 csharp)
Fallback    2 files as line windows (0 no grammar, 2 parse errors)
```

- **Right after it**: `selenium-e2e is already up to date at ba4074640a4a`.

**Found and fixed: a directive on the last line.** The two fallbacks were the NSwag-generated `ProductAPI.cs` clients
(616 lines). Each ends with `#pragma warning restore 3016` and no final newline, and C# rules reject a directive without
its line end (so would C/C++ rules for a final `#endif`). `chunker.parse` now gives the grammar a final newline when the
file lacks one. Lines and chunk text are unchanged, because chunks are cut from the original lines, and flask's and
gin's output is still identical. `test_a_directive_on_the_last_line_without_a_newline_parses` covers C# and C++.
- **Applying it to the dev index**: my pre-fix ingest had already stored those two files as `csharp`. They were reset
  to `text`, as they are on any index built before the upgrade, and an ordinary ingest gave `Reparsed  2 files ...
  (2 csharp)` and 50 more symbols.
- **Result**: `stats --by-language` shows `csharp  46 files  211 symbols  0 chunks`, so 100% of the C# files are
  definitions.

**3. C# by name (US1, SC-002).**
- **Classes**: `get_symbol` gives each hand-picked class with its full source: `DriverFixture` (11-69),
  `BrowserDriver` (9-22), `ProductController` (two, in EAWebApp and ProductAPI), `ProductRepository` (18-69) and
  `TestSettings` (6-13).
- **Callers against `git grep`**, outside comments, strings and declarations:

| Method | `git grep` call sites | `ccctx callers` |
|---|---|---|
| `GetWebDriver` | DriverFixture.cs:22 | `DriverFixture.DriverFixture` at 22 |
| `GetAllProducts` | ProductController.cs:33 (the other line is the interface member) | `ProductController.GetProducts` at 33 |
| `ClearAndEnterText` (an extension method) | 9: ProductPage.cs in EATestBDD (24-26, 45-47) and EATestProject (27-29) | the same 9, in `EnterProductDetails` and `EditProduct` |

- **Wiki**: `ccctx wiki build --repo selenium-e2e` compiled 9 pages (`selenium-e2e: 9 pages (9 added, 0 updated, 0
  removed) in 2.4s`).
  - `EATestFramework/Driver` (11 definitions) reads: "`EATestFramework/Driver` is a C# directory of 4 files and 11
    definitions: 6 methods, 2 classes, 2 interfaces and 1 type."
  - It depends on `EATestFramework/Settings` (through `using`), with the `OpenQA.Selenium.*` and `WebDriverManager`
    namespaces outside the index.

**4. Through MCP**, in one stdio session against `ccctx mcp`:

```text
get_symbol: ok DriverFixture.GetWebDriver method EATestFramework/Driver/DriverFixture.cs 35-43 'private IWebDriver GetWebDriver()'
find_callers: ok [('DriverFixture.DriverFixture', 'EATestFramework/Driver/DriverFixture.cs', 22)]
search_code csharp: ok [('selenium-e2e', 'csharp', 'DriverFixture.DriverFixture'), ('selenium-e2e', 'csharp', 'DriverFixture'), ...]
search_code cobol: unavailable unknown language 'cobol'; valid languages: batch, c, cpp, csharp, css, go, html, ini, java, javascript, json, kotlin, markdown, php, proto, python, rst, ruby, rust, shell, sql, swift, text, toml, tsx, typescript, yaml
read_wiki: ok csharp `EATestFramework/Driver` is a C# directory of 4 files and 11 definitions: 6 meth...
```

**Other things found while implementing**:
- **Implicit receivers**: C#, Java, Kotlin, Swift, C++ and Ruby call their own methods without `this.`, so a bare
  call there first looks for the enclosing type's method (research R7, `graph.IMPLICIT_SELF`).
- **Comment node types**: Java, Kotlin and Rust grammars name their comment nodes `block_comment` and
  `line_comment`, so their doc readers accept those types.
- **Ruby docs**: Ruby attaches a class's leading `#` comments to the enclosing module, so its docs are read from the
  source lines above.
- **A Swift fixture change**: the grammar misparses `square(r) * self.scale()`, taking the product as the callee of
  the second call, so that fixture line was rewritten.
