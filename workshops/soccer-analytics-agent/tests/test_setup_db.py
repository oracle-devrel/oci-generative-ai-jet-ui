import subprocess
from pathlib import Path

import pytest
from soccer_agent.db import get_connection

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def sample_csvs(soccer_user_ready):
    """Ensure data/ contains at least the three required CSVs (real or stub)."""
    import csv as _csv
    data_dir = REPO / "data"
    data_dir.mkdir(exist_ok=True)
    if not (data_dir / "results.csv").exists():
        with open(data_dir / "results.csv", "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["date", "home_team", "away_team", "home_score",
                        "away_score", "tournament", "city", "country", "neutral"])
            w.writerow(["2022-12-18", "Argentina", "France", 3, 3,
                        "FIFA World Cup", "Lusail", "Qatar", "TRUE"])
            w.writerow(["2024-07-14", "Spain", "England", 2, 1,
                        "UEFA Euro", "Berlin", "Germany", "TRUE"])
            w.writerow(["2023-11-21", "Brazil", "Argentina", 0, 1,
                        "FIFA World Cup qualification", "Rio de Janeiro", "Brazil", "FALSE"])
        with open(data_dir / "goalscorers.csv", "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["date", "home_team", "away_team", "team", "scorer",
                        "minute", "own_goal", "penalty"])
            w.writerow(["2022-12-18", "Argentina", "France", "Argentina",
                        "Messi", "23", "FALSE", "FALSE"])
        with open(data_dir / "shootouts.csv", "w", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["date", "home_team", "away_team", "winner", "first_shooter"])
            w.writerow(["2022-12-18", "Argentina", "France", "Argentina", "Argentina"])
    yield data_dir


@pytest.mark.integration
def test_setup_db_creates_tables(sample_csvs):
    result = subprocess.run(
        ["uv", "run", "python", str(REPO / "scripts" / "setup_db.py")],
        capture_output=True, text=True, check=True, cwd=REPO,
    )
    assert "Done!" in result.stdout
    with get_connection() as conn:
        cur = conn.cursor()
        for table in ["MATCH_RESULTS", "GOALSCORERS", "SHOOTOUTS", "WC2026_VENUES"]:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            assert cur.fetchone()[0] > 0, f"{table} is empty"
