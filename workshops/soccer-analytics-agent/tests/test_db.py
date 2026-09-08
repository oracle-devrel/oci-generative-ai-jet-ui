from soccer_agent.db import get_connection, get_admin_connection


def test_admin_connection_runs_select():
    with get_admin_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM DUAL")
        assert cur.fetchone()[0] == 1


def test_soccer_user_can_select_dual(soccer_user_ready):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM DUAL")
        assert cur.fetchone()[0] == 1
