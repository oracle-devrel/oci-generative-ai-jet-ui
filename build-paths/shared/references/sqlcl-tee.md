# SQLcl-tee — log every SQL the agent runs

The intermediate and advanced tiers fold this in by default after the friction-pass walk found that pairing MCP with SQLcl makes agent SQL inspectable end-to-end. MCP shows the SQL the *agent* emits; SQLcl shows what the *DB* actually did (rows, errors, execution plan).

## Install (Ubuntu 24.04)

```bash
sudo apt-get install -y default-jre-headless unzip
mkdir -p ~/opt
cd ~/opt
curl -fsSLo sqlcl-latest.zip https://download.oracle.com/otn_software/java/sqldeveloper/sqlcl-latest.zip
unzip -q sqlcl-latest.zip
echo 'export PATH="$HOME/opt/sqlcl/bin:$PATH"' >> ~/.bashrc
export PATH="$HOME/opt/sqlcl/bin:$PATH"
sql -V
```

Expected: `SQLcl: Release 26.x.0.0 Production Build: ...`. Tested with 26.1.0.0.

On other platforms: SQLcl is a Java app, so any JRE 11+ works. The zip is the same on macOS / Linux / WSL.

## How the tee works

`shared/snippets/sqlcl_tee.py` ships a `TeedRunSQL(BaseTool)` subclass that wraps your `run_sql` tool. When the agent invokes `run_sql`, the wrapper:

1. Calls the inner tool (the source of truth — its result is what the agent sees).
2. Writes the SQL to `<target>/sql/run_<unix_timestamp>.sql`.
3. Spawns SQLcl in the background via `subprocess.Popen` to run the same SQL with `sql -L -S "$DB_USER/$DB_PASSWORD@$DB_DSN" @sql/run_<ts>.sql > logs/sqlcl_<ts>.log 2>&1`.
4. Appends `[sqlcl_log: logs/sqlcl_<ts>.log]` to the inner tool's result so the streamed response carries the log path.

Cost: zero latency on the response (the SQLcl process is async). One log file per query — inspect with `tail -50 logs/sqlcl_<latest>.log`.

If SQLcl is not installed, the wrapper appends `[sqlcl_tee: skipped — SQLcl not installed]` and the inner tool's result passes through unchanged.

## Wiring (intermediate tier example)

```python
# src/<pkg>/tool_registry.py
from shared.snippets.sqlcl_tee import wrap_with_sqlcl_tee
from .mcp_client import list_tools

_cached: list | None = None

def get_tools():
    global _cached
    if _cached is None:
        tools = list_tools()
        _cached = [
            wrap_with_sqlcl_tee(t, sql_dir="sql", log_dir="logs") if t.name == "run_sql" else t
            for t in tools
        ]
    return _cached
```

## Why this lives in shared/, not in a tier SKILL

The SQLcl tee is useful at every tier where the agent emits SQL. The intermediate tier folds it in by default; the advanced tier mentions it as an optional add-on per project. Anchoring it in `shared/snippets/` lets both reach for the same implementation.
