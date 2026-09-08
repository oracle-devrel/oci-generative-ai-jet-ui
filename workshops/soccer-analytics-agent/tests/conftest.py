import os
import subprocess
from pathlib import Path

import pandas as pd
import pytest
import oracledb
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / ".env")

# Integration tests are allowed to drop and recreate their target schema. Never
# point that destructive fixture at the workshop/demo user by default; otherwise
# a normal `pytest` run erases the already-bootstrapped attendee environment.
_WORKSHOP_USER = os.environ.get("ORACLE_USER", "soccer")
_TEST_USER = os.environ.get("ORACLE_TEST_USER", f"{_WORKSHOP_USER}_test")
_TEST_PASSWORD = os.environ.get("ORACLE_TEST_PASSWORD", os.environ.get("ORACLE_PASSWORD", "oracle"))
_TEST_DSN = os.environ.get("ORACLE_TEST_DSN", os.environ.get("ORACLE_DSN", "localhost:1525/FREEPDB1"))

if (
    _TEST_USER.upper() == _WORKSHOP_USER.upper()
    and os.environ.get("ALLOW_DESTRUCTIVE_ORACLE_TESTS") != "1"
):
    raise RuntimeError(
        "Refusing to run destructive Oracle integration tests against the "
        f"workshop user {_WORKSHOP_USER!r}. Set ORACLE_TEST_USER to a separate "
        "schema (default: <ORACLE_USER>_test), or set "
        "ALLOW_DESTRUCTIVE_ORACLE_TESTS=1 if this is intentional."
    )

os.environ["ORACLE_USER"] = _TEST_USER
os.environ["ORACLE_PASSWORD"] = _TEST_PASSWORD
os.environ["ORACLE_DSN"] = _TEST_DSN


@pytest.fixture(scope="session")
def soccer_user_ready():
    """Create the isolated test user once for the test session."""
    admin_pw = os.environ["ORACLE_ADMIN_PASSWORD"]
    user = os.environ["ORACLE_USER"]
    pw = os.environ["ORACLE_PASSWORD"]
    dsn = os.environ["ORACLE_DSN"]

    with oracledb.connect(user="system", password=admin_pw, dsn=dsn) as conn:
        cur = conn.cursor()
        cur.execute(
            "BEGIN EXECUTE IMMEDIATE 'DROP USER " + user + " CASCADE'; "
            "EXCEPTION WHEN OTHERS THEN NULL; END;"
        )
        cur.execute(f'CREATE USER {user} IDENTIFIED BY "{pw}"')
        cur.execute(f"GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO {user}")
        cur.execute(f"GRANT CREATE VIEW, CREATE SESSION TO {user}")
        cur.execute(f"GRANT CREATE MINING MODEL TO {user}")
        # Note: DBMS_VECTOR is already EXECUTE to PUBLIC on Oracle AI Database Free; no explicit grant needed.
        conn.commit()
    yield


@pytest.fixture(scope="session")
def onnx_model_loaded(soccer_user_ready):
    """Ensure ALL_MINILM_L6_V2 is registered."""
    subprocess.run(
        ["uv", "run", "python", "scripts/load_onnx_model.py"],
        check=True, cwd=REPO,
    )
    yield


@pytest.fixture(scope="session")
def memory_schema_ready(soccer_user_ready):
    """Apply memory schema once per test session."""
    subprocess.run(
        ["uv", "run", "python", "scripts/init_memory.py"],
        check=True, cwd=REPO,
    )
    yield


@pytest.fixture(scope="session")
def predictions_loaded(soccer_user_ready, tmp_path_factory):
    parq = tmp_path_factory.mktemp("predictions") / "predictions.parquet"
    pd.DataFrame([
        {"home_team": "Spain", "away_team": "Brazil",
         "prob_home_win": 0.45, "prob_draw": 0.25, "prob_away_win": 0.30,
         "model_version": "v1"},
        {"home_team": "Andorra", "away_team": "Spain",
         "prob_home_win": 0.02, "prob_draw": 0.08, "prob_away_win": 0.90,
         "model_version": "v1"},
    ]).to_parquet(parq, index=False)
    subprocess.run(
        ["uv", "run", "python", str(REPO / "scripts" / "load_predictions.py"),
         "--path", str(parq)],
        check=True, cwd=REPO,
    )
    try:
        yield
    finally:
        default_parq = REPO / "models" / "predictions.parquet"
        if default_parq.exists():
            subprocess.run(
                ["uv", "run", "python", str(REPO / "scripts" / "load_predictions.py")],
                check=False, cwd=REPO,
            )
