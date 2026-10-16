"""Preflight: one readable report on whether the Codespace has what the notebook needs."""
import os
import sys
from importlib.metadata import version

import oracledb

FINANCE_TABLES = ("BRANCHES", "CUSTOMERS", "ACCOUNTS", "CARDS", "MERCHANTS",
                  "TRANSACTIONS", "LOANS", "SAR_REPORTS", "SANCTIONS_SCREENINGS",
                  "BENEFICIAL_OWNERS", "WIRE_MESSAGES", "LOGIN_EVENTS",
                  "KYC_DOCUMENTS", "CASE_NOTES", "FX_RATES")
OPS_TABLES = ("sanctions_screenings", "beneficial_owners", "wire_messages",
              "login_events", "kyc_documents", "case_notes", "fx_rates")
SEED_FIX = "cd app && python scripts/bootstrap.py && python scripts/seed.py"
ALERT_QUEUE_SQL = (
    "SELECT COUNT(*) FROM (SELECT a.customer_id, t.flag_reason "
    "  FROM finance.transactions t JOIN finance.accounts a ON a.account_id = t.account_id "
    " WHERE t.status IN ('FLAGGED','BLOCKED') "
    "   AND t.txn_ts >= SYSTIMESTAMP - INTERVAL '30' DAY "
    " GROUP BY a.customer_id, t.flag_reason)")


def _scalar(conn, sql, default=None):
    """Single-value query; returns `default` if the object does not exist yet."""
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()[0]
    except oracledb.DatabaseError:
        return default


def _line(label, ok, detail, fix=""):
    """One report line per section; a failing section adds its fix on a second line."""
    print(f"  {'✅' if ok else '❌'} {label:<14} {detail}")
    if not ok and fix:
        print(f"     ↳ fix: {fix}")
    return ok


def _environment():
    parts = [f"python {sys.version.split()[0]}"]
    for pkg in ("oracledb", "oracleagentmemory", "openai", "numpy", "langchain-oracledb"):
        try:
            parts.append(f"{pkg} {version(pkg)}")
        except Exception:
            parts.append(f"{pkg} (version unknown)")
    _line("environment", True, ", ".join(parts))


def _agent_schema(conn):
    q = lambda sql, d=0: _scalar(conn, sql, d)
    has_table = q("SELECT COUNT(*) FROM user_tables WHERE table_name = 'EDA_ONNX_MEMORY'")
    rows = q("SELECT COUNT(*) FROM eda_onnx_memory") if has_table else 0
    tools, skills = q("SELECT COUNT(*) FROM toolbox", None), q("SELECT COUNT(*) FROM skillbox", None)
    text_idx = q("SELECT COUNT(*) FROM user_indexes WHERE index_name = 'EDA_MEMORY_TEXT_IDX'")
    detail = (f"EDA_ONNX_MEMORY has {rows} memories; toolbox {tools}, skillbox {skills}"
              + ("" if text_idx else "; note: the Oracle Text index is created in Part 3"))
    _line("AGENT schema", tools is not None and skills is not None, detail, SEED_FIX)


def _finance(conn):
    """Prints the FINANCE line. Returns (missing tables, transaction count)."""
    q = lambda sql: _scalar(conn, sql, 0)
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM all_tables WHERE owner = 'FINANCE'")
        present = {r[0] for r in cur.fetchall() if "$" not in r[0]}
    missing = [t for t in FINANCE_TABLES if t not in present]
    txns = q("SELECT COUNT(*) FROM finance.transactions")
    flagged = q("SELECT COUNT(*) FROM finance.transactions "
                "WHERE status IN ('FLAGGED','BLOCKED') AND flag_reason IS NOT NULL")
    sars = q("SELECT COUNT(*) FROM finance.sar_reports")
    alerts = q(ALERT_QUEUE_SQL)
    ops = {t: q(f"SELECT COUNT(*) FROM finance.{t}") for t in OPS_TABLES}
    ok = not missing and txns > 5000 and flagged > 0 and sars > 0 and all(ops.values())
    detail = (f"{len(FINANCE_TABLES) - len(missing)}/{len(FINANCE_TABLES)} required tables; "
              f"{txns} transactions ({flagged} flagged or blocked); {alerts} alerts in the 30-day queue; "
              f"{sars} SAR reports")
    if missing:
        detail += f"; missing {', '.join(missing)}"
    elif not all(ops.values()):
        detail += "; empty: " + ", ".join(t for t, n in ops.items() if not n)
    _line("FINANCE", ok, detail, SEED_FIX)
    return missing, txns


def _models(conn):
    has = lambda name: _scalar(conn, f"SELECT COUNT(*) FROM user_mining_models WHERE model_name = '{name}'", 0)
    embedder = has("ALL_MINILM_L12_V2")
    detail = "embedder ALL_MINILM_L12_V2 (384-dim)" + ("; reranker RERANKER_ONNX" if has("RERANKER_ONNX") else "")
    _line("models", embedder, detail, "cd app && python scripts/bootstrap.py")
    return embedder


def _llm(provider, router):
    lanes = len(router.lanes) if router else int(bool(os.environ.get("OPENAI_API_KEY")))
    unit = "lane(s)" if router else "key(s)"
    _line("chat LLM", lanes, f"{provider}/{os.environ.get('LLM_MODEL')}, {lanes} {unit} ready",
          "add OCI_GENAI_API_KEY as a Codespaces secret and restart, or enter it when the credentials cell asks")


def run_preflight(conn, provider, router=None):
    """Print one readiness line per section. Raises if FINANCE is not seeded or the embedder is missing."""
    _environment()
    _agent_schema(conn)
    missing, txns = _finance(conn)
    embedder = _models(conn)
    _llm(provider, router)
    if missing or not txns:
        raise RuntimeError("FINANCE is not seeded. Fix: " + SEED_FIX)
    if not embedder:
        raise RuntimeError("The in-database embedder is missing. Fix: cd app && python scripts/bootstrap.py")
    print("  ✅ preflight passed")
