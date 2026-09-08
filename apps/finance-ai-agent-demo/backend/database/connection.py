"""Oracle Database connection with retry logic."""

import time

import oracledb
from config import DB_CONFIG

# Return CLOBs/BLOBs as Python strings/bytes instead of LOB objects
oracledb.defaults.fetch_lobs = False


def connect_to_oracle(max_retries=3, retry_delay=5, **overrides):
    """Connect to Oracle database with retry logic and error handling."""
    cfg = {**DB_CONFIG, **overrides}

    for attempt in range(1, max_retries + 1):
        try:
            print(f"  Connection attempt {attempt}/{max_retries}...")
            conn = oracledb.connect(
                user=cfg["user"],
                password=cfg["password"],
                dsn=cfg["dsn"],
                program=cfg.get("program", "finance_ai_agent_demo"),
            )
            print("  Connected successfully!")
            return conn
        except oracledb.OperationalError as e:
            error_msg = str(e)
            print(f"  Connection failed (attempt {attempt}/{max_retries}): {error_msg}")
            if attempt < max_retries:
                print(f"  Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)
            else:
                raise
        except Exception as e:
            print(f"  Unexpected error: {e}")
            raise

    raise ConnectionError("Failed to connect after all retries")


def get_admin_connection(admin_password, dsn=None):
    """Connect as SYSDBA for user creation."""
    return oracledb.connect(
        user="sys",
        password=admin_password,
        dsn=dsn or DB_CONFIG["dsn"],
        mode=oracledb.SYSDBA,
    )
