import subprocess
import pytest
from pathlib import Path
from soccer_agent.db import get_connection

REPO = Path(__file__).resolve().parent.parent
TABLES = ["AGENT_SESSIONS", "WORKING_MEMORY", "EPISODIC_MEMORY", "SEMANTIC_MEMORY"]


@pytest.mark.integration
def test_init_memory_creates_all_tables(soccer_user_ready):
    result = subprocess.run(
        ["uv", "run", "python", str(REPO / "scripts" / "init_memory.py")],
        capture_output=True, text=True, check=True, cwd=REPO,
    )
    assert "Memory schema applied." in result.stdout
    with get_connection() as conn:
        cur = conn.cursor()
        for t in TABLES:
            cur.execute(
                "SELECT COUNT(*) FROM user_tables WHERE table_name = :1", [t]
            )
            assert cur.fetchone()[0] == 1, f"Missing table {t}"
