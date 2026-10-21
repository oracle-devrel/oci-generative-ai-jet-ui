from workshop.memory import SchemaScanner, format_scan

scanner = SchemaScanner(memory_client, USER_ID, AGENT_ID, _scan_tables)
write_facts, run_scan = scanner.write_facts, scanner.run_scan

print(format_scan(run_scan(agent_conn, DEMO_USER)))
