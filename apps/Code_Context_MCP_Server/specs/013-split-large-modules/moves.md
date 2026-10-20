# Move Record: Split Large Modules

Where each definition and test went, and what was found along the way (data-model.md Section 4). The tables of
source and test moves are printed by `movecheck.py --report` and `movecheck.py --tests --report`.

## Source moves

From `movecheck.py --report` at the US1 checkpoint (T032): every top-level definition of master's
source, by old file, and the file it is in now. Each was found once, unchanged (`0 missing, 0 changed,
0 duplicated`), apart from the reviewed differences in `movecheck.py`'s `EXPECTED`.

| Old file | Definitions | New file |
| `src/golestan_code_mcp/__init__.py` | `__version__` | `src/golestan_code_mcp/__init__.py` |
| `src/golestan_code_mcp/chunker.py` | `_calls`, `_parser`, `_start`, `chunk`, `detect_language`, `parse`, `windows` | `src/golestan_code_mcp/parsing/chunks.py` |
| `src/golestan_code_mcp/chunker.py` | `Call`, `Chunk`, `DOC_LIMIT`, `DOTTED`, `Found`, `Import`, `QUOTES`, `UNDERLINE`, `_alone`, `_clean`, `_comments_above`, `_definition`, `_docstring`, `_name`, `_public`, `_text`, `_uncomment` | `src/golestan_code_mcp/parsing/common.py` |
| `src/golestan_code_mcp/chunker.py` | `_go`, `_go_doc`, `_go_file_doc`, `_go_imports`, `_go_public`, `_go_receiver` | `src/golestan_code_mcp/parsing/languages/go.py` |
| `src/golestan_code_mcp/chunker.py` | `JS_FUNCTION_VALUES`, `_javascript`, `_js_bound`, `_js_doc`, `_js_imports` | `src/golestan_code_mcp/parsing/languages/javascript.py` |
| `src/golestan_code_mcp/chunker.py` | `_python`, `_python_imports` | `src/golestan_code_mcp/parsing/languages/python.py` |
| `src/golestan_code_mcp/chunker.py` | `EXTENSIONS`, `LEADING`, `NAMES`, `NAMESPACES` | `src/golestan_code_mcp/parsing/tables.py` |
| `src/golestan_code_mcp/chunker.py` | CALLS, FILE_DOCS, GRAMMARS, IMPORTS, SYMBOL_DOCS, WALKERS | src/golestan_code_mcp/parsing/tables.py (changed: Section 3.1) |
| `src/golestan_code_mcp/cli.py` | `main` | `src/golestan_code_mcp/cli/entry.py` |
| `src/golestan_code_mcp/cli.py` | `_db_migrate`, `_ingest`, `_model_load`, `_repo_add`, `_repo_list`, `_stats`, `_symbols` | `src/golestan_code_mcp/cli/index_commands.py` |
| `src/golestan_code_mcp/cli.py` | `_distillers`, `_fact_text`, `_feedback_add`, `_feedback_list`, `_feedback_reset`, `_memory_consolidate`, `_memory_facts`, `_memory_list` | `src/golestan_code_mcp/cli/memory_commands.py` |
| `src/golestan_code_mcp/cli.py` | `SKIP_ORDER`, `_format_full`, `_format_incremental`, `_format_memory`, `_format_wiki`, `format_summary`, `format_table` | `src/golestan_code_mcp/cli/output.py` |
| `src/golestan_code_mcp/cli.py` | `KINDS`, `_count`, `_eval_limit`, `_not_negative`, `_positive`, `parser` | `src/golestan_code_mcp/cli/parser.py` |
| `src/golestan_code_mcp/cli.py` | `GRAPH`, `_callers`, `_calls`, `_dash`, `_eval`, `_impact`, `_percent`, `_repos`, `_search` | `src/golestan_code_mcp/cli/search_commands.py` |
| `src/golestan_code_mcp/cli.py` | `_source`, `_top`, `_when`, `_wiki_build`, `_wiki_citations`, `_wiki_list`, `_wiki_show` | `src/golestan_code_mcp/cli/wiki_commands.py` |
| `src/golestan_code_mcp/config.py` | `Config`, `ConfigError`, `MODEL_URL`, `MemoryModel`, `PROJECT_ROOT`, `_number`, `_weight`, `environment`, `feedback_cap`, `feedback_half_life`, `load`, `max_file_bytes`, `memory_model`, `model_cache`, `model_url`, `repos_dir`, `search_candidates`, `text_weight`, `vector_weight`, `vendor_dirs` | `src/golestan_code_mcp/config.py` |
| `src/golestan_code_mcp/db.py` | `CheckResult`, `STARTING_CODES`, `VECTOR_SQL`, `check`, `connect`, `describe`, `main` | `src/golestan_code_mcp/db.py` |
| `src/golestan_code_mcp/feedback.py` | `Evaluation`, `load_gold`, `matches` | `src/golestan_code_mcp/search/evaluation.py` |
| `src/golestan_code_mcp/feedback.py` | evaluate | src/golestan_code_mcp/search/evaluation.py (changed: its late import of semantic is now an ordinary import of search.query) |
| `src/golestan_code_mcp/feedback.py` | `BASE`, `FeedbackRow`, `SATURATION`, `add`, `boost`, `listing`, `reset`, `resolve`, `weights`, `write_use` | `src/golestan_code_mcp/search/feedback.py` |
| `src/golestan_code_mcp/graph.py` | `BARE_KINDS`, `IMPLICIT_SELF`, `SELF`, `_enclosing`, `_resolve`, `rebuild` | `src/golestan_code_mcp/graph/build.py` |
| `src/golestan_code_mcp/graph.py` | `JS_SUFFIXES`, `OUTSIDE`, `SEPARATORS`, `TS_SUFFIXES`, `_files`, `_folder_index`, `_go_module`, `_import_refs`, `_imports`, `_jvm`, `_normalize`, `_python`, `_python_index`, `_rust`, `_rust_crate`, `_rust_files`, `_suffix_index`, `external_imports` | `src/golestan_code_mcp/graph/imports.py` |
| `src/golestan_code_mcp/graph.py` | `Callee`, `Caller`, `Definition`, `Impact`, `JOIN`, `MAX_DEFINITIONS`, `MAX_DEPTH`, `MAX_SOURCE_LINES`, `_match`, `_targets`, `callers`, `calls`, `check_depth`, `check_name`, `definitions`, `impact` | `src/golestan_code_mcp/graph/queries.py` |
| `src/golestan_code_mcp/ingest.py` | `GIT_SAFE`, `IngestError`, `_ls`, `_paths`, `_read`, `discover`, `git` | `src/golestan_code_mcp/indexing/files.py` |
| `src/golestan_code_mcp/ingest.py` | `Summary`, `_candidates`, `_full_reason`, `_lock`, `_prepare`, `ingest`, `log` | `src/golestan_code_mcp/indexing/ingest.py` |
| `src/golestan_code_mcp/ingest.py` | `EXTRACT_VERSION`, `_insert_refs`, `_insert_symbols`, `_keep_unchanged`, `_sha`, `_write` | `src/golestan_code_mcp/indexing/write.py` |
| `src/golestan_code_mcp/languages.py` | `COMMENTS`, `Hit`, `_above`, `_block_doc`, `_c_receiver`, `_child`, `_dotted`, `_modifiers`, `_named`, `_until_tag`, `_walk_calls` | `src/golestan_code_mcp/parsing/common.py` |
| `src/golestan_code_mcp/languages.py` | `C_PASS_THROUGH`, `C_SCOPED`, `C_TYPES`, `DOXYGEN`, `LICENSE`, `_c_call`, `_c_family`, `_c_file_doc`, `_c_includes`, `_c_name`, `_c_receiver_text`, `_c_type`, `_declared`, `_doxygen`, `_static` | `src/golestan_code_mcp/parsing/languages/c_family.py` |
| `src/golestan_code_mcp/languages.py` | `CS_MEMBERS`, `CS_NAMESPACES`, `CS_TYPES`, `XML_REF`, `XML_TAG`, `_csharp`, `_csharp_call`, `_csharp_doc`, `_csharp_imports`, `_csharp_namespaces`, `_csharp_scopes`, `_identifier` | `src/golestan_code_mcp/parsing/languages/csharp.py` |
| `src/golestan_code_mcp/languages.py` | `JAVA_MEMBERS`, `JAVA_TYPES`, `_java`, `_java_call`, `_java_imports`, `_java_public` | `src/golestan_code_mcp/parsing/languages/java.py` |
| `src/golestan_code_mcp/languages.py` | `_kotlin`, `_kotlin_call`, `_kotlin_imports`, `_kotlin_kind`, `_kotlin_public` | `src/golestan_code_mcp/parsing/languages/kotlin.py` |
| `src/golestan_code_mcp/languages.py` | `PHP_REQUIRES`, `PHP_TYPES`, `_php`, `_php_call`, `_php_file_doc`, `_php_imports`, `_php_last`, `_php_path`, `_php_public`, `_php_receiver`, `_php_string` | `src/golestan_code_mcp/parsing/languages/php.py` |
| `src/golestan_code_mcp/languages.py` | `RUBY_REQUIRES`, `_ruby`, `_ruby_call`, `_ruby_doc`, `_ruby_imports`, `_ruby_private_names` | `src/golestan_code_mcp/parsing/languages/ruby.py` |
| `src/golestan_code_mcp/languages.py` | `RUST_TYPES`, `_rust`, `_rust_call`, `_rust_doc`, `_rust_docs`, `_rust_file_doc`, `_rust_imports`, `_rust_public`, `_rust_type_name` | `src/golestan_code_mcp/parsing/languages/rust.py` |
| `src/golestan_code_mcp/languages.py` | `SWIFT_KINDS`, `_swift`, `_swift_call`, `_swift_doc`, `_swift_imports`, `_swift_public` | `src/golestan_code_mcp/parsing/languages/swift.py` |
| `src/golestan_code_mcp/languages.py` | `TS_CLASSES`, `TS_FUNCTIONS`, `TS_TYPES`, `_typescript`, `_typescript_imports` | `src/golestan_code_mcp/parsing/languages/typescript.py` |
| `src/golestan_code_mcp/languages.py` | JS_CALLS | src/golestan_code_mcp/parsing/languages/typescript.py (changed: reads tables.CALLS by its name instead of chunker's CALLS as _BASE_CALLS alias) |
| `src/golestan_code_mcp/languages.py` | `CALLS`, `FILE_DOCS`, `GRAMMARS`, `IMPORTS`, `LEADING`, `NAMES`, `NAMESPACES`, `SYMBOL_DOCS`, `register` | `src/golestan_code_mcp/parsing/tables.py` |
| `src/golestan_code_mcp/languages.py` | EXTENSIONS, WALKERS | src/golestan_code_mcp/parsing/tables.py (changed: Section 3.1) |
| `src/golestan_code_mcp/memory.py` | `Consolidation`, `_consolidate`, `_load`, `_lock`, `_merge`, `_new_meta`, `_norm`, `_now`, `_same`, `_status`, `_write`, `confidence`, `consolidate` | `src/golestan_code_mcp/memory/consolidate.py` |
| `src/golestan_code_mcp/memory.py` | `ANSWER`, `CODE`, `CONSOLIDATOR`, `SPAN`, `TEMPLATE`, `WORD`, `_Fact`, `_contradict`, `_distill`, `_names_in`, `_plural`, `_prompt`, `_quoted`, `_source`, `template_text`, `unknown_names` | `src/golestan_code_mcp/memory/distill.py` |
| `src/golestan_code_mcp/memory.py` | `Finding`, `NAMES`, `NO_FACTS`, `SOURCE_LINES`, `_json`, `_key`, `_names`, `_page`, `_plain`, `_ref`, `_symbol`, `finding`, `pending` | `src/golestan_code_mcp/memory/findings.py` |
| `src/golestan_code_mcp/memory.py` | `FACT_CANDIDATES`, `FactView`, `RECALL_RUNS`, `Recall`, `SIMILARITY_SQL`, `_ordered`, `_records`, `_sources`, `_views`, `facts`, `forget`, `recall`, `search_facts` | `src/golestan_code_mcp/memory/recall.py` |
| `src/golestan_code_mcp/memory.py` | `_ask_again`, `_definitions`, `_rekey`, `_stale`, `recheck` | `src/golestan_code_mcp/memory/recheck.py` |
| `src/golestan_code_mcp/memory.py` | `KEEP`, `QUESTION`, `RunView`, `_STOP`, `_drain`, `_rows`, `_runs`, `_write_runs`, `_writer`, `_writer_lock`, `flush`, `record`, `run_of`, `runs`, `store_runs`, `store_use` | `src/golestan_code_mcp/memory/runs.py` |
| `src/golestan_code_mcp/memory.py` | `AGENT`, `MAX_INPUT_TOKENS`, `MemoryStoreError`, `STORE_ID`, `_store`, `client`, `create_package_schema`, `log`, `model` | `src/golestan_code_mcp/memory/store.py` |
| `src/golestan_code_mcp/registry.py` | `NAME_RE`, `RegistryError`, `Repo`, `_conflict`, `add_repo`, `get_repo`, `list_repos`, `repo_id`, `resolve_dir`, `validate_name` | `src/golestan_code_mcp/registry.py` |
| `src/golestan_code_mcp/samples.py` | `CloneFailed`, `InsideProject`, `REPOS`, `Repo`, `_head`, `clone`, `main` | `src/golestan_code_mcp/samples.py` |
| `src/golestan_code_mcp/schema.py` | `ALREADY_EXISTS`, `BACKFILL_SEARCH_TEXT`, `MIGRATIONS`, `TRACKING`, `_package_schema`, `_run`, `migrate`, `version` | `src/golestan_code_mcp/schema.py` |
| `src/golestan_code_mcp/semantic.py` | `IDENTIFIER`, `MAX_CANDIDATES`, `PAGE_CANDIDATES`, `RESERVED`, `SNIPPET_CHARS`, `SNIPPET_LINES`, `_candidates`, `_definitions`, `_hybrid`, `_page_candidates`, `_page_rows`, `_snippet`, `_stemmable`, `_symbols`, `text_query` | `src/golestan_code_mcp/search/candidates.py` |
| `src/golestan_code_mcp/semantic.py` | `DIMENSION`, `INDEX`, `LEXER`, `METADATA`, `MODEL`, `MODEL_FILE`, `ModelError`, `_ensure_lexer`, `_state`, `fetch_model`, `load_model`, `require_model` | `src/golestan_code_mcp/search/model.py` |
| `src/golestan_code_mcp/semantic.py` | `LANGUAGES`, `LIMIT`, `MAX_LIMIT`, `MODES`, `Result`, `check_language`, `check_limit`, `search` | `src/golestan_code_mcp/search/query.py` |
| `src/golestan_code_mcp/semantic.py` | `FLOOR`, `MODULE_WORDS`, `_boost`, `_fuse`, `_place`, `names_module` | `src/golestan_code_mcp/search/ranking.py` |
| `src/golestan_code_mcp/semantic.py` | _boosts | src/golestan_code_mcp/search/ranking.py (changed: its late import of feedback is now an ordinary import) |
| `src/golestan_code_mcp/server.py` | `INSTRUCTIONS`, `LIMIT`, `NAME`, `Name`, `READ_ONLY`, `Repo`, `SESSION`, `_answer`, `_client`, `_logged`, `_opened`, `_repos`, `_returned`, `_use`, `log`, `main`, `mcp` | `src/golestan_code_mcp/server/app.py` |
| `src/golestan_code_mcp/server.py` | `CalleeHit`, `CalleeResults`, `CallerHit`, `CallerResults`, `ImpactHit`, `ImpactResults`, `_graph`, `find_callees`, `find_callers`, `impact_of` | `src/golestan_code_mcp/server/graph_tools.py` |
| `src/golestan_code_mcp/server.py` | `MarkUsedResult`, `RecallFact`, `RecallResults`, `RecallRun`, `RecallSource`, `mark_used`, `recall` | `src/golestan_code_mcp/server/memory_tools.py` |
| `src/golestan_code_mcp/server.py` | `RepoInfo`, `RepoList`, `list_repositories` | `src/golestan_code_mcp/server/repository_tools.py` |
| `src/golestan_code_mcp/server.py` | `SearchHit`, `SearchResults`, `SymbolHit`, `SymbolResults`, `get_symbol`, `search_code` | `src/golestan_code_mcp/server/search_tools.py` |
| `src/golestan_code_mcp/server.py` | `WikiCitation`, `WikiPage`, `WikiPageInfo`, `WikiResults`, `_iso`, `read_wiki` | `src/golestan_code_mcp/server/wiki_tools.py` |
| `src/golestan_code_mcp/wiki.py` | `Built`, `Refresh`, `_build`, `_log`, `_rewritten`, `_targets`, `build`, `enabled`, `log`, `mark_stale`, `refresh` | `src/golestan_code_mcp/wiki/build.py` |
| `src/golestan_code_mcp/wiki.py` | `COMPILER`, `LANGUAGE_NAMES`, `MAX_CALLED`, `MAX_KEYS`, `MAX_PURPOSE`, `MAX_TEXT`, `MAX_TYPES`, `NO_DOC`, `ROLES`, `SYMBOL_ROLES`, `TEST_SUFFIXES`, `THRESHOLD`, `TYPES`, `_Draft`, `_Index`, `_compile`, `_file_citation`, `_is_test`, `_load`, `_names`, `_page`, `_plain_name`, `_symbol_citation` | `src/golestan_code_mcp/wiki/compile.py` |
| `src/golestan_code_mcp/wiki.py` | `CitationView`, `Page`, `PageInfo`, `_summary`, `pages`, `read` | `src/golestan_code_mcp/wiki/read.py` |
| `src/golestan_code_mcp/wiki.py` | `INDEX`, `MAX_CITATIONS`, `WikiError`, `_Stored`, `_apply`, `_lob`, `_repo`, `_stored`, `_write_page`, `ensure_index` | `src/golestan_code_mcp/wiki/store.py` |
| `src/golestan_code_mcp/wiki.py` | `DIRECTIVE`, `MAX_SENTENCE`, `SENTENCE_END`, `SPHINX_ROLE`, `UNDERLINE`, `UNSAFE`, `_EXTENSIONS`, `_and`, `_plural`, `_sentences`, `_ticked` | `src/golestan_code_mcp/wiki/text.py` |

### Changes to the module map

Placed differently from data-model.md Section 1, to avoid an import cycle between two new files or a confusing name:

| Definition | Planned in | Now in | Why |
|---|---|---|---|
| `_public` | `parsing/chunks.py` | `parsing/common.py` | Python's and JavaScript's walkers use it; chunks imports the tables, which import the languages |
| `_calls` | `parsing/common.py` | `parsing/chunks.py` | it reads `tables.CALLS`; in common.py it would make common and tables import each other |
| `_named`, `_until_tag` | `parsing/languages/typescript.py` | `parsing/common.py` | C, C++ and PHP use them too; no language file imports another, apart from TypeScript importing JavaScript |
| `_c_receiver` | `parsing/languages/c_family.py` | `parsing/common.py` | Ruby and Rust use it too |
| `_files`, `_import_refs`, `external_imports` | `graph/build.py` | `graph/imports.py` | `external_imports` needs both, and the wiki needs it without the edge rebuild |
| `FLOOR` | `search/query.py` | `search/ranking.py` | the ranking applies it; in query.py, query and ranking would import each other |
| `SNIPPET_LINES`, `SNIPPET_CHARS`, `_snippet` | `search/query.py` | `search/candidates.py` | the candidate queries cut the snippets; same reason |
| `THRESHOLD`, `MAX_TEXT` | `wiki/build.py`, `wiki/store.py` | `wiki/compile.py` | the compiler applies them; compile no longer imports build or store |
| `WikiError`, `_repo` | `wiki/read.py`, `wiki/build.py` | `wiki/store.py` | build and read both use them; build and read would import each other |
| `log`, `_log` | `wiki/store.py` | `wiki/build.py` | only the builds log |
| `_contradict` | `memory/consolidate.py` | `memory/distill.py` | recheck uses it too; it changes a `_Fact`, defined beside it |
| `IngestError` | `indexing/ingest.py` | `indexing/files.py` | git's failures raise it first |
| `EXTRACT_VERSION` | `indexing/ingest.py` | `indexing/write.py` | the write stores it; ingest compares with it |
| `main` | `cli/main.py` | `cli/entry.py` | `cli/__init__.py` exposes the function `main`, which would hide a submodule of that name |
| the output helpers | `cli/format.py` | `cli/output.py` | `format` would hide Python's built-in `format()` wherever the module is imported |

Two late imports became ordinary imports, because the split removed the cycle they avoided (research R5):
`search/ranking.py` imports `search/feedback.py`, and `search/evaluation.py` imports `search/query.py`.

## Test moves

Every test kept its name: no test was renamed or merged, so a test's old id is its new file plus the same name.
`movecheck.py --tests` found every master test function once, unchanged (`0 missing, 0 changed, 0 duplicated`), and
the suite collects 686 tests besides the layout ones, as master does (T002). By old file, the definitions and the
file each is in now (`movecheck.py --tests --report`):

| Old file | Definitions | New file |
|---|---|---|
| `tests/conftest.py` | `_keep_real_repositories_out_of_memory`, `real_recording` | `tests/conftest.py` |
| `tests/test_chunker.py` | `FIXTURES`, `GO_DOCS`, `PY_DOCS`, `PY_SOURCE`, `docs`, `numbered`, `outline`, `refs`, `spans` | `tests/parsing/helpers.py` |
| `tests/test_chunker.py` | `GO_SOURCE`, `test_go_calls_and_imports`, `test_go_header_separated_by_a_blank_line_is_not_attached`, `test_go_outline`, `test_go_symbol_and_package_docs` | `tests/parsing/languages/test_go.py` |
| `tests/test_chunker.py` | `JS_DOCS`, `JS_SOURCE`, `test_javascript_calls_and_imports`, `test_javascript_docs`, `test_javascript_outline` | `tests/parsing/languages/test_javascript.py` |
| `tests/test_chunker.py` | `test_python_calls`, `test_python_file_without_docstring`, `test_python_imports`, `test_python_outline`, `test_python_symbol_and_module_docs` | `tests/parsing/languages/test_python.py` |
| `tests/test_chunker.py` | `test_an_rst_heading_is_skipped_for_the_paragraph_after_it`, `test_crlf_text_matches_lf`, `test_detect_language`, `test_doc_is_cut_at_1000_characters`, `test_docs_leave_chunks_unchanged`, `test_empty_text_has_no_windows`, `test_exported_follows_the_name_rule`, `test_parse_chunks_match_chunk`, `test_parse_error_returns_none`, `test_parse_returns_namespaces_last`, `test_sixty_lines_is_one_window`, `test_syntax_error_yields_no_calls_or_imports`, `test_unknown_language_returns_none`, `test_windows_have_no_exported`, `test_windows_overlap_and_stop_at_last_line`, `test_windows_source_is_the_lines` | `tests/parsing/test_chunks.py` |
| `tests/test_chunker.py` | `test_new_grammars_load_only_when_used` | `tests/parsing/test_chunks.py (changed: imports golestan_code_mcp.parsing.chunks, named in its code string, in place of golestan_code_mcp.chunker)` |
| `tests/test_cli.py` | `distilled`, `graphed`, `ingested`, `live`, `model`, `remembered`, `wikirepo` | `tests/cli/conftest.py` |
| `tests/test_cli.py` | `FAKE_PW`, `HEADER`, `WIKI_PKG`, `WIKI_USER`, `a_run`, `make_repo`, `make_wiki_repo`, `run`, `summary`, `symbol_run`, `table`, `untimed` | `tests/cli/helpers.py` |
| `tests/test_cli.py` | `test_mcp_child_process_serves_the_tools_from_any_directory`, `test_mcp_starts_the_server_without_connecting` | `tests/cli/test_entry.py` |
| `tests/test_cli.py` | `test_bad_depth_refused_before_connecting`, `test_eval_bad_limit_exits_2`, `test_eval_gold_errors_exit_1`, `test_eval_prints_questions_recall_and_misses`, `test_graph_empty_name_refused_before_connecting`, `test_graph_empty_results`, `test_graph_repo_flags_and_default_depth`, `test_graph_tables`, `test_graph_unknown_name_exits_1` | `tests/cli/test_graph_commands.py` |
| `tests/test_cli.py` | `test_add_then_list`, `test_duplicate_name_exits_1`, `test_empty_registry`, `test_ingest_again_then_full`, `test_ingest_prints_summary`, `test_ingest_prints_the_pages_it_recompiled`, `test_ingest_refusals_exit_1`, `test_ingest_warns_when_the_wiki_was_not_recompiled`, `test_migrate`, `test_missing_setting_exits_1`, `test_model_load_when_present`, `test_note_goes_to_stderr`, `test_refusals_without_database`, `test_stats_by_language`, `test_symbols_lists_parsed_first`, `test_unreachable_exits_2_fast_without_secret` | `tests/cli/test_index_commands.py` |
| `tests/test_cli.py` | `test_feedback_add_bad_numbers_exit_2`, `test_feedback_add_refusals`, `test_feedback_add_then_list`, `test_feedback_list_empty_and_unknown`, `test_feedback_reset`, `test_feedback_reset_needs_exactly_one_scope`, `test_memory_consolidate_line_and_rerun`, `test_memory_facts_empty_and_refusals`, `test_memory_facts_table`, `test_memory_list_limit_and_empty`, `test_memory_list_newest_first`, `test_memory_list_refusals`, `test_memory_list_shows_used_of_returned` | `tests/cli/test_memory_commands.py` |
| `tests/test_cli.py` | `test_format_incremental_summary`, `test_format_summary_fallback_and_reason_order`, `test_format_summary_matches_request`, `test_format_summary_nothing_skipped`, `test_format_table`, `test_format_up_to_date`, `test_incremental_summary_reports_reparsed_files`, `test_ingest_summary_memory_line`, `test_ingest_summary_wiki_lines`, `test_no_reparsed_line_without_reparsed_files` | `tests/cli/test_output.py` |
| `tests/test_cli.py` | `test_search_bad_language_or_limit_refused_before_connecting`, `test_search_empty_question_refused_before_connecting`, `test_search_empty_results`, `test_search_language_and_limit_match_core`, `test_search_language_and_limit_reach_the_core`, `test_search_missing_model_hint`, `test_search_modes`, `test_search_prints_ranked_table`, `test_search_repo_flags_narrow`, `test_search_shows_page_rows`, `test_search_shows_the_feedback_column`, `test_search_unknown_mode_refused_before_connecting`, `test_search_unknown_repo`, `test_search_unreachable_exits_2` | `tests/cli/test_search_commands.py` |
| `tests/test_cli.py` | `test_wiki_ambiguous_page_needs_repo`, `test_wiki_build_notes_when_pages_are_not_searchable`, `test_wiki_build_prints_one_line_per_repository`, `test_wiki_citations_table`, `test_wiki_list_columns`, `test_wiki_list_without_pages`, `test_wiki_refusals_exit_1`, `test_wiki_show_prints_the_stored_text_then_sources`, `test_wiki_unreachable_exits_2` | `tests/cli/test_wiki_commands.py` |
| `tests/test_config.py` | `BASE`, `SECRET`, `test_absolute_repos_dir_kept`, `test_all_missing_and_blank_named_together`, `test_bad_feedback_settings_named`, `test_bad_max_file_bytes_named`, `test_bad_port_named`, `test_bad_search_settings_named`, `test_defaults_applied`, `test_environment_wins_over_dotenv`, `test_feedback_settings_defaults_and_overrides`, `test_ingest_limits_defaults_and_overrides`, `test_memory_model_environment_wins_over_dotenv`, `test_memory_model_settings_and_hidden_key`, `test_memory_model_unset_or_blank_means_none`, `test_model_settings_defaults_and_overrides`, `test_password_never_shown`, `test_search_settings_defaults_and_overrides` | `tests/test_config.py` |
| `tests/test_db.py` | `cfg`, `test_check_ok`, `test_main_output_has_no_secret`, `test_smoke_rows_grow`, `test_unreachable_reports_reason_without_secret` | `tests/test_db.py` |
| `tests/test_eval.py` | `BASELINE_HITS`, `EVAL_VERSION`, `GOLD`, `IDENTIFIERS`, `QUESTION`, `ROUTING`, `ROUTING_QUESTION`, `added`, `baseline`, `conn`, `counts`, `gold`, `gold_file`, `test_a_hammered_symbol_never_takes_over`, `test_a_missing_gold_file`, `test_bad_gold_files_are_refused`, `test_evaluation_records_nothing_and_holds_the_floor`, `test_expected_paths_match_files_and_directories`, `test_feedback_on_expected_results_holds_or_improves_recall`, `test_identifier_definitions_at_rank_one`, `test_out_of_domain_question`, `test_repository_scope`, `test_routing_question_finds_both_repositories`, `test_the_gold_set_has_twenty_questions_in_plain_words`, `test_url_for_definitions_first`, `where` | `tests/search/test_evaluation.py` |
| `tests/test_feedback.py` | `conn` | `tests/conftest.py (changed: T033)` |
| `tests/test_feedback.py` | `clean`, `fb` | `tests/search/conftest.py` |
| `tests/test_feedback.py` | `CAP`, `FILES`, `QUESTION`, `WIDGETS`, `hammer`, `make_repo`, `search`, `stored`, `symbols`, `use`, `write` | `tests/search/feedback_helpers.py` |
| `tests/test_feedback.py` | `test_a_cited_use_replaces_an_opened_one_in_the_same_session`, `test_a_name_at_several_paths_needs_a_path`, `test_a_use_of_removed_code_lists_unindexed_and_boosts_nothing`, `test_add_finds_pages_and_refuses_what_it_cannot_place`, `test_add_gives_each_use_its_own_cli_session`, `test_another_session_adds_a_use`, `test_boost_grows_linearly_to_the_cap`, `test_listing_shows_decay_by_weight`, `test_reset_one_repository`, `test_resolve_finds_symbols_and_pages`, `test_two_opened_uses_in_one_session_are_one`, `test_weights_add_up_and_skip_other_repositories`, `test_weights_halve_every_half_life` | `tests/search/test_feedback.py` |
| `tests/test_feedback.py` | `test_a_used_page_is_placed_by_its_boosted_similarity`, `test_a_used_symbol_passes_only_what_is_within_twenty_percent`, `test_every_hit_explains_its_boost`, `test_feedback_adds_no_visible_latency`, `test_feedback_never_adds_a_hit`, `test_identifier_definitions_stay_first`, `test_switching_feedback_off_ranks_as_without_uses`, `test_the_boost_never_passes_the_cap` | `tests/search/test_ranking_feedback.py` |
| `tests/test_feedback.py` | `git` | `tests/support.py` |
| `tests/test_feedback.py` | `ENV` | `tests/wiki/helpers.py` |
| `tests/test_graph.py` | `conn` | `tests/conftest.py (changed: T033)` |
| `tests/test_graph.py` | `csharp`, `defs`, `ext`, `repos`, `us2`, `us4`, `us5` | `tests/graph/conftest.py` |
| `tests/test_graph.py` | `APP`, `CHAIN`, `DEFS`, `EXT`, `GO`, `H`, `OTHER`, `PY`, `TEST`, `edges`, `file_imports`, `imports`, `language_repo`, `make`, `outside`, `rows` | `tests/graph/helpers.py` |
| `tests/test_graph.py` | `test_go_and_javascript_call_resolution`, `test_python_call_resolution`, `test_receivers_are_normalized_to_dotted_names`, `test_self_receivers_include_the_new_languages` | `tests/graph/test_build.py` |
| `tests/test_graph.py` | `test_external_imports_name_what_resolves_to_no_indexed_file`, `test_external_imports_of_the_graph_repositories`, `test_files_carry_their_namespaces`, `test_imports_resolve_within_the_repository`, `test_suffix_index_maps_every_path_suffix` | `tests/graph/test_imports.py` |
| `tests/test_graph.py` | `test_an_include_found_by_path_anywhere_in_the_repository`, `test_csharp_callers_across_projects`, `test_csharp_ingests_as_definitions`, `test_csharp_usings_resolve_through_declared_namespaces`, `test_us2_callers`, `test_us2_imports_resolve`, `test_us2_ingests_as_definitions`, `test_us4_callers`, `test_us4_imports_resolve`, `test_us4_ingests_as_definitions`, `test_us5_callers`, `test_us5_imports_resolve`, `test_us5_ingests_as_definitions` | `tests/graph/test_languages.py` |
| `tests/test_graph.py` | `test_callers_of_a_bare_name_cover_every_definition`, `test_calls`, `test_definitions_bare_name_returns_the_function_and_the_methods`, `test_definitions_cap_at_five_in_repo_path_line_order`, `test_definitions_cut_a_long_source_at_400_lines`, `test_definitions_qualified_name_returns_that_definition_with_its_source`, `test_definitions_refusals`, `test_definitions_repos_limit_the_matches`, `test_depth_out_of_range`, `test_impact_hops`, `test_qualified_name_narrows_to_the_method`, `test_refusals`, `test_repos_limit_every_question` | `tests/graph/test_queries.py` |
| `tests/test_graph.py` | `ENV` | `tests/indexing/helpers.py` |
| `tests/test_graph.py` | `LANGUAGE_FIXTURES` | `tests/wiki/helpers.py` |
| `tests/test_ingest.py` | `conn` | `tests/conftest.py (changed: T033)` |
| `tests/test_ingest.py` | `before_csharp`, `graph_repo`, `repo`, `wiki_repo` | `tests/indexing/conftest.py` |
| `tests/test_ingest.py` | `APP_PY`, `CS`, `DOC_GO`, `DOC_PY`, `ENV`, `LIB_PY`, `MAIN_GO`, `RELATIONS`, `USE_PY`, `WEB_JS`, `assert_matches_full`, `callers_of`, `content`, `docs`, `extract_version`, `forget_graph`, `head`, `named_ids`, `pages_of`, `pkg_module`, `register`, `relations`, `revision`, `stored`, `symbol_ids`, `try_symlink`, `visibility`, `write` | `tests/indexing/helpers.py` |
| `tests/test_ingest.py` | `test_discover_assigns_skip_reasons`, `test_discover_honours_vendor_setting`, `test_git_helper_is_read_only` | `tests/indexing/test_files.py` |
| `tests/test_ingest.py` | `test_concurrent_ingest_refused`, `test_dirty_tree_flagged`, `test_every_symbol_gets_search_text`, `test_failed_ingest_keeps_previous_index`, `test_ingest_summary_and_rows`, `test_ingested_symbols_are_searchable_at_once`, `test_missing_model_changes_nothing`, `test_refuses_non_git_and_empty_repos`, `test_unchanged_reingest_is_current` | `tests/indexing/test_ingest.py` |
| `tests/test_ingest.py` | `test_docs_are_stored_and_follow_edits`, `test_exported_and_namespaces_are_stored_and_stable`, `test_extract_version_1_is_reread_once_without_new_symbols`, `test_failed_reread_keeps_the_old_extract_version`, `test_files_whose_language_gained_rules_are_re_read`, `test_graph_follows_edits_and_deletions`, `test_repository_indexed_before_the_graph_is_reread_without_reembedding`, `test_uses_and_facts_of_the_old_windows_end_like_removed_code` | `tests/indexing/test_ingest_extraction.py` |
| `tests/test_ingest.py` | `test_change_reverted_in_a_later_commit_is_unchanged`, `test_deleted_and_newly_skipped_files_leave_the_index`, `test_edited_file_keeps_its_unchanged_symbols`, `test_full_rebuild_on_up_to_date_repository`, `test_only_changed_files_are_reprocessed`, `test_uncommitted_edit_at_same_head_is_indexed`, `test_unknown_revision_rebuilds_in_full` | `tests/indexing/test_ingest_incremental.py` |
| `tests/test_ingest.py` | `test_editing_a_cited_function_marks_and_recompiles_its_page`, `test_failed_recompile_keeps_the_ingestion`, `test_full_reingest_marks_and_recompiles_every_page`, `test_uncited_change_and_no_change_mark_nothing`, `test_without_a_wiki_nothing_is_created` | `tests/indexing/test_ingest_wiki.py` |
| `tests/test_ingest.py` | `git` | `tests/support.py` |
| `tests/test_languages.py` | `FIXTURES`, `calls`, `definitions`, `docs`, `parsed` | `tests/parsing/languages/helpers.py` |
| `tests/test_languages.py` | `test_a_header_is_read_as_cpp`, `test_c_definitions_calls_and_includes`, `test_cpp_calls_and_includes`, `test_cpp_classes_out_of_class_definitions_and_templates` | `tests/parsing/languages/test_c_family.py` |
| `tests/test_languages.py` | `test_csharp_call_forms`, `test_csharp_calls`, `test_csharp_definitions_kinds_and_visibility`, `test_csharp_file_that_does_not_parse`, `test_csharp_files`, `test_csharp_usings_and_namespaces`, `test_csharp_xml_docs` | `tests/parsing/languages/test_csharp.py` |
| `tests/test_languages.py` | `ORDER_JAVA`, `test_java_definitions_docs_calls_and_imports` | `tests/parsing/languages/test_java.py` |
| `tests/test_languages.py` | `test_kotlin_definitions_docs_calls_and_imports` | `tests/parsing/languages/test_kotlin.py` |
| `tests/test_languages.py` | `test_php_definitions_docs_calls_and_imports` | `tests/parsing/languages/test_php.py` |
| `tests/test_languages.py` | `test_ruby_definitions_docs_calls_and_imports`, `test_ruby_private_by_name` | `tests/parsing/languages/test_ruby.py` |
| `tests/test_languages.py` | `test_rust_definitions_docs_calls_and_imports`, `test_rust_impl_names_drop_generics` | `tests/parsing/languages/test_rust.py` |
| `tests/test_languages.py` | `test_swift_definitions_docs_calls_and_imports` | `tests/parsing/languages/test_swift.py` |
| `tests/test_languages.py` | `test_tsx_components`, `test_typescript_calls_and_imports`, `test_typescript_definitions_kinds_and_visibility` | `tests/parsing/languages/test_typescript.py` |
| `tests/test_languages.py` | `test_a_directive_on_the_last_line_without_a_newline_parses` | `tests/parsing/test_chunks.py` |
| `tests/test_languages.py` | `test_us2_files`, `test_us2_files_that_do_not_parse`, `test_us4_files`, `test_us4_files_that_do_not_parse`, `test_us5_files`, `test_us5_files_that_do_not_parse` | `tests/parsing/test_languages.py` |
| `tests/test_memory.py` | `conn` | `tests/conftest.py (changed: T033)` |
| `tests/test_memory.py` | `ready`, `repo` | `tests/memory/conftest.py` |
| `tests/test_memory.py` | `FILES`, `FORBIDDEN`, `FakeLlm`, `HIT`, `OTHER`, `a_use`, `change`, `facts_of`, `fields`, `hit`, `make_repo`, `pending_runs`, `run_count`, `seed`, `synthetic`, `uses_of`, `with_model` | `tests/memory/helpers.py` |
| `tests/test_memory.py` | `ask` | `tests/memory/helpers.py (changed: finds the tool by name in the server's tool registry (app.mcp) instead of on the old server module)` |
| `tests/test_memory.py` | `test_a_thousand_runs_consolidate_within_a_minute`, `test_a_wording_that_moves_weakens_the_old_fact_and_links_them`, `test_an_aspect_that_changes_value_is_a_contradiction`, `test_confidence_rises_with_agreeing_runs`, `test_consolidation_is_idempotent_and_skips_counted_runs`, `test_consolidation_logs_counts_never_text`, `test_near_identical_questions_merge_into_one_fact`, `test_the_same_words_to_another_tool_are_not_a_contradiction`, `test_two_consolidations_at_once_count_each_run_once` | `tests/memory/test_consolidate.py` |
| `tests/test_memory.py` | `test_model_failure_falls_back_to_the_template`, `test_model_text_naming_unknown_code_is_rejected`, `test_model_writes_the_text_from_exactly_the_documented_inputs`, `test_names_from_the_source_sent_are_allowed_and_prose_is_not_a_name`, `test_the_model_never_decides_subject_runs_or_confidence`, `test_unknown_names` | `tests/memory/test_distill.py` |
| `tests/test_memory.py` | `test_a_run_over_two_repositories_gives_each_its_own_top`, `test_graph_and_symbol_findings`, `test_page_finding_from_read_wiki`, `test_runs_that_give_no_finding`, `test_search_hit_finding_is_about_the_top_symbol` | `tests/memory/test_findings.py` |
| `tests/test_memory.py` | `test_a_fact_hit_run_confirms_its_fact`, `test_fact_hits_follow_filters_and_skip_stale`, `test_forget_removes_only_that_repository`, `test_fresh_facts_are_search_hits_below_definitions`, `test_recall_by_topic_puts_the_related_fact_first`, `test_recall_size_does_not_grow_with_the_log`, `test_recall_unknown_repository`, `test_recall_without_a_repository_covers_every_one`, `test_recall_without_topic_is_fresh_then_confident`, `test_runs_only_a_removed_repository_held_go_with_it` | `tests/memory/test_recall.py` |
| `tests/test_memory.py` | `test_search_without_facts_never_loads_the_package` | `tests/memory/test_recall.py (changed: its code string searches through golestan_code_mcp.search.query, the new home of semantic.search)` |
| `tests/test_memory.py` | `test_a_consolidation_failure_never_undoes_the_ingestion`, `test_edited_code_answered_by_other_code_goes_stale`, `test_edited_code_answered_the_same_way_stays_fresh`, `test_every_ingestion_consolidates_even_when_current`, `test_moved_code_is_repointed_without_a_re_ask`, `test_removed_code_makes_its_fact_stale_and_halves_it`, `test_stale_facts_wait_for_a_run_and_consolidation_is_idempotent` | `tests/memory/test_recheck.py` |
| `tests/test_memory.py` | `test_a_failing_use_is_logged_and_the_writer_goes_on`, `test_a_use_queued_after_its_run_is_linked_to_it`, `test_a_use_whose_run_was_never_written_is_unlinked`, `test_graph_runs_keep_their_columns`, `test_list_repositories_and_failures`, `test_mark_used_makes_no_fact`, `test_repositories_come_from_results_without_a_repo_argument`, `test_runs_list_their_used_results_in_result_order`, `test_search_run_keeps_locations_not_snippets`, `test_store_runs_gives_each_run_its_id`, `test_symbol_run_drops_source`, `test_wiki_page_is_one_row_and_list_is_pages` | `tests/memory/test_runs.py` |
| `tests/test_memory.py` | `test_client_requires_the_migrated_store`, `test_client_writes_reads_and_searches_facts`, `test_configured_model_gets_a_package_llm`, `test_no_model_configured_means_no_llm` | `tests/memory/test_store.py` |
| `tests/test_memory.py` | `test_importing_memory_does_not_import_the_package` | `tests/memory/test_store.py (changed: imports memory's modules by their new paths; importing the memory package alone now loads only its docstring)` |
| `tests/test_memory.py` | `WIDGETS` | `tests/search/feedback_helpers.py` |
| `tests/test_memory.py` | `commit`, `git`, `write` | `tests/support.py` |
| `tests/test_memory.py` | `ENV` | `tests/wiki/helpers.py` |
| `tests/test_registry.py` | `conn` | `tests/conftest.py (changed: T033)` |
| `tests/test_registry.py` | `name`, `repo_count`, `test_add_stores_absolute_path`, `test_get_repo`, `test_get_repo_deleted_directory`, `test_get_repo_unknown_name`, `test_invalid_names`, `test_list_sorted_with_counts`, `test_refusals_record_nothing`, `test_resolve_dir_expands_and_resolves`, `test_resolve_dir_refuses_missing_and_files`, `test_valid_names` | `tests/test_registry.py` |
| `tests/test_samples.py` | `git`, `origin`, `test_clone_then_present`, `test_failed_clone_names_repo`, `test_main_exit_codes`, `test_non_git_folder_is_an_error`, `test_pinned_urls`, `test_refuses_folder_inside_project` | `tests/test_samples.py` |
| `tests/test_schema.py` | `conn` | `tests/conftest.py (changed: T033)` |
| `tests/test_schema.py` | `repo_id` | `tests/schema/conftest.py` |
| `tests/test_schema.py` | `GRAPH_TABLES`, `MEMORY_TABLES`, `SHA`, `TABLES`, `WIKI_TABLES`, `add_citation`, `add_file`, `add_page`, `add_run`, `add_symbol`, `add_use`, `columns_of`, `counts`, `insert` | `tests/schema/helpers.py` |
| `tests/test_schema.py` | `test_backfill_fills_search_text`, `test_bad_repo_name_rejected`, `test_bad_symbol_rejected`, `test_commit_sha_accepts_sha1_and_sha256`, `test_commit_sha_rejects_bad_values`, `test_delete_cascades`, `test_exported_backfill_follows_the_name_rule`, `test_file_path_unique_per_repo`, `test_indexed_commit_accepts_null_sha1_sha256`, `test_indexed_commit_rejects_bad_values`, `test_language_coverage_columns`, `test_migrate_three_times_changes_nothing`, `test_repo_indexed_revision_columns`, `test_schema_version_is_ten`, `test_tables_exist_and_version_recorded` | `tests/schema/test_core.py` |
| `tests/test_schema.py` | `test_call_ref_form_rejects_other_values`, `test_code_graph_tables_and_extract_version`, `test_file_delete_cascades_refs_and_edges`, `test_graph_one_hop_calls`, `test_import_pair_unique` | `tests/schema/test_graph.py` |
| `tests/test_schema.py` | `test_agent_memory_tables_and_package_schema`, `test_memory_run_and_repo_delete_cascade_links`, `test_memory_run_defaults_and_status_check`, `test_usage_feedback_table`, `test_use_how_check_and_default_time`, `test_uses_go_with_their_repository_and_outlive_their_run` | `tests/schema/test_memory.py` |
| `tests/test_schema.py` | `test_module_wiki_columns_and_tables`, `test_wiki_citation_keys_set_null_on_delete`, `test_wiki_citation_rejects_bad_role_and_key_with_file`, `test_wiki_page_accepts_good_row`, `test_wiki_page_and_repo_delete_cascade`, `test_wiki_page_directory_and_name_unique_per_repo`, `test_wiki_page_rejects_bad_values` | `tests/schema/test_wiki.py` |
| `tests/test_semantic.py` | `conn` | `tests/conftest.py (changed: T033)` |
| `tests/test_semantic.py` | `ledger`, `repos` | `tests/search/conftest.py` |
| `tests/test_semantic.py` | `A`, `B`, `C`, `D`, `LANGUAGE_LIST`, `LEDGER_SYMBOLS`, `LEDGER_TEXT`, `LITERALS`, `RUN`, `SYMBOLS`, `TOKEN`, `add_symbol`, `hit`, `in_language`, `names`, `opening` | `tests/search/helpers.py` |
| `tests/test_semantic.py` | `test_hybrid_keyword_side_accepts_any_word`, `test_operator_words_stay_literal`, `test_special_characters_are_literal`, `test_text_query_escapes_every_word` | `tests/search/test_candidates.py` |
| `tests/test_semantic.py` | `test_failed_download_names_the_url_and_leaves_nothing`, `test_hybrid_index_is_set_up`, `test_load_model_again_changes_nothing`, `test_load_model_keeps_the_page_index`, `test_require_model_names_the_setup_command` | `tests/search/test_model.py` |
| `tests/test_semantic.py` | `test_case_does_not_matter`, `test_definitions_rank_above_call_sites`, `test_empty_question_refused`, `test_fresh_commit_is_searchable_at_once`, `test_hybrid_results_explain_their_rank`, `test_languages_are_the_chunkers_plus_text`, `test_limit_inside_1_to_50_accepted`, `test_limit_outside_1_to_50_refused`, `test_no_boost_without_a_definition`, `test_qualified_name_ranks_that_method_first`, `test_question_then_limit_then_language_checked`, `test_repository_scoping`, `test_text_mode_needs_every_word`, `test_unknown_language_refused_before_connecting`, `test_unknown_mode_refused_before_searching`, `test_unknown_repo_refused`, `test_vector_mode_ranks_by_meaning_above_the_floor` | `tests/search/test_query.py` |
| `tests/test_semantic.py` | `test_defaults_give_the_same_hits_as_before`, `test_every_hit_has_its_language_and_opening_snippet`, `test_language_keeps_only_that_language`, `test_limit_caps_the_hits`, `test_repo_and_language_still_fill_limit` | `tests/search/test_query_filters.py` |
| `tests/test_semantic.py` | `test_a_module_question_puts_its_page_first`, `test_a_named_module_page_ranks_first_after_definitions`, `test_a_page_hit_has_its_directory_no_lines_and_its_state`, `test_a_page_without_similarity_goes_last`, `test_a_question_names_a_module_only_with_module_words`, `test_a_stale_page_is_found_as_stale`, `test_an_unrelated_question_finds_no_page`, `test_identifier_definitions_stay_above_pages`, `test_pages_go_above_the_first_hit_they_beat_on_similarity`, `test_repo_and_language_filters_apply_to_pages`, `test_symbol_hits_have_no_state`, `test_without_the_page_index_search_returns_symbols_only` | `tests/search/test_ranking.py` |
| `tests/test_server.py` | `fresh_session`, `pages`, `recorded`, `used_repo` | `tests/server/conftest.py` |
| `tests/test_server.py` | `CALLS`, `CLIENT`, `CONTRACT`, `CORE`, `FACT_SENTENCE`, `FEEDBACK_CONTRACT`, `GRAPH_CALLS`, `LANGUAGE_CONTRACT`, `MARK`, `MEMORY_CONTRACT`, `PKG`, `SPECS`, `TOOLS`, `UNREACHABLE`, `WIKI_CONTRACT`, `_session`, `as_client`, `call`, `contract`, `core`, `definitions`, `instructions`, `listed`, `newest_run`, `raw_call`, `ready`, `runs_since`, `search_hit`, `uses`, `wiki_repo` | `tests/server/helpers.py` |
| `tests/test_server.py` | `test_each_tool_call_is_logged`, `test_every_tool_call_is_one_run`, `test_lists_the_nine_tools_as_the_contract_describes_them`, `test_missing_password_named`, `test_next_call_after_an_outage_succeeds`, `test_recording_adds_no_visible_delay`, `test_recording_failure_leaves_the_answer_alone`, `test_refused_calls_are_recorded_unavailable`, `test_server_instructions_match_the_contract`, `test_tool_log_record_is_unchanged`, `test_unknown_arguments_are_refused`, `test_unreachable_is_a_result` | `tests/server/test_app.py` |
| `tests/test_server.py` | `test_graph_input_refused_before_connecting`, `test_graph_refusals_are_results`, `test_graph_results_are_capped`, `test_graph_tools_match_core` | `tests/server/test_graph_tools.py` |
| `tests/test_server.py` | `test_a_use_recording_failure_leaves_the_answer_alone`, `test_mark_used_after_a_search_is_linked`, `test_mark_used_on_nothing_records_nothing`, `test_mark_used_unknown_repository`, `test_mark_used_without_a_search_is_unlinked`, `test_opened_then_cited_is_one_cited_use`, `test_reading_a_returned_hit_is_an_opened_use`, `test_reading_without_a_search_is_not_a_use`, `test_recall_database_down`, `test_recall_matches_core_and_shape`, `test_recall_refuses_bad_input_before_connecting`, `test_recall_unknown_repository` | `tests/server/test_memory_tools.py` |
| `tests/test_server.py` | `test_list_repositories_matches_registry`, `test_list_repositories_unreachable_is_a_result` | `tests/server/test_repository_tools.py` |
| `tests/test_server.py` | `test_an_unknown_language_lists_the_new_ones`, `test_get_symbol_matches_core`, `test_get_symbol_refusals_are_results`, `test_search_code_finds_csharp_definitions_as_the_core_does`, `test_search_code_hits_can_be_pages`, `test_search_code_input_refused_before_connecting`, `test_search_code_matches_core`, `test_search_code_unknown_repository_is_a_result`, `test_search_hits_carry_relevance_and_feedback`, `test_search_with_feedback_off_matches_the_core` | `tests/server/test_search_tools.py` |
| `tests/test_server.py` | `test_read_wiki_ambiguous_name_asks_for_repo`, `test_read_wiki_empty_page_refused_before_connecting`, `test_read_wiki_list_is_capped`, `test_read_wiki_lists_the_pages`, `test_read_wiki_matches_core`, `test_read_wiki_refusals_are_results` | `tests/server/test_wiki_tools.py` |
| `tests/test_wiki.py` | `conn` | `tests/conftest.py (changed: T033)` |
| `tests/test_wiki.py` | `commit`, `git`, `write` | `tests/support.py` |
| `tests/test_wiki.py` | `built`, `fresh` | `tests/wiki/conftest.py` |
| `tests/test_wiki.py` | `CORE_PY`, `ENV`, `FILES`, `LANGUAGE_FIXTURES`, `SERVER_GO`, `TESTS_PY`, `citation_rows`, `execute`, `functions`, `language_wiki`, `lob`, `make_repo`, `mark`, `module_name`, `page_of`, `page_rows`, `rid`, `symbol_of`, `text` | `tests/wiki/helpers.py` |
| `tests/test_wiki.py` | `test_a_rewritten_symbol_is_reported_as_changed`, `test_build_logs_one_record_per_repository`, `test_failed_refresh_leaves_pages_stale`, `test_first_build_counts_and_sets_wiki_at`, `test_mark_stale_names_the_changed_or_gone_symbol`, `test_page_index_exists_after_a_build`, `test_refresh_recompiles_adds_and_removes`, `test_repository_without_a_wiki_is_untouched`, `test_second_build_is_idempotent_and_keeps_search_text`, `test_unknown_and_unindexed_repositories_refused` | `tests/wiki/test_build.py` |
| `tests/test_wiki.py` | `test_citations_record_commit_and_hash_and_read_back_current_locations`, `test_every_named_symbol_and_module_is_cited`, `test_go_page`, `test_key_symbols_at_most_ten_ranked_by_outside_callers`, `test_key_symbols_rank_by_the_stored_exported_flag`, `test_no_path_or_line_number_in_any_page`, `test_one_page_per_directory_of_ten_named_definitions`, `test_purpose_falls_back_to_types_then_to_the_stated_sentence`, `test_structure_purpose_and_sections` | `tests/wiki/test_compile.py` |
| `tests/test_wiki.py` | `test_a_csharp_directory_page`, `test_a_kotlin_directory_page`, `test_a_typescript_directory_page`, `test_every_language_with_rules_has_a_plain_name`, `test_us2_test_files_rank_last`, `test_us4_test_files_rank_last`, `test_us5_test_files_rank_last` | `tests/wiki/test_compile_languages.py` |
| `tests/test_wiki.py` | `test_pages_and_read_follow_the_contract`, `test_read_refuses_unknown_and_ambiguous_pages` | `tests/wiki/test_read.py` |

### Shared setup (T033)

- **`conn`.** The copies that were the same became one `conn` in tests/conftest.py. It skips without the database,
  and, in a file marked `pytestmark = pytest.mark.needs_model`, without the embedding model. At a file's end it
  removes the `t-` repositories (the graph, ingest and wiki copies did; the memory, schema and registry files now do
  too, which only cleans up rows they made). The marker is on every graph, indexing, wiki and search test file. The
  evaluation's `conn` differs (it needs flask and gin indexed) and stays in tests/search/test_evaluation.py.
- **`git`, `write`, `commit`.** The identical copies are in tests/support.py. tests/test_samples.py keeps its own
  `git`, which runs without the test identity.
- **Helpers and fixtures of one folder** are in its `helpers.py` and `conftest.py`. The search folder has two helper
  modules, because the usage feedback tests and the search tests each defined a `QUESTION`.

### Test edits during US2

| Where | Change | Why |
|---|---|---|
| `FIXTURES`, `LANGUAGE_FIXTURES`, `SPECS`, `GOLD`, the C# fixture copy | `Path(__file__).parent` became `.resolve().parents[1]` or `[2]` | the files are one or two folders deeper |
| tests/schema/ | the schema tests are a folder | split by the tables they cover, with shared inserts and a fixture |
| pyproject.toml | `--import-mode=importlib`, `pythonpath = ["tests"]`, the `needs_model` marker | research R11 |

### Test edits during US1

US1 retargets imports and `monkeypatch.setattr` targets in the existing test files (tasks.md, Rules). These test
bodies needed more than that, and are listed in `movecheck.py`'s `EXPECTED`:

| Test | Change | Why |
|---|---|---|
| `test_chunker.py::test_new_grammars_load_only_when_used` | its code string imports `golestan_code_mcp.parsing.chunks` and `golestan_code_mcp.indexing.ingest` | the modules it named are gone |
| `test_memory.py::test_importing_memory_does_not_import_the_package` | its code string imports memory's modules by their new paths | importing the `memory` package alone loads only its docstring |
| `test_memory.py::ask` | finds a tool in the server's registry, `app.mcp._tool_manager.get_tool(tool).fn` | the tools are in five files; this is the same function object |
| `test_graph.py::test_refusals` | `getattr(queries, question)` | the graph queries are in `graph/queries.py` |
| `test_semantic.py` (two tests) | `oracledb.DB_TYPE_CLOB` | they read `oracledb` through `semantic`'s import of it |

## Cross-file private names

Underscore names another file now uses (research R8), by the file that defines them. They keep their
names so the move check can match them; dropping the underscore is a clean-up for a later change.

- `cli/index_commands.py`: `_db_migrate`, `_ingest`, `_model_load`, `_repo_add`, `_repo_list`, `_stats`, `_symbols`
- `cli/memory_commands.py`: `_feedback_add`, `_feedback_list`, `_feedback_reset`, `_memory_consolidate`, `_memory_facts`, `_memory_list`
- `cli/search_commands.py`: `_callers`, `_calls`, `_eval`, `_impact`, `_percent`, `_repos`, `_search`
- `cli/wiki_commands.py`: `_top`, `_when`, `_wiki_build`, `_wiki_citations`, `_wiki_list`, `_wiki_show`
- `graph/imports.py`: `_files`, `_import_refs`, `_imports`, `_normalize`
- `indexing/files.py`: `_ls`, `_paths`
- `indexing/ingest.py`: `_candidates`
- `indexing/write.py`: `_sha`, `_write`
- `memory/distill.py`: `_Fact`, `_contradict`, `_distill`, `_plural`
- `memory/findings.py`: `_json`, `_key`, `_page`, `_plain`, `_ref`, `_symbol`
- `memory/recheck.py`: `_definitions`
- `parsing/common.py`: `_above`, `_block_doc`, `_c_receiver`, `_child`, `_clean`, `_comments_above`, `_definition`, `_docstring`, `_dotted`, `_modifiers`, `_name`, `_named`, `_public`, `_text`, `_uncomment`, `_until_tag`, `_walk_calls`
- `parsing/languages/javascript.py`: `_js_doc`, `_js_imports`
- `search/candidates.py`: `_page_candidates`
- `search/model.py`: `_ensure_lexer`, `_state`
- `search/ranking.py`: `_boost`, `_boosts`, `_fuse`, `_place`
- `server/app.py`: `_answer`, `_logged`, `_returned`, `_use`
- `server/wiki_tools.py`: `_iso`
- `wiki/compile.py`: `_Draft`, `_compile`
- `wiki/read.py`: `_summary`
- `wiki/store.py`: `_apply`, `_lob`, `_repo`, `_stored`
- `wiki/text.py`: `_and`, `_sentences`, `_ticked`

87 names in 22 files.

## Bugs found, not fixed

Behavior is frozen (spec, Assumptions), so these are listed, not changed.

1. **Same-named definitions get an arbitrary caller.** When a file defines two symbols of one name, which of them a
   call's caller id, or a wiki citation, points to varies between ingests of the same code. Example: flask's typing
   overloads of `App.template_filter` (lines 666 and 670 of `sansio/app.py`). Found because two baseline runs of
   master differed. The baseline leaves those line columns out.
2. **`import golestan_code_mcp.languages` alone failed on master.** languages.py imported chunker.py, which imported
   languages.py back at its end, before languages.py had defined its tables. Nothing imported languages.py first, so
   it never showed. The split removes it: `parsing/tables.py` defines `register()` before it loads the language
   files.
3. **`test_search_code_matches_core` depends on the database's feedback state.** It compares a direct search with
   the `search_code` tool's answer, both with usage feedback on. When the real flask repository has recorded uses,
   their weight decays between the two calls, so the scores differ in the last digits. It failed on master too
   (T002) for two of its four cases, and on the branch for one or two, depending on the run.
4. **`test_recording_adds_no_visible_delay` is a timing test.** It failed once on the branch while the machine was
   busy (100 ms with recording against 81 ms without), and passed when run again alone. The recording code moved
   unchanged.

## Baseline noise

What two runs of master on the same database disagreed on (T006), and how the comparison handles it:

- **Search scores shift after an ingest.** The rows step ingests a repository, which changes the text index's
  statistics, so a search run afterwards can score one point lower and reorder near-ties. The comparison runs the
  search steps of master and the branch back to back, and the rows step after both (baseline.py docstring).
- **Timings.** Durations in the CLI's text and the `seconds` and `ms` fields of the JSON log records are masked.
- **Callers of same-named definitions.** See bug 1: `caller_line` in call refs and calls, and `symbol_line` in
  wiki citations, are left out.

After these, two runs of master gave `no differences`.

**Master's own suite.** 684 passed and 2 failed in 11 min 36 s (T002). The two failures,
`test_server.py::test_search_code_matches_core[arguments0]` and `[arguments3]`, are from the database's state: the
real flask repository has usage feedback, and its boost changes between the test's direct search and its tool call.

## Verified

On 2026-10-16, against master at 43a3c3e, on the Rancher Desktop database with flask, gin and selenium-e2e indexed.

| Check | Result |
|---|---|
| Layout (`tests/test_layout.py`) | 309 passed: every source and test file at most 300 lines, with a docstring, and in the README's Layout |
| Move check, source (`movecheck.py`) | `0 missing, 0 changed, 0 duplicated` over 554 definitions, apart from `EXPECTED` |
| Move check, tests (`movecheck.py --tests`) | `0 missing, 0 changed, 0 duplicated`; 686 tests besides the layout ones, as on master |
| Each module alone (`movecheck.py --imports`) | 67 modules imported alone, 0 failed |
| Installed commands | `[project.scripts]` unchanged; `ccctx.exe --help` works without `uv sync`; `python -m golestan_code_mcp.cli` and `.server` start |
| Behavior (`baseline.py`, master then branch, back to back) | no differences: tool listing, language tables, 149 `ccctx` commands with `eval`, parse output of 538 files, stored rows after `ingest --full` and `wiki build` |
| Full suite, random order (`pytest-randomly`) | 993 passed, 2 failed in 10 min 36 s, against master's 684 passed, 2 failed in 11 min 36 s (T002). The 2 are `test_search_code_matches_core`, which fails on master too (Bugs found, 3) |
| Each test file alone | 64 of 64 files passed, apart from that same test's `[arguments3]` case |

The source went from 16 files (longest 916 lines) to 69 (longest 291, `schema.py`, which did not move), and the
tests from 17 files (longest 930 lines) to 85 (longest 290).
