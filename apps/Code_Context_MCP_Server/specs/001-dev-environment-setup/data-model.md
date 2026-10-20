# Data Model: Development Environment Setup

This feature stores almost nothing. Its entities are configuration, a few result shapes that scripts and the `health` tool return, and one smoke table. None of them are domain data for code search; those arrive with the ingestion feature.

## 1. Environment configuration

Loaded once by `config.py` from the process environment, with `.env` at the project root as the fallback source (`python-dotenv`, existing environment wins). Every entry point reads it.

| Field | Env variable | Type | Required | Default | Secret |
|---|---|---|---|---|---|
| db_user | `DB_USER` | string | yes | none | no |
| db_password | `DB_PASSWORD` | string | yes | none | **yes** |
| db_host | `DB_HOST` | string | no | `localhost` | no |
| db_port | `DB_PORT` | int | no | `1521` | no |
| db_service | `DB_SERVICE` | string | no | `FREEPDB1` | no |
| oracle_pwd | `ORACLE_PWD` | string | container only | none | **yes** |
| repos_dir | `CCCTX_REPOS_DIR` | path | no | `../ccctx-repos` (resolved against project root) | no |

`ORACLE_PWD` is read by the container and the startup script `db/startup/01_app_user.sh`, never by the Python package. `DB_PORT` is also the host port Compose publishes, so a port clash is fixed in one place.

**Validation rules**

- A required field that is missing, or present but blank after trimming, fails with a message naming the variable (US1 scenario 3, FR-002). All missing names are reported together, not one per run.
- `DB_PORT` must parse as an integer in 1-65535; the error names `DB_PORT` and echoes the bad value (it is not secret).
- No error message, log line, `repr()` or `str()` of the configuration contains `db_password` or `oracle_pwd`. The redacted form shows `***` (FR-003, SC-007).
- `repos_dir` is resolved to an absolute path. Spaces in the path are allowed (Windows edge case).
- `.env.example` lists every variable above with placeholder values; `.env` is listed in `.gitignore`.

## 2. Sample repository

A third-party project cloned by `golestan-clone-samples`. The set is fixed in `samples.py`; nothing is persisted beyond the clone itself, and the commit is read back from git when needed.

| Field | Type | Notes |
|---|---|---|
| name | string | `flask`, `gin`; also the folder name under `repos_dir` |
| language | enum | `python`, `go` |
| url | string | `https://github.com/pallets/flask.git`, `https://github.com/gin-gonic/gin.git` (verbatim) |
| local_path | path | `repos_dir / name` |
| commit | string | full SHA of `HEAD` after clone, from `git rev-parse HEAD` |

**Validation rules**

- `repos_dir` must not be the project root or any path inside it, compared after resolving both (symlinks and `..` included). Violation exits non-zero before any clone (FR-007).
- A `local_path` that exists and is a git work tree counts as present. A `local_path` that exists but is not a git work tree is an error naming the folder; the cloner does not overwrite it.
- The cloner never imports, executes or installs anything from a cloned repository (constitution VII).

**State transitions (per repository, per run)**

```text
absent  --clone ok-->     cloned   (reports name + commit)
absent  --clone fails-->  failed   (exits non-zero, names the repository)
present --no action-->    skipped  (prints `present <name> <commit>`, no network)
```

`repos_dir` is created when absent. A run exits zero only if every repository ends `cloned` or `skipped` (SC-006).

## 3. Database check result

Returned by `db.check()` and printed by `golestan-check-db`.

| Field | Type | Notes |
|---|---|---|
| ok | bool | true only when login and the vector check both pass |
| version | string or null | database version banner from `v$version` or `oracledb` connection `version` |
| vector_ok | bool | `SELECT VECTOR_DIMENSION_COUNT(TO_VECTOR('[1,2,3]')) FROM dual` returned 3 |
| smoke_rows | int or null | row count of `ccctx_smoke`, null when the table does not exist yet |
| reason | string or null | set when `ok` is false; never contains a secret |

**Waiting behaviour**: on first start the check retries the connection until a bounded deadline. Outcomes:

```text
connecting --login + vector ok-->         ok
connecting --listener up, PDB not open--> retry until deadline --> "still starting"
connecting --refused / timeout-->         retry until deadline --> "unreachable: <reason>"
connecting --auth error-->                fail at once (no retry)  --> "login failed for <DB_USER>"
```

## 4. Health result

The structured output of the MCP `health` tool (FR-008, FR-009). Full contract in `contracts/health-tool.md`.

| Field | Type | Notes |
|---|---|---|
| server | string | always `golestan_code_mcp` |
| version | string | `golestan_code_mcp.__version__` |
| database | enum | `reachable` or `unreachable` |
| reason | string or null | null when reachable; short cause when unreachable (e.g. `connection refused`, `timeout`, `missing setting DB_PASSWORD`) |

**Validation rules**

- The tool takes no input; its input schema is an empty object.
- An unreachable database, a connect timeout or a configuration error all produce a normal result with `database: "unreachable"`, never an MCP error.
- The answer arrives within 5 s with the database down (3 s connect timeout plus overhead). The tool does not use the check's retry loop.
- `reason` never contains a secret.

## 5. Smoke table `ccctx_smoke`

The only database object this feature creates, in the application user's schema. It exists to prove persistence across restarts (SC-003).

| Column | Type | Constraint |
|---|---|---|
| id | `NUMBER GENERATED ALWAYS AS IDENTITY` | primary key |
| created_at | `TIMESTAMP` | `DEFAULT SYSTIMESTAMP NOT NULL` |

Created by `test_db.py` when missing; each run inserts one row. The row count only grows, so a count after restart that is at least the count before it shows the volume kept the data.

## 6. Parsed symbol (test-only)

What the parser smoke test extracts from each fixture; it lives only in `test_parser.py` until the ingestion feature adds an extraction module.

| Field | Type | Notes |
|---|---|---|
| name | string | function, class or type name |
| kind | enum | Python: `function`, `class`; Go: `function`, `method`, `type` |
| start_line | int | 1-based, from the node's start point |
| end_line | int | 1-based, inclusive, `end_line >= start_line` |

Only top-level definitions are counted (plus Go methods, which are top-level in Go). The test asserts the exact expected set per fixture (SC-004). A missing grammar fails with the grammar's package name.

## Relationships

```text
Environment configuration
 ├── read by --> Database check result   (db_* fields)
 ├── read by --> Health result           (db_* fields, via the same connect())
 └── read by --> Sample repository       (repos_dir)
Database check result --reports--> ccctx_smoke row count
```
