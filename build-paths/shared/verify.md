# Verify — the gate every path enforces

Every scaffolded project ships a `verify.py` (from `shared/templates/verify.template.py`). The skill is **not allowed to declare success** until the user runs it and sees `verify: OK (...)`.

This file is the spec.

## What `verify.py` does

1. **Connect.** `oracledb.connect(...)` against `ORACLE_DSN`. Fails fast on the common ORA codes (see `oracledb-python.md`) with a translated message.
2. **Round-trip via `OracleVS`.** Insert one known string, search for it, assert it comes back. This is the canonical "the whole vector stack works" test — it exercises connection, table creation, embedding, vector insert, vector search, and metadata read-back in one call.
3. **Inference smoke (skip if the project doesn't use a chat LLM).** One deterministic call (e.g. "Reply with the single word OK"), assert non-empty response.
4. **Print one line.** Either:
   - `verify: OK (db, vector, inference)`
   - `verify: FAIL (<which step>): <error>`
5. **Exit 0 / 1.** No verbose tracebacks unless `--debug` is passed.

## What it does NOT do

- It does not test any feature beyond connect + round-trip + one inference call. A passing verify means "the wires are connected"; it doesn't mean "the project's logic is right." The user's own code is responsible for that.
- It does not run benchmarks, perf tests, or load tests.
- It does not require network access beyond the local Docker container and (if OCI) the OCI GenAI endpoint. Intentionally hermetic.
- It does not write user data — it uses a dedicated `CYP_VERIFY_SMOKE` table and drops it at the end.

## What advanced verify adds

For the advanced path (DB-as-only-store), the verify expands:

- **Each memory table round-trips.** Conversational, knowledge base, workflow, toolbox, entity, summary — write one, read one, assert match.
- **No non-Oracle state.** The verify greps the project for forbidden imports (`redis`, `psycopg`, `sqlite3`, `chromadb`, `qdrant_client`, `pinecone`) and fails if it finds any. Hard rule from the plan.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | All checks passed. |
| 1 | A check failed. The line on stderr says which one. |
| 2 | Misconfiguration (missing env var, missing dependency). The skill caused this — fix the scaffold, don't loop. |

## When the skill must run verify

The skill prints to the user "let's run verify now" and **invokes `python verify.py` itself** (not asks the user to run it). If it returns non-zero, the skill:
1. Reads stderr.
2. Maps the failure to a known fix from `oracledb-python.md` or `langchain-oracledb.md`.
3. Applies the fix to the project.
4. Re-runs verify.
5. After 3 failed attempts, stops and asks the user.

The skill does NOT mark the project "done" or write the social-share section of the README until verify passes.

## What the user sees on success

```
$ python verify.py
verify: OK (db, vector, inference)
```

That's the unambiguous green light. Post that line in your social copy, screenshot it, whatever — it means the stack genuinely works.
