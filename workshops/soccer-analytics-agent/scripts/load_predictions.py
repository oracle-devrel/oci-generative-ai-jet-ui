#!/usr/bin/env python3
"""Bulk-load match predictions from models/predictions.parquet into Oracle.

Parquet columns: home_team, away_team, prob_home_win, prob_draw, prob_away_win, model_version.
"""

import argparse
from pathlib import Path

import pandas as pd

from soccer_agent.db import get_connection

REPO = Path(__file__).resolve().parent.parent
DEFAULT_PARQUET = REPO / "models" / "predictions.parquet"

DDL = """
CREATE TABLE PREDICCIONES_FINAL (
    HOME_TEAM        VARCHAR2(200),
    AWAY_TEAM        VARCHAR2(200),
    PROB_HOME_WIN    NUMBER,
    PROB_DRAW        NUMBER,
    PROB_AWAY_WIN    NUMBER,
    MODEL_VERSION    VARCHAR2(64),
    CONSTRAINT pk_pred PRIMARY KEY (HOME_TEAM, AWAY_TEAM, MODEL_VERSION)
)
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_PARQUET,
        help="Parquet file to load into PREDICCIONES_FINAL.",
    )
    ns = parser.parse_args()
    parquet = ns.path if ns.path.is_absolute() else REPO / ns.path
    if not parquet.exists():
        raise SystemExit(
            f"{parquet} not found. Run `uv run python scripts/prepare_artifacts.py` "
            "after loading the Kaggle data, then rerun this loader."
        )

    df = pd.read_parquet(parquet)
    expected = {"home_team", "away_team", "prob_home_win",
                "prob_draw", "prob_away_win", "model_version"}
    missing = expected - set(df.columns)
    if missing:
        raise SystemExit(f"Parquet missing columns: {missing}")

    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DROP TABLE PREDICCIONES_FINAL PURGE")
        except Exception:
            pass
        cur.execute(DDL)
        rows = list(df[["home_team", "away_team", "prob_home_win",
                        "prob_draw", "prob_away_win", "model_version"]]
                    .itertuples(index=False, name=None))
        cur.executemany(
            "INSERT INTO PREDICCIONES_FINAL "
            "(HOME_TEAM, AWAY_TEAM, PROB_HOME_WIN, PROB_DRAW, PROB_AWAY_WIN, MODEL_VERSION) "
            "VALUES (:1, :2, :3, :4, :5, :6)",
            rows,
        )
        conn.commit()
    try:
        shown = parquet.relative_to(REPO)
    except ValueError:
        shown = parquet
    print(f"Loaded {len(rows)} predictions from {shown}.")


if __name__ == "__main__":
    main()
