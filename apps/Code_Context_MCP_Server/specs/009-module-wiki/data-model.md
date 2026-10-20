# Data Model: Module Wiki

One migration (7, "module wiki") adds the doc columns, the two wiki tables and `ccctx_repos.wiki_at`. The page search index is built outside the migration, because it needs the loaded model (research R8). In memory, the chunker gains docs, ingestion gains a wiki summary, and search hits gain a `page` kind. The `wiki` module and the `read_wiki` tool add their own read results.

## Relationships

```text
Repository (ccctx_repos)                     + wiki_at: set by the first `wiki build`
  1 ──< File (ccctx_files)                   + doc: the file's own documentation
  │       1 ──< Symbol (ccctx_symbols)       + doc: the definition's documentation
  │
  1 ──< Wiki page (ccctx_wiki_pages)         one per qualifying directory, on delete cascade
          1 ──< Citation (ccctx_wiki_citations)   on delete cascade
                  ──> 0..1 Symbol   symbol_id, on delete set null   (roles key, calls)
                  ──> 0..1 File     file_id,   on delete set null   (roles file, depends, uses)

Page index (CCCTX_WIKI_HYBRID_IX) over ccctx_wiki_pages.search_text, same model and lexer as the symbol index
Search hit ──> one Symbol, or one Wiki page (kind 'page')
```

A citation is the only place a page's evidence lives. Its path and line range are always read through `symbol_id` or `file_id`, never stored (FR-005, R6). Removing a repository removes its pages and their citations (cascade). Removing a file or a symbol nulls the citations that point at it, which is what marks the page stale (R7).

## Repository (`ccctx_repos`, one column added)

| Column | Type | Rule |
|---|---|---|
| `wiki_at` | `timestamp with time zone`, null | **New.** When `wiki build` first ran for this repository. Null means the repository has no wiki: ingestion neither marks nor recompiles anything for it (FR-010, US3-5). Never cleared by ingestion. |
| `extract_version` | `number` (existing) | `ingest.EXTRACT_VERSION` moves 1 -> 2. A repository stored at 1 is re-read once, keeping every unchanged symbol, so the docs are backfilled without re-embedding (R2). |

## File (`ccctx_files`, one column added)

| Column | Type | Rule |
|---|---|---|
| `doc` | `varchar2(1000 char)`, null | **New.** The file's documentation: the Python module docstring, or the Go comment run ending just above `package` (skipping `//go:build`, not attaching a header separated by a blank line). None for JavaScript and line-window files. Stored as the first paragraph, comment markers removed, whitespace collapsed, at most 1000 characters. Written on file insert and update. |

## Symbol (`ccctx_symbols`, one column added)

| Column | Type | Rule |
|---|---|---|
| `doc` | `varchar2(1000 char)`, null | **New.** The definition's documentation: the Python body's leading string, the Go `//` run ending on the line above, or the JavaScript `/** */` just above. Same cleaning and limit as `ccctx_files.doc`. Always null for `kind = 'chunk'`. `_keep_unchanged` also updates it on kept symbols, because a Go doc comment can change while the symbol's source does not. |

`commit_sha` and `content_hash` (existing) are what a citation records and is compared against.

## Wiki page (`ccctx_wiki_pages`, new)

One per directory of a wiki-enabled repository whose own files hold at least 10 symbols of kind other than `chunk` (FR-001). Subdirectories count separately.

| Column | Type | Rule |
|---|---|---|
| `id` | `number` identity, primary key | |
| `repo_id` | `number` not null, references `ccctx_repos (id)` on delete cascade | |
| `directory` | `varchar2(1024)` not null | The directory's path relative to the repository root, `.` for the root. Unique with `repo_id`. |
| `name` | `varchar2(1024)` not null | The directory with one leading `src/` removed; the repository name for `.`. If two qualifying directories of one repository would share a name (`src/x` and `x`), both use their full directory. Unique with `repo_id` (R1). |
| `language` | `varchar2(32)` not null | The most common `ccctx_files.language` among the page's symbols, ties broken by name. Used by the `--language` filter (FR-014). |
| `symbols` | `number` not null | The count of named definitions directly in the directory. `>= 10` (`ccctx_wiki_pages_symbols_ck`). |
| `text` | `clob` not null | The page's Markdown (R3): heading, structural sentence and purpose, Key symbols, Depends on, Used by. At most 8000 characters. Contains no file path and no line number (FR-005, see Validation). |
| `search_text` | `clob` not null | `page <name> in <directory>\n<text>`. The column the page index embeds. Rewritten only when `text` changes, so an unchanged page is not re-embedded (R11). |
| `state` | `varchar2(8)` not null | `fresh` or `stale` (`ccctx_wiki_pages_state_ck`). See State transitions. |
| `compiled_at` | `timestamp with time zone` not null | When the current `text` was compiled. Moves on every build or recompile. |
| `compiler` | `varchar2(64)` not null | Who compiled it: the wiki compiler and its version, `wiki.COMPILER`, `ccctx-wiki/<n>` (for example `ccctx-wiki/1`). Bumped when the page rules change (FR-006, constitution V). |
| `stale_reason` | `varchar2(512)`, null | What last made the page stale, `<name> changed (<old commit 12> -> <new commit 12>)`, `<name> was re-indexed` or `<name> is gone`, for example `jsonify changed (5f2c1a9e04b7 -> 9e0d3b71c2aa)`. Set when the page goes stale, and kept after a recompile so `wiki list` can show what triggered it (FR-007). Null for a page that was never stale. |

Constraints: `ccctx_wiki_pages_dir_uk unique (repo_id, directory)`, `ccctx_wiki_pages_name_uk unique (repo_id, name)`. The same name may exist in two repositories; commands then require `--repo` and refuse the ambiguous name with the repositories that have it.

## Citation (`ccctx_wiki_citations`, new)

One row per record a page names (FR-005). Outside packages on the "Outside the index" line have no record and are not cited.

| Column | Type | Rule |
|---|---|---|
| `id` | `number` identity, primary key | |
| `page_id` | `number` not null, references `ccctx_wiki_pages (id)` on delete cascade | |
| `symbol_id` | `number`, references `ccctx_symbols (id)` on delete set null | Set for roles `key` and `calls`. Null once the symbol is gone. |
| `file_id` | `number`, references `ccctx_files (id)` on delete set null | Set for roles `file`, `depends` and `uses`. Null once the file is gone. |
| `role` | `varchar2(8)` not null | `key` (a key symbol), `file` (one of the directory's own files), `depends` (an imported file in another directory), `uses` (an importing file in another directory), `calls` (a named symbol of a depended-on module). |
| `name` | `varchar2(1024)` not null | The cited symbol's qualified name, or the cited file's path, at compile time. Kept only to describe a citation whose record is gone; never used to locate anything. |
| `kind` | `varchar2(16)` not null | The symbol's kind, or `file`. |
| `commit_sha` | `varchar2(64)` not null | The record's commit at compile time: the symbol's `commit_sha`, or the repository's `indexed_commit` for a file. Same hex check as `ccctx_symbols.commit_sha`. |
| `content_hash` | `varchar2(64)` not null | The record's `content_hash` at compile time (FR-006). |

Constraints and indexes:
- `ccctx_wiki_citations_role_ck`: `role in ('key','calls','file','depends','uses')`.
- `ccctx_wiki_citations_target_ck`: `(role in ('key','calls') and file_id is null) or (role in ('file','depends','uses') and symbol_id is null)`. It still holds after a set-null, which leaves both keys null.
- Indexes on `page_id`, `symbol_id` and `file_id`, so a set-null on delete and the stale check do not scan the table.
- At most one row per `(page_id, role, record)`, enforced by the compiler, which replaces a page's citations as a whole.

## Page index (`CCCTX_WIKI_HYBRID_IX`, new)

A hybrid vector index over `ccctx_wiki_pages.search_text`, with the same model, lexer and `SYNC (ON COMMIT)` as the symbol index. Created by `ccctx model load` beside the symbol index, or by `wiki build` when the model is loaded and the index is missing. `require_model` does not require it: without it, search returns symbols only and the wiki still builds, lists and shows.

## Validation rules

| Rule | Source |
|---|---|
| A directory qualifies only with `>= 10` named definitions (`kind <> 'chunk'`) in its own files. Line windows never count and are never cited. | FR-001, edge cases |
| Key symbols: at most 10; up to 4 types (`class`, `interface`, `type`) first, then the rest; each ordered by call edges (`ccctx_calls` + `ccctx_file_calls`) from files outside the directory, then all callers, then name. Every key symbol is a named definition of that directory. | FR-004, R4 |
| Depends on and Used by come from `ccctx_imports` grouped by the other file's directory, named by the page-name rule. Outside packages come from `graph.external_imports` and are listed by name only. | FR-002, R5 |
| `text` holds no path and no line number: any sentence containing a file name with an indexed extension or `line <n>` is dropped, Sphinx roles are reduced to their last name, directive lines and RST underlines are removed. | FR-005, R3 |
| Every backticked name in `text` is a cited symbol, a module named through `file`/`depends`/`uses` citations, or an entry on the "Outside the index" line. Every key symbol and every `calls` name has a citation. | US2-3 |
| Nothing in `text` is stated beyond the index: the structural sentence is computed, the purpose is quoted documentation, or "Its code has no documentation; the sections below come from its structure." | FR-003, edge cases |
| A sentence is at most 300 characters, a doc at most 1000, a page at most 8000. | R2, R3 |
| Two builds with no change in between give the same `text`, `search_text` and citation set; only `compiled_at` moves. | US1-4, R11 |

## State transitions

```text
                 wiki build / refresh (directory qualifies)
   (no page) ───────────────────────────────────────────────▶ fresh
       ▲                                                        │  mark_stale, in the ingest transaction:
       │ directory no longer qualifies,                         │  a symbol citation's symbol_id is null or its
       │ or the repository is removed                           │  commit_sha differs from the symbol's, or a
       │                                                        ▼  file citation's file_id is null
       └──────────────────────────────────────────────────── stale
                                                          │   ▲
                         refresh after commit succeeds ───┘   └─── refresh fails: stays stale, committed
                         (recompiled -> fresh, stale_reason kept)    (ingestion still succeeds, FR-012)
```

- **Marking** (`wiki.mark_stale(cur, repo_id)`): runs only for repositories with `wiki_at` set, inside the ingest transaction after `_write` and the graph rebuild, so no reader sees new code beside a page called fresh. Only `fresh` pages are marked; `stale_reason` names the first offending citation. A file citation goes stale only when its file is removed, not when its content changes. An ingestion that changes nothing marks nothing.
- **Recompiling** (`wiki.refresh(conn, repo_id)`): after `conn.commit()`, in its own transaction. Recompiles every stale page, compiles pages for newly qualifying directories, deletes pages for directories that no longer qualify. On failure the transaction rolls back and the pages stay stale.
- **Full re-ingestion**: deleting the files nulls every citation, so every page goes stale and is recompiled.
- **Repository** `wiki_at`: null -> set on the first `wiki build`; unchanged afterwards.

## In-memory shapes

| Shape | Change |
|---|---|
| `chunker.Chunk` | **New field** `doc: str \| None = None`. |
| `chunker.parse` | Returns a 4th element, the file doc (`str \| None`). |
| `graph.external_imports(cur, repo_id) -> dict[int, set[str]]` | **New.** Per file id, the import refs that resolve to no indexed file: the first dotted component for Python, the full path for Go, never a relative import. Shares one resolution loop with `rebuild`. |
| `wiki.Refresh` | **New.** `stale: list[tuple[str, str]]` (page name, reason), `recompiled: int`, `added: int`, `removed: int`, `error: str \| None`. |
| `ingest.Summary` | **New field** `wiki: Refresh \| None`, None when the repository has no wiki. The CLI prints one line per stale page, then the counts (FR-011). |
| `semantic.Result` | `kind` gains `page`. For a page hit: `name` is the page name, `path` the directory, `language` the page's language, `snippet` the first 10 lines of `text`, `start_line` and `end_line` are None (widened to `int \| None`). **New field** `state: str \| None`: the page's `fresh` or `stale`, None for symbol hits (FR-012). `score`, `keyword_rank` and `semantic_rank` are its values within the page index; `similarity` places it above the first non-definition hit with a lower similarity (R8). |
| `wiki.Page` (read) | name, repo, directory, language, state, compiled_at, compiler, stale_reason, symbols, text, `citations[]` (at most 200), `truncated`. |
| `wiki.CitationView` (read) | name, kind, role, repo, path, start_line, end_line (current, read through the key; None when the record is gone), `recorded_commit`, `current_commit` (None when gone). |
| `server.WikiResults` | `status`, `reason`, `page: Page \| None` (None when listing), `pages[]` (at most 200: name, repo, state, summary = first purpose sentence). Unknown page, ambiguous name and unknown repository return `unavailable` with a reason (FR-016). |
