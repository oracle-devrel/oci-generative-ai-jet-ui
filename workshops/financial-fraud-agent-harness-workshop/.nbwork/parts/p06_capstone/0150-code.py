from workshop.triage import (evidence_pack, show_pack, extract_json, validate_decision,
                             check_validator, TRIAGE_SYSTEM_PROMPT)

show_pack(evidence_pack(agent_conn, _queue[0]))
check_validator()   # two probe replies through extract_json and validate_decision
