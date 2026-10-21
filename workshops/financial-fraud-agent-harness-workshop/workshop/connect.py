"""Oracle connection helper for the workshop notebook."""
import time
import warnings

import oracledb

# oracleagentmemory emits a benign UserWarning on import; the notebook does not need to see it.
warnings.filterwarnings("ignore", category=UserWarning, module="oracleagentmemory")


def connect(user, password, dsn, mode=None, retries=5):
    """Open an Oracle connection, retrying while the database is still starting."""
    last_err = None
    for _ in range(retries):
        try:
            kwargs = dict(user=user, password=password, dsn=dsn)
            if mode is not None:
                kwargs["mode"] = mode
            conn = oracledb.connect(**kwargs)
            with conn.cursor() as cur:
                cur.execute("SELECT banner FROM v$version WHERE rownum = 1")
                print(f"connected as {user}@{dsn}: {cur.fetchone()[0]}")
            return conn
        except Exception as e:
            last_err = e
            time.sleep(3)
    raise RuntimeError(f"could not connect to {dsn}: {last_err}")
