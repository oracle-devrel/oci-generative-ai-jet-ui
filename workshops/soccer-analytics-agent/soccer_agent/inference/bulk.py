"""Lookup precomputed predictions from PREDICCIONES_FINAL."""

from __future__ import annotations

from dataclasses import dataclass

from soccer_agent.db import get_connection


@dataclass
class Prediction:
    home_team: str
    away_team: str
    prob_home_win: float
    prob_draw: float
    prob_away_win: float
    model_version: str
    source: str  # "bulk" | "live"


def lookup(home_team: str, away_team: str,
           model_version: str | None = None) -> Prediction | None:
    sql = (
        "SELECT HOME_TEAM, AWAY_TEAM, PROB_HOME_WIN, PROB_DRAW, PROB_AWAY_WIN, MODEL_VERSION "
        "FROM PREDICCIONES_FINAL "
        "WHERE HOME_TEAM = :h AND AWAY_TEAM = :a "
    )
    binds = {"h": home_team, "a": away_team}
    if model_version:
        sql += "AND MODEL_VERSION = :v "
        binds["v"] = model_version
    sql += "ORDER BY MODEL_VERSION DESC FETCH FIRST 1 ROWS ONLY"

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, binds)
        row = cur.fetchone()
    if not row:
        return None
    return Prediction(*row, source="bulk")
