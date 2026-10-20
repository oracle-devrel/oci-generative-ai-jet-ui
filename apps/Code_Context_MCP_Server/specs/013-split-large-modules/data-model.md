# Module Map: Split Large Modules

There is no data model: no schema, table or stored value changes. The design this feature needs is where each
definition goes. This file holds that map:
- **Section 1** covers the source.
- **Section 2** covers the tests.
- **Section 3** lists the definitions the move check may not find unchanged.
- **Section 4** gives the format of the move record kept during the work.

Line counts are estimates: the old lines of the definitions, plus each new file's docstring and imports. All of them
are under the 300-line limit. Where a definition is used decides the file; a constant goes with the functions that
use it. A constant used by several files goes with the main one, and the others import it (research R4).

## 1. Source

Files not listed stay where they are, unchanged: `__init__.py`, `config.py`, `db.py`, `registry.py`, `samples.py`
and `schema.py`. The only edits to them are imports retargeted to the new files.

### parsing/ (from chunker.py 404 and languages.py 852)

| File | Holds | Est. |
|---|---|---|
| `parsing/__init__.py` | docstring only | 5 |
| `parsing/tables.py` | the language tables (`GRAMMARS`, `EXTENSIONS` with the non-code languages, `NAMES`, `WALKERS`, `CALLS`, `IMPORTS`, `SYMBOL_DOCS`, `FILE_DOCS`, `NAMESPACES`, `LEADING`), `register()` (was `languages._register`), and at the end the late import of `parsing.languages` (research R6) | 90 |
| `parsing/common.py` | what several languages share: `Chunk`, `Call`, `Import`, `Found`, `Hit`, `DOTTED`, `COMMENTS`, `_name`, `_definition`, `_text`, `_calls`, `_walk_calls`, `_dotted`, `_child`, `_above`, `_modifiers`, and the doc helpers `_clean`, `_docstring`, `_alone`, `_comments_above`, `_uncomment`, `_block_doc` | 190 |
| `parsing/chunks.py` | `detect_language`, `_parser`, `_public`, `_start`, `parse`, `chunk`, `windows` | 90 |
| `parsing/languages/__init__.py` | imports each language file in registration order | 20 |
| `parsing/languages/python.py` | `_python`, `_python_imports`, Python's doc readers, registration | 55 |
| `parsing/languages/go.py` | `_go_receiver`, `_go_public`, `_go`, `_go_imports`, `_go_doc`, `_go_file_doc`, registration | 60 |
| `parsing/languages/javascript.py` | `JS_FUNCTION_VALUES`, `_javascript`, `_js_bound`, `_js_imports`, `_js_doc`, registration | 75 |
| `parsing/languages/csharp.py` | `CS_*`, `_csharp`, `_identifier`, `_csharp_call`, `_csharp_scopes`, `_csharp_imports`, `_csharp_namespaces`, `XML_*`, `_csharp_doc` | 105 |
| `parsing/languages/typescript.py` | `JS_CALLS`, `TS_*`, `_named`, `_typescript`, `_until_tag`, `_typescript_imports` | 80 |
| `parsing/languages/c_family.py` | `C_*`, `_declared`, `_static`, `_c_family`, `_c_type`, `_c_receiver`, `_c_call`, `_c_name`, `_c_receiver_text`, `_c_includes`, `_doxygen`, `_c_file_doc`, `LICENSE`; registers C and C++ | 160 |
| `parsing/languages/java.py` | `JAVA_*`, `_java_public`, `_java`, `_java_call`, `_java_imports` | 60 |
| `parsing/languages/kotlin.py` | `_kotlin_public`, `_kotlin_kind`, `_kotlin`, `_kotlin_call`, `_kotlin_imports` | 65 |
| `parsing/languages/rust.py` | `_rust_public` … `_rust_file_doc` | 95 |
| `parsing/languages/php.py` | `_php_public` … `_php_file_doc` | 100 |
| `parsing/languages/ruby.py` | `_ruby_private_names` … `_ruby_doc` | 90 |
| `parsing/languages/swift.py` | `_swift_public` … `_swift_doc` | 60 |

### indexing/ (from ingest.py 364)

| File | Holds | Est. |
|---|---|---|
| `indexing/__init__.py` | docstring only | 5 |
| `indexing/files.py` | `GIT_SAFE`, `git`, `_paths`, `_ls`, `_read`, `discover` | 80 |
| `indexing/write.py` | `_sha`, `_insert_symbols`, `_keep_unchanged`, `_write`, `_insert_refs` | 120 |
| `indexing/ingest.py` | `EXTRACT_VERSION`, `IngestError`, `Summary`, `log`, `_lock`, `_full_reason`, `_candidates`, `_prepare`, `ingest` | 175 |

### search/ (from semantic.py 429 and feedback.py 192)

| File | Holds | Est. |
|---|---|---|
| `search/__init__.py` | docstring only | 5 |
| `search/model.py` | `MODEL`, `DIMENSION`, `MODEL_FILE`, `METADATA`, `INDEX`, `LEXER`, `ModelError`, `_state`, `require_model`, `fetch_model`, `_ensure_lexer`, `load_model` | 115 |
| `search/candidates.py` | `IDENTIFIER`, `MAX_CANDIDATES`, `PAGE_CANDIDATES`, `RESERVED`, `text_query`, `_stemmable`, `_hybrid`, `_symbols`, `_page_rows`, `_definitions`, `_page_candidates`, `_candidates` | 125 |
| `search/ranking.py` | `_boosts`, `_boost`, `_fuse`, `MODULE_WORDS`, `names_module`, `_place` | 95 |
| `search/query.py` | `LIMIT`, `MAX_LIMIT`, `LANGUAGES`, `SNIPPET_LINES`, `SNIPPET_CHARS`, `FLOOR`, `MODES`, `Result`, `check_limit`, `check_language`, `_snippet`, `search` | 140 |
| `search/feedback.py` | `BASE`, `SATURATION`, `boost`, `resolve`, `write_use`, `weights`, `FeedbackRow`, `listing`, `add`, `reset` | 145 |
| `search/evaluation.py` | `load_gold`, `matches`, `Evaluation`, `evaluate` | 65 |

### graph/ (from graph.py 490)

| File | Holds | Est. |
|---|---|---|
| `graph/__init__.py` | docstring only | 5 |
| `graph/imports.py` | `JS_SUFFIXES`, `TS_SUFFIXES`, `_suffix_index`, `SEPARATORS`, `_normalize`, `_folder_index`, `_jvm`, `_rust_crate`, `_rust_files`, `_rust`, `_python_index`, `_python`, `_go_module`, `_imports`, `OUTSIDE`, `external_imports` | 225 |
| `graph/build.py` | `SELF`, `BARE_KINDS`, `IMPLICIT_SELF`, `_files`, `_import_refs`, `_enclosing`, `_resolve`, `rebuild` | 100 |
| `graph/queries.py` | `MAX_DEPTH`, `Caller`, `Callee`, `Impact`, `Definition`, `MAX_DEFINITIONS`, `MAX_SOURCE_LINES`, `JOIN`, `check_depth`, `_targets`, `check_name`, `_match`, `definitions`, `callers`, `calls`, `impact` | 195 |

### wiki/ (from wiki.py 578)

| File | Holds | Est. |
|---|---|---|
| `wiki/__init__.py` | docstring only | 5 |
| `wiki/text.py` | `SENTENCE_END`, `SPHINX_ROLE`, `DIRECTIVE`, `UNDERLINE`, `UNSAFE`, `MAX_SENTENCE`, `_sentences`, `_plural`, `_and`, `_ticked` | 65 |
| `wiki/compile.py` | `COMPILER`, `MAX_KEYS`, `MAX_TYPES`, `MAX_CALLED`, `MAX_PURPOSE`, `TYPES`, `ROLES`, `SYMBOL_ROLES`, `LANGUAGE_NAMES`, `NO_DOC`, `TEST_SUFFIXES`, `_Index`, `_Draft`, `_plain_name`, `_names`, `_load`, `_symbol_citation`, `_file_citation`, `_is_test`, `_page`, `_compile` | 215 |
| `wiki/store.py` | `INDEX`, `MAX_TEXT`, `MAX_CITATIONS`, `_Stored`, `_lob`, `ensure_index`, `_stored`, `_write_page`, `_apply`, `_log` | 105 |
| `wiki/build.py` | `THRESHOLD`, `Refresh`, `Built`, `_repo`, `_targets`, `build`, `_build`, `enabled`, `_rewritten`, `mark_stale`, `refresh` | 130 |
| `wiki/read.py` | `WikiError`, `PageInfo`, `CitationView`, `Page`, `_summary`, `pages`, `read` | 95 |

### memory/ (from memory.py 916)

| File | Holds | Est. |
|---|---|---|
| `memory/__init__.py` | docstring only | 5 |
| `memory/store.py` | `AGENT`, `STORE_ID`, `MAX_INPUT_TOKENS`, `MemoryStoreError`, `_store`, `create_package_schema`, `client`, `model` | 75 |
| `memory/runs.py` | `KEEP`, `QUESTION`, `_rows`, `run_of`, `store_use`, `store_runs`, `_STOP`, `record`, `_write_runs`, `flush`, `_drain`, `RunView`, `runs` | 185 |
| `memory/findings.py` | `NO_FACTS`, `NAMES`, `SOURCE_LINES`, `Finding`, `_plain`, `_json`, `pending`, `_symbol`, `_page`, `_ref`, `_key`, `_names`, `finding` | 155 |
| `memory/distill.py` | `CONSOLIDATOR`, `TEMPLATE`, `_Fact`, `_plural`, `_quoted`, `template_text`, `WORD`, `CODE`, `SPAN`, `_names_in`, `unknown_names`, `_source`, `ANSWER`, `_prompt`, `_distill` | 150 |
| `memory/consolidate.py` | `Consolidation`, `_now`, `_norm`, `confidence`, `_same`, `_new_meta`, `_contradict`, `_merge`, `_load`, `_status`, `_write`, `_lock`, `_consolidate`, `consolidate` | 205 |
| `memory/recheck.py` | `_ask_again`, `_stale`, `_rekey`, `recheck`, `_definitions` | 120 |
| `memory/recall.py` | `FactView`, `_sources`, `_records`, `_ordered`, `_views`, `facts`, `Recall`, `recall`, `forget`, `search_facts` | 165 |

### server/ (from server.py 610)

| File | Holds | Est. |
|---|---|---|
| `server/__init__.py` | docstring; imports the tool files in listing order (research R6); the strict-arguments loop; exposes `main` | 30 |
| `server/__main__.py` | runs `main()` | 5 |
| `server/app.py` | `NAME`, `INSTRUCTIONS`, `mcp`, `READ_ONLY`, `SESSION`, `LIMIT`, `log`, `_returned`, `_client`, `_use`, `_opened`, `_logged`, `_answer`, `_repos`, `main` | 130 |
| `server/search_tools.py` | `SearchHit`, `SearchResults`, `search_code`, `SymbolHit`, `SymbolResults`, `get_symbol` | 110 |
| `server/graph_tools.py` | `CallerHit`, `CalleeHit`, `ImpactHit`, `CallerResults`, `CalleeResults`, `ImpactResults`, `_graph`, `find_callers`, `find_callees`, `impact_of` | 100 |
| `server/wiki_tools.py` | `WikiCitation`, `WikiPage`, `WikiPageInfo`, `WikiResults`, `_iso`, `read_wiki` | 90 |
| `server/repository_tools.py` | `RepoInfo`, `RepoList`, `list_repositories` | 40 |
| `server/memory_tools.py` | `RecallSource`, `RecallFact`, `RecallRun`, `RecallResults`, `recall`, `MarkUsedResult`, `mark_used` | 125 |

### cli/ (from cli.py 529)

| File | Holds | Est. |
|---|---|---|
| `cli/__init__.py` | docstring; exposes `main` | 5 |
| `cli/__main__.py` | runs `main()` | 5 |
| `cli/format.py` | `SKIP_ORDER`, `format_table`, `format_summary`, `_format_memory`, `_format_wiki`, `_format_full`, `_format_incremental` | 90 |
| `cli/index_commands.py` | `_repo_add`, `_repo_list`, `_ingest`, `_symbols`, `_stats`, `_model_load`, `_db_migrate` | 85 |
| `cli/search_commands.py` | `_repos`, `_dash`, `_search`, `_percent`, `_callers`, `_calls`, `_impact`, `GRAPH`, `_eval` | 80 |
| `cli/wiki_commands.py` | `_when`, `_wiki_build`, `_wiki_list`, `_source`, `_wiki_show`, `_wiki_citations`, `_top` | 75 |
| `cli/memory_commands.py` | `_memory_list`, `_distillers`, `_memory_consolidate`, `_fact_text`, `_memory_facts`, `_feedback_list`, `_feedback_add`, `_feedback_reset` | 70 |
| `cli/parser.py` | `KINDS`, `_positive`, `_not_negative`, `_count`, `_eval_limit`, `parser` | 125 |
| `cli/main.py` | `main` | 65 |

The source goes from 16 files (longest 916 lines) to 69 files (longest about 225): 63 in the eight area folders and
the 6 that stay at the top level. TypeScript reuses JavaScript's import reader and doc reader, so
`languages/typescript.py` imports `languages/javascript.py`. No other language file imports another.

## 2. Tests

Each test file is named for the source file it tests (research R11). The groupings below are by concern. The exact
test-by-test moves are recorded during the work (Section 4).

| Today | Lines | Goes to |
|---|---|---|
| `conftest.py` | 26 | `tests/conftest.py`: the memory guard, plus the shared `conn` fixture |
| (new) | | `tests/support.py`: `git`, `commit`, `write_files`, `make_repo` |
| (new) | | `tests/test_layout.py`: size, docstring and README checks (research R12) |
| `test_config.py`, `test_db.py`, `test_registry.py`, `test_samples.py` | 55–145 | stay; only their setup moves to the shared fixture |
| `test_schema.py` | 533 | `test_schema.py` (migrate, version, repos, files, symbols, revisions, language columns); `test_schema_graph.py`; `test_schema_wiki.py`; `test_schema_memory.py` (memory and feedback tables) |
| `test_chunker.py` | 402 | `tests/parsing/test_chunks.py`, `tests/parsing/languages/test_python.py`, `test_go.py`, `test_javascript.py` |
| `test_languages.py` | 391 | `tests/parsing/languages/test_<language>.py`, one per language file; the cross-language checks go to `tests/parsing/test_tables.py` |
| `test_ingest.py` | 822 | `tests/indexing/test_files.py`, `test_write.py`, `test_ingest.py` and `test_ingest_<concern>.py` as the 300-line limit needs, with a shared `tests/indexing/conftest.py` |
| `test_semantic.py` | 477 | `tests/search/test_model.py`, `test_candidates.py`, `test_ranking.py`, `test_query.py` |
| `test_feedback.py` | 341 | `tests/search/test_feedback.py` (and `test_feedback_<concern>.py` if needed) |
| `test_eval.py` | 193 | `tests/search/test_evaluation.py` |
| `test_graph.py` | 701 | `tests/graph/test_imports.py`, `test_build.py`, `test_queries.py`, with a shared `tests/graph/conftest.py` |
| `test_wiki.py` | 576 | `tests/wiki/test_text.py`, `test_compile.py`, `test_store.py`, `test_build.py`, `test_read.py` |
| `test_memory.py` | 880 | `tests/memory/test_runs.py`, `test_findings.py`, `test_distill.py`, `test_consolidate.py`, `test_recheck.py`, `test_recall.py` |
| `test_server.py` | 843 | `tests/server/test_app.py`, `test_search_tools.py`, `test_graph_tools.py`, `test_wiki_tools.py`, `test_repository_tools.py`, `test_memory_tools.py` |
| `test_cli.py` | 930 | `tests/cli/test_format.py`, `test_index_commands.py`, `test_search_commands.py`, `test_wiki_commands.py`, `test_memory_commands.py`, `test_parser.py`, `test_main.py` |

A test that checks several files at once, such as an end-to-end ingest followed by a search, goes with the file
whose behavior it asserts. That choice is noted in the move record.

## 3. Expected differences for the move check

The move check (research R9) finds every master definition once, unchanged, except these:

1. **Language registration.** Python, Go and JavaScript were dict literals in `chunker.py`. They become
   `register(...)` calls in their language files. The table contents and order must still match (research R6,
   checked by the baseline).
2. **The merge loop.** `chunker.py`'s loop that copied `languages.py`'s tables into its own is removed. It has nothing
   left to merge.
3. **`_register` → `register`.** The function is renamed, now that the language files call it from another file. This
   is the one rename (research R8).
4. **`server.py`'s strict-arguments loop.** It moves to `server/__init__.py`, unchanged.
5. **Late imports.** The six late imports (research R5) are retargeted. Each is the same statement with a new module
   path.
6. **New code.** The new `__init__.py` and `__main__.py` files, and new test files: `test_layout.py`, `support.py`
   and the folder `conftest.py` files.
7. **Test fixtures.** A fixture that was defined in several test files appears once in the shared setup. It is listed
   per file in the move record.

## 4. The move record

`specs/013-split-large-modules/moves.md` is kept during the work. It holds:

- **Source moves.** A table of old file and definition, with its new file.
- **Test moves.** A table of old test id, with its new test id. A test whose name changed is marked "renamed"; one
  merged with an identical test is marked "merged".
- **Cross-file private names.** The underscore names that another file now uses (research R8), for a later clean-up.
- **Bugs found and not fixed.** Behavior is frozen (spec, Assumptions), so they are listed instead.
