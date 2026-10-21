from workshop.triage import impact_board

MANUAL_MINUTES_PER_ALERT = 45.0   # assumed analyst time; change it and re-run

impact_board(agent_conn, MANUAL_MINUTES_PER_ALERT)
