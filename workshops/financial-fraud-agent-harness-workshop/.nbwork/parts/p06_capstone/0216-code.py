from workshop.triage import meter, record_decision, case_decision_fact, print_ledger, run_queue

chat = meter(chat)   # agent_turn looks up `chat`, so every model call is now counted
TRIAGE_THREAD = "aml-triage-desk"

def triage_alert(alert, thread_id=TRIAGE_THREAD, verbose=True):
    prompt = (TRIAGE_SYSTEM_PROMPT + "\n\n--- ALERT ---\n" + evidence_pack(agent_conn, alert)
              + "\n--- END ALERT ---\nDecide now. Reply with the JSON object only.")
    reply = agent_turn(prompt, thread_id=thread_id, max_iterations=6, budget_seconds=120.0, verbose=verbose)
    decision = validate_decision(extract_json(reply), alert)
    record_decision(agent_conn, alert, decision)               # ledger row for the examiner
    write_facts([case_decision_fact(alert, decision)])         # memory for the agent's next run
    return {**alert, **decision}

_records = run_queue(_queue[:TRIAGE_LIMIT], triage_alert, TRIAGE_THREAD)
print_ledger(agent_conn)   # the ledger as an examiner would query it
