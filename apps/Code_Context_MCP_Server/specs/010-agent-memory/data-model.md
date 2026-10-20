# Data Model: Agent Memory

Migration 8, `agent memory`, creates everything:
- **Our two run tables**, by SQL.
- **The package's tables**, prefixed `ccctx_mem_`, which hold the facts. A Python step,
  `memory.create_package_schema(conn)`, builds the package client once with `SchemaPolicy.CREATE_IF_NECESSARY`.

At runtime the client uses `SchemaPolicy.REQUIRE_EXISTING`, so a database without migration 8 fails with a clear
error instead of creating tables on the fly.

## `ccctx_memory_runs`: episodic memory, one row per MCP tool call

| Column | Type | Rule |
|---|---|---|
| `id` | number identity, primary key | The run ID |
| `called_at` | timestamp with time zone | Default `systimestamp` |
| `tool` | varchar2(64) | Not null |
| `arguments` | json | Not null, as given |
| `question` | varchar2(1000 char) | The query, name, page or topic argument. Null when the tool has none |
| `client` | varchar2(256) | `name version` from the client's handshake. Null outside a session |
| `status` | varchar2(16) | `ok`, `unavailable` or `error` |
| `reason` | varchar2(1000 char) | The tool's reason when not `ok` |
| `ms` | number | Latency |
| `result_count` | number | Not null, 0 when none |
| `results` | json | Array of result identities (research R3). Never source, snippets or page text |
| `scoped` | boolean | Default false. True once linked to a repository (R12) |

Index: `(called_at)`.

## `ccctx_memory_run_repos`: which repositories a run belongs to

| Column | Type | Rule |
|---|---|---|
| `run_id` | number | References runs, on delete cascade |
| `repo_id` | number | References `ccctx_repos`, on delete cascade |
| `consolidated` | boolean | Default false, not null |

Primary key `(run_id, repo_id)`. Index `(repo_id, consolidated)`.

## Fact: a package `fact` record, one per subject per repository

| Package field | Value |
|---|---|
| `memory_type` | `"fact"` |
| `user_id` | The repository name (the scope) |
| `agent_id` | `"ccctx"` |
| `content` | The fact's text (R6, R13) |
| `status` | `VALID` when fresh, `INVALID` when stale |
| `ttl_days` | `None`: facts never expire |
| `metadata` | The object below, always written whole |

```json
{
  "subject_key": "symbol:src/flask/helpers.py:url_for:function",
  "subject": "url_for", "kind": "function", "language": "python",
  "findings": {
    "defined": {"tool": "get_symbol", "arguments": {"name": "url_for", "repo": "flask"}, "run": 41,
                "path": "src/flask/helpers.py", "definitions": 2},
    "callers": {"tool": "find_callers", "arguments": {"name": "url_for", "repo": "flask"}, "run": 42,
                "count": 12, "names": ["Flask.url_for", "redirect_to_login"]}
  },
  "questions": ["where's url_for defined?", "where is url_for defined"],
  "runs": [40, 41, 42, 44],
  "refs": [{"role": "subject", "kind": "function", "name": "url_for", "path": "src/flask/helpers.py",
            "content_hash": "9f2c..."},
           {"role": "related", "kind": "method", "name": "Flask.url_for", "path": "src/flask/app.py",
            "content_hash": "41ab..."}],
  "agree": 4, "contradict": 0, "confidence": 0.938,
  "state": "fresh", "stale_reason": null,
  "distiller": "template/1", "consolidator": "memory/1.2.0",
  "created_at": "2026-10-12T08:10:00Z", "updated_at": "2026-10-12T08:15:02Z"
}
```

| Rule | Where it is enforced |
|---|---|
| One fact per `(user_id, subject_key)` | `memory.consolidate` looks the subject up before adding |
| `0 <= confidence <= 1`, computed from `agree` and `contradict` | R7, in code |
| `runs`: every ID exists in `ccctx_memory_runs` | Run IDs come only from consolidated links |
| `state` and `status` agree | Both are written by the same update |
| `refs` has exactly one `subject` entry | Written from the subject resolved in R5 |
| `distiller` is `template/1` or `llm:<model>` | R13 |

**Links** (package relations between facts): `contradicts` when a question wording moved from one fact to another
(R7). `autonomous_linking` is always off (R1).

## State transitions

```text
          new finding (first)           code removed, or re-ask answered by another subject (contradict + 1)
 (none) ───────────────────▶ fresh ─────────────────────────────────────────────────────▶ stale
                               ▲  │ code edited or moved, and re-ask answered               │
                               │  └ by the same subject: re-pointed, stays fresh            │
                               └────────────────── new run's finding for its subject ───────┘
```

- **Contradictions**: a contradiction from a new run changes the confidence, not the state. A contradiction from a
  re-ask or from removed code also marks the fact stale.
- **Run links** go from `consolidated = false` to `true` exactly once.
