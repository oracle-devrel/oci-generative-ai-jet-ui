# Part 4: DBFS Scratchpad

[Oracle DBFS (Database File System)](https://docs.oracle.com/en/database/oracle/oracle-database/26/adlob/database-filesystem-DBFS-intro.html) is a POSIX-like filesystem layered on SecureFile LOBs in a table. The agent sees files and directories; the database sees rows. Same backups, same audit, same security model as everything else in the harness — but with `open()`/`read()`/`write()` ergonomics.

## What's pre-built

The Codespace ran `app/scripts/bootstrap.py`, which provisions:

- A tablespace `AGENT_DBFS_TS` with a dedicated datafile.
- A DBFS store `AGENT_SCRATCH` (`DBMS_DBFS_SFS.CREATEFILESYSTEM` + `DBMS_DBFS_CONTENT.REGISTERSTORE`).
- A mount at `/scratch` (`DBMS_DBFS_CONTENT.MOUNTSTORE`).
- All required grants (`EXECUTE ON DBMS_DBFS_CONTENT`, `EXECUTE ON DBMS_DBFS_SFS`, `DBFS_ROLE`).

You don't run any DDL in this Part. The notebook just wraps the PL/SQL `PUTPATH` / `GETPATH` calls behind a Python class so the rest of the harness can use `read` / `write` / `append` semantics.

## Why a filesystem at all?

Three reasons:

1. **Mid-task scratch.** "Write a SQL draft, read it back, edit, run it" is a filesystem workload, not OLTP.
2. **Path-addressable handles.** Tools can pass `/scratch/draft.sql` between calls without serializing a row id.
3. **Cheap rewrite.** Overwriting a CLOB row works but isn't idiomatic; DBFS gives you file semantics directly.

We use DBFS only as the agent's scratchpad — the long-term, search-heavy data stays in Part 2's OAMP tables.

## The `DBFS` Python wrapper

Minimal file-like wrapper. Only the methods the agent uses:

| Method | What it does | Use when |
|---|---|---|
| `write(path, content)` | Create-or-overwrite the file at `path`. | SQL drafts, plan revisions — *"latest is the truth"* |
| `append(path, content)` | Append to `path`, create if missing. | Running findings logs, transcripts |
| `read(path)` | Read the bytes back as a string. | Reading scratch before passing to `run_sql` |
| `list(path)` | Enumerate files under `path`. | Inspecting state |

The agent uses these via three pre-registered tools: `scratch_write`, `scratch_append`, `scratch_read`.

## Why not just use the kernel's `/tmp`?

Because we want the scratchpad to live inside the database:

- It survives container rebuilds (as long as the datafile survives).
- It's inside the same transactional boundary as OAMP's memory tables.
- In an enterprise deployment it's covered by the same backups, replication, and audit as the rest of the database.

No separate filesystem to secure.

## Key Takeaways — Part 4

- **The scratchpad is a real filesystem.** DBFS persists across tool calls AND across turns on the same thread.
- **`scratch_write` for drafts, `scratch_append` for logs.** Write replaces (SQL drafts, plan revisions); append grows (findings logs, transcripts).
- **BATCH your appends.** One `scratch_append` per row of data is wasteful and burns the iteration budget. Combine many rows into one call.
- **Multi-step reasoning without context bloat.** The agent reasons over a long task by *writing* intermediate state to the scratchpad, not by inflating the prompt.

## Troubleshooting

**`ORA-64001: path not found`** — File doesn't exist. Either `scratch.write` it first or catch `FileNotFoundError`.

**`ORA-22288: file or LOB operation FILEOPEN failed`** — The DBFS store isn't mounted. Re-run `app/scripts/bootstrap.py`.

**`PLS-00306: wrong number or types of arguments in call to PUTPATH`** — Wrong Oracle DBFS version. Ensure you're on Oracle 23ai / 26ai.
