# Research: Module Wiki

## R1. A page is a directory, named without `src/`

**Decision**: one page per directory whose own files hold at least 10 symbols of kind other than `chunk`. Subdirectories count separately.
- **Name**: the directory's path with one leading `src/` removed. `src/flask/json` becomes `flask/json` and `binding` stays `binding`. The root directory (path `.`) is named after the repository.
- **Clash**: when two qualifying directories of one repository would get the same name (`src/x` and `x`), both use their full path.
- **Unique keys**: `(repo, directory)` and `(repo, name)`.

**Rationale**: the user's example `flask/json` is the directory `src/flask/json`. Dropping `src/` gives the import path a reader expects without guessing per language.

**Alternatives considered**:
- A page per file: `app.py` would get a page and so would its directory, saying the same things twice.
- `<repo>/<last component>`: `tests/templates` and `examples/tutorial/tests` would clash.
- Python import paths (`flask.json`): no Go equivalent without the module path.

At this index the rule gives 7 flask pages and 7 gin pages, the sets named in SC-001.

## R2. Docs are stored at ingestion

The index holds definitions only. A Python module docstring and every Go doc comment sit outside the chunks today, and gin has no Go doc in the index at all. A page compiled "from the index alone" (FR-003) needs them there.

**Decision**: the chunker reads the docs from the same parse.
- **Symbol doc**: `Chunk.doc` (default `None`).
  - Python: the first statement of the body, when it is a string.
  - Go: the run of `//` comments that ends on the line just above the declaration.
  - JavaScript: the `/** */` comment just above it.
- **File doc**: `parse` returns it as a 4th element.
  - Python: the module's first statement, when it is a string.
  - Go: the comment run that ends on the line just above the `package` clause. `//go:build` lines are skipped. A copyright header separated by a blank line is not attached.
  - JavaScript: none (`# simplified: no JS file docs, read a leading block comment when a JS repository needs it`).
- **Stored text**: the first paragraph with comment markers removed, whitespace collapsed and at most 1000 characters. It goes in `ccctx_symbols.doc` and `ccctx_files.doc`.
- **Writes**:
  - `_insert_symbols` and the file insert and update write the docs.
  - `_keep_unchanged` also updates a kept symbol's `doc`, because a Go doc comment can change while the symbol's source does not.
- **`EXTRACT_VERSION` 1 -> 2**: every repository is re-read once. The existing path treats each file as changed and keeps every symbol whose `(name, kind, content_hash)` matches, so nothing is re-embedded.

**Rationale**: docs are the only honest source of "what is this for" without a model. The extraction-version mechanism already gives a cheap, idempotent backfill.

**Alternatives considered**:
- Reading files from the working tree at compile time: they can differ from what was indexed, and staleness would then track the disk instead of the index.
- Widening Go chunks to include their comments: this changes every Go line range and content hash, re-embeds the gin index and changes `get_symbol` output.

## R3. Page text

**Decision**: deterministic Markdown in four sections. Names appear in backticks. No path or line number appears anywhere.

```markdown
# flask/json

`flask/json` is a Python package of 3 files and 62 definitions: 6 classes, 9 functions and 47 methods.
A compact representation for lossless serialization of non-standard JSON types. ...

## Key symbols
- `JSONProvider` (class): A standard set of JSON operations for an application.
- `jsonify` (function): Serialize the given arguments as JSON, and return a Response object with the application/json mimetype.
...

## Depends on
- `flask`: `current_app`, `Response`
- Outside the index: `dataclasses`, `decimal`, `json`, `typing`, `uuid`, `weakref`, `werkzeug`

## Used by
- `flask`, `flask/sansio`, `tests`
```

- **The first sentence** is always structural:
  - "a <Language> package" when a Python `__init__.py` exists, or when the directory is Go;
  - "a <Language> directory" otherwise;
  - then the file count, the definition count, and counts by kind, largest first.
- **Purpose**:
  - the directory's file docs, `__init__.py` or the file named after the directory first, then the rest by path, at most 3 paragraphs;
  - if there are none, the docs of the first 2 key types;
  - if there are none at all, the sentence "Its code has no documentation; the sections below come from its structure."
- **Key symbols**: each line is the doc's first sentence. A symbol with no doc gets "no documentation".
- **Depends on**: one line per depended-on module, named by the R1 rule (as page names). Each line lists up to 5 of the module's symbols this directory calls, from the call edges. The outside packages come last.
- **Used by**: the importing modules, by the same rule.
- **Cleaning**: Sphinx roles are reduced to the last part of their target (``:class:`~flask.sessions.SecureCookieSessionInterface` `` becomes `SecureCookieSessionInterface`). Directive lines (`.. autoclass::`) and RST heading underlines are dropped. Any sentence that would still contain a file name with an indexed extension, or `line <n>`, is dropped. That keeps FR-005 true even when a docstring mentions a file.
- **Limits**: one sentence is at most 300 characters and the page is at most 8000 characters.

**Rationale**: the structural sentence makes even an undocumented page true and searchable. The word "package" or "directory" next to the name is what a question like "what does the json module do" meets on the keyword side.

**Alternatives considered**: free prose templates per language. They are more text to test and still say nothing the facts above do not.

## R4. Key symbols

**Decision**: up to 10 named definitions of the directory.
- **Types first**: up to 4 types (`class`, `interface`, `type`), by usage. Then the rest by usage up to 10.
- **Ranking**:
  1. Code before its tests: a symbol in a test file (`test_*.py`, `*_test.py`, `*_test.go`, `conftest.py`) comes after every other one.
  2. Usage: the count of call edges (`ccctx_calls` plus `ccctx_file_calls`) into the symbol from files outside the directory.
  3. Exported before private (a Go capital, a Python name without a leading underscore), then documented before undocumented.
  4. All callers, then the name.
- **Why exported and documented come before all callers**: found in the live check. Go interfaces are never the target of a call edge, so gin's `binding` listed unexported test types ahead of `Binding`.

**Rationale**: what other modules call is what the module offers, and its types are how a reader holds it in mind.

**Alternatives considered**: the longest symbols, which picks big private helpers; and alphabetical order, which picks noise.

## R5. Dependencies

**Decision**:
- **Inside the index**: `ccctx_imports` rows from this directory's files to files of other directories, grouped by the imported file's directory. Used-by is the same grouping reversed.
- **Outside the index**: a new `graph.external_imports(cur, repo_id) -> dict[file_id, set[str]]`. It runs each stored import ref through the existing resolver and keeps the refs that resolve to no file. The name is the first dotted component for Python and the full import path for Go. Relative Python imports are never external.
- **Refactor**: `_imports` is reshaped so `rebuild` and `external_imports` share one resolution loop, with no copied rules.

**Rationale**: these are the step 6 import edges, and the resolver already decides what is internal.

**Alternatives considered**: deciding "external" from the module text, for example a first component that is not a repository directory. That duplicates the resolver and disagrees with it on `src/` layouts.

## R6. Citations are foreign keys

**Decision**: `ccctx_wiki_citations` has one row per cited record. Each row has:
- `symbol_id` referencing `ccctx_symbols` and `file_id` referencing `ccctx_files`, both `on delete set null`;
- the cited `name`, `kind` and `role`;
- the `commit_sha` and `content_hash` the record had at compile time.

The roles:
- `key`: each key symbol.
- `file`: each of the directory's own files.
- `depends`: each imported file in another directory.
- `uses`: each importing file in another directory.
- `calls`: each named symbol of a depended-on module.

A citation never points at a wrong record. It points at the right one, or at nothing once that record is gone. Locations are always read through the key, never stored.

**Rationale**: `on delete cascade` would silently drop the citation of an edited symbol, because ingestion deletes and reinserts it. That is the rot the user wants caught. Set-null leaves the evidence for staleness.

**Alternatives considered**: storing a symbol's name and path and re-resolving them at read time. That is the prose citation the user rejected, kept in a column.

## R7. Staleness and recompiling

**Decision**:
- **When the wiki exists**: `ccctx_repos.wiki_at` is set by the first `wiki build`. Only repositories with it set are marked or recompiled (US3-5).
- **Marking**: `wiki.mark_stale(cur, repo_id)` runs inside the ingest transaction, after `_write` and the graph rebuild. A fresh page becomes stale when one of its symbol citations has a null `symbol_id`, or a `commit_sha` that differs from the symbol's current one. Its `stale_reason` names the first such citation, `<name> changed (<old commit 12> -> <new commit 12>)` or `<name> is gone`. File citations go stale only when their file is removed (`file_id` null). A file's content changing does not count: its symbols carry that. A rewritten symbol (ingestion deletes an edited one and inserts it again) is matched by its name: `changed` with its new commit, or `was re-indexed` when the commit is the same, as after a full re-ingestion.
- **Recompiling**: after `conn.commit()`, `wiki.refresh(conn, repo_id)` runs in its own transaction.
  - It recompiles every stale page.
  - It compiles pages for directories that now qualify and deletes pages for directories that no longer do.
  - It returns `Refresh(stale: list[(page, reason)], recompiled, added, removed, error)`.
  - If it fails, the transaction is rolled back, the pages stay stale and committed, `error` carries the reason, and the ingestion still succeeds (FR-012).
- **Ingest summary**: `ingest.Summary` gains `wiki: Refresh | None`. The CLI prints one line per stale page and then the counts.
- **What makes a page stale**: the ingestion stamps every symbol of a changed file with the new commit (`_keep_unchanged`), so any edit to a cited file marks its page stale. That is the user's rule, and it errs toward recompiling.
- **Full re-ingestion**: deleting the files sets every citation to null, so every page goes stale and is recompiled.

**Rationale**: marking in the ingest transaction means no reader ever sees new code beside a page called fresh. Recompiling after the commit means a wiki bug cannot cost an ingestion.

**Alternatives considered**:
- Recompiling inside the ingest transaction: a recompile error would roll back the ingestion.
- Recompiling on the next ingestion: the user's test expects one ingestion to mark the page stale and recompile it.
- Computing staleness at read time only: nothing records why a page was rebuilt, and `wiki list` could not show it.

## R8. Pages in search

**Decision**:
- **Storage and index**: pages live in `ccctx_wiki_pages`. Their `search_text` (`page <name> in <directory>\n<text>`) is indexed by a second hybrid vector index, `CCCTX_WIKI_HYBRID_IX`, built with the same model, lexer and `SYNC (ON COMMIT)`.
- **Building it**: `load_model` creates it beside the symbol index. `wiki build` creates it when the model is loaded and the index is missing, so an existing install needs no extra step.
- **Search**:
  - `search` runs the same request against the page index with `topN` of `MAX_LIMIT`, and applies the same keyword-or-floor rule and the same repository and language scope. A page's language is the most common language of its symbols.
  - Each page is placed above the first hit in the fused list, after the definitions block, whose semantic similarity is lower than the page's. A missing similarity counts as the lowest. A page with no similarity goes after every hit that has one. The list is then cut to `limit`.
  - A page hit's `score`, `keyword_rank` and `semantic_rank` are its values within the page index. Its `similarity` is comparable across both indexes, which is why it decides the placement.
- **When the page index is missing**: `require_model` still requires only the model and the symbol index, and search returns symbols only.

**Rationale**:
- The two indexes' fused RRF scores are not comparable. The best of 14 pages always scores near the top of its own index, so merging by fused score would put a page first for every question.
- Cosine similarity comes from the same model on both sides, so it is comparable. It is the honest test of whether a question is closer to the module as a whole or to one of its functions.
- The definitions block is untouched, so identifier queries and the retrieval evaluation's rank-1 checks hold.

**Alternatives considered**:
- Pages as rows of `ccctx_symbols`: a page has no file, every `kind <> 'chunk'` query would need to exclude it, and full re-ingestion would delete it.
- One shared search table for symbols and pages: moving the symbol index re-embeds everything.
- Re-fusing both result lists ourselves: this changes the order of every existing symbol result.

**Fallback if SC-005 fails**: if similarity alone does not put `flask/json` above its functions, add one rule beside the definitions rule: a page whose name's last part is a word of the question ranks first. The live check decides, and the outcome is recorded.

## R9. The tool contract

**Decision**:
- **`search_code` hits**: they keep their shape. A page hit has `kind` `page`, `name` the page name, `path` the directory, `language` the page's language, and a `snippet` of the page's first 10 lines. Its `start_line` and `end_line` are null, which widens their schema type to `integer | null`. Every hit gains `state`: `fresh` or `stale` for a page, null for a symbol, so search shows a stale page as stale (FR-012).
- **`read_wiki(page?, repo?)`** returns `WikiResults`:
  - `status` and `reason`;
  - `page`, which is null when listing: name, repo, directory, language, state, compiled_at, compiler, stale_reason, symbols, text, `citations[]` (at most 200) and `truncated`;
  - `pages[]`, at most 200: name, repo, state and summary (the first purpose sentence).
- **Refusals**: an unknown page, an ambiguous name and an unknown repository come back as `unavailable` with a reason, like the other tools.
- **Version**: 1.1.0, because the contract only gained things.

**Rationale**: one tool for listing and reading keeps the tool count down, and a client gets page names from search or from the list.

**Alternatives considered**:
- A `list_wiki` tool: one more description for the model to choose between.
- A line range of 1 to the page's length: a client would open the directory at lines that do not exist.

## R10. The live staleness check uses a clone

**Decision**: T-polish clones `../ccctx-repos/flask` with `git clone --local` into the scratchpad and registers it as `wiki-flask`. It ingests the clone, builds its wiki, edits and commits `dumps` in `src/flask/json/__init__.py` there, ingests again, and records the summary and the `wiki list` output. It then removes the repository and the clone.

**Rationale**: constitution VII says the tool never modifies indexed code. The user's own steps edit their checkout, and the README shows those steps for them to run.

## R11. Idempotent builds

**Decision**: `wiki build` upserts pages by `(repo_id, directory)`. It writes `text` and `search_text` only when the text changed, so an unchanged page is not re-embedded. It replaces the page's citations, deletes the pages of directories that no longer qualify, and sets `state` to `fresh`, `compiled_at` to now and `wiki_at` if unset. Two builds with no change in between give the same pages, text and citation set (US1-4). Only `compiled_at` moves.

**Rationale**: a rebuild should cost nothing when nothing changed, and its output should be comparable.
