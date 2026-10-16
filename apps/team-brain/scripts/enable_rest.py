"""REST-enable the app schema so Database Actions (ORDS) can sign in as it.

Run once after ORDS is installed in the database:
    uv run python scripts/enable_rest.py
Then open http://localhost:8181/ords/sql-developer and sign in as the app user.
"""

from __future__ import annotations

import oracledb

from team_brain.config import ORACLE_DSN, ORACLE_PASSWORD, ORACLE_USER
oracledb.defaults.program = "devrel-developerhub-team-brain"

conn = oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)
cur = conn.cursor()
cur.execute(
    """
    BEGIN
      ORDS.ENABLE_SCHEMA(
        p_enabled             => TRUE,
        p_schema              => :schema,
        p_url_mapping_type    => 'BASE_PATH',
        p_url_mapping_pattern => LOWER(:schema),
        p_auto_rest_auth      => TRUE);
      COMMIT;
    END;
    """,
    schema=ORACLE_USER,
)
cur.execute(
    "SELECT COUNT(*) FROM user_ords_schemas WHERE parsing_schema = :s AND status = 'ENABLED'",
    s=ORACLE_USER,
)
print(f"{ORACLE_USER} REST-enabled:", cur.fetchone()[0] == 1)
