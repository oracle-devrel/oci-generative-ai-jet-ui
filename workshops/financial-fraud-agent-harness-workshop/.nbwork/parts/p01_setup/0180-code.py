from workshop.connect import connect
from workshop.preflight import run_preflight

SYS_DSN    = os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1")
AGENT_USER = os.environ.get("ORACLE_AGENT_USER", "AGENT")
AGENT_PASS = os.environ.get("ORACLE_AGENT_PASS", "AgentPwd_2025")
DEMO_USER  = os.environ.get("ORACLE_DEMO_USER", "FINANCE")

agent_conn = connect(AGENT_USER, AGENT_PASS, SYS_DSN)
run_preflight(agent_conn, LLM_PROVIDER, OCI_ROUTER)
