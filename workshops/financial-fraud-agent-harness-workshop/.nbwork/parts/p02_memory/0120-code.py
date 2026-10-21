# Hard-stop checkpoint: TODO 3
# Test the _scan_tables you just wrote: it should return one table fact for every table in the schema.
from workshop.memory import check_scan_tables
check_scan_tables(_scan_tables, agent_conn, DEMO_USER)
