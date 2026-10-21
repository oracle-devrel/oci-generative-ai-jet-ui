required = ("agent_conn", "agent_turn", "chat", "retrieve_knowledge", "retrieve_tools",
            "tool_run_sql", "write_facts", "Fact", "TOOLS")
missing = [name for name in required if name not in globals()]
assert not missing, f"❌ Part 6 needs {', '.join(missing)}. Finish the TODOs above first."

from workshop.triage import ensure_ledger, alert_queue, print_queue

ALERT_LOOKBACK_DAYS = 30     # how far back "incoming" reaches
TRIAGE_LIMIT        = 3      # alerts to work now; raise after the first pass
IGNORE_WATERMARK    = True   # False: only alerts newer than the last triage run

ensure_ledger(agent_conn)    # AGENT.AML_TRIAGE: one row per customer and typology
_queue = alert_queue(agent_conn, ALERT_LOOKBACK_DAYS, IGNORE_WATERMARK)
print_queue(_queue, TRIAGE_LIMIT, ALERT_LOOKBACK_DAYS)
