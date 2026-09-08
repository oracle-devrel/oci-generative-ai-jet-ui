#!/usr/bin/env python3
"""Generate semantic_memory facts from MATCH_RESULTS.

One fact per (team, decade) summarizing FIFA World Cup performance:
matches, wins, goals scored, goals conceded. Embeddings are computed in-DB
via the agent embedding helper.
"""

from __future__ import annotations

from typing import Iterable

from soccer_agent.agent.embeddings import embed_many
from soccer_agent.db import get_connection
from soccer_agent.memory.semantic import Fact, SemanticMemory

BATCH = 64


def team_profile_facts() -> Iterable[tuple[str, str, dict]]:
    """Yield one (fact_type, key, source) tuple per (team, decade)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            WITH team_decade AS (
                SELECT home_team AS team,
                       FLOOR(EXTRACT(YEAR FROM date_rw) / 10) * 10 AS decade,
                       CASE WHEN home_score > away_score THEN 1 ELSE 0 END AS win,
                       home_score AS gf, away_score AS ga
                FROM match_results WHERE tournament = 'FIFA World Cup'
                UNION ALL
                SELECT away_team AS team,
                       FLOOR(EXTRACT(YEAR FROM date_rw) / 10) * 10 AS decade,
                       CASE WHEN away_score > home_score THEN 1 ELSE 0 END AS win,
                       away_score AS gf, home_score AS ga
                FROM match_results WHERE tournament = 'FIFA World Cup'
            )
            SELECT team, decade, COUNT(*) AS n,
                   SUM(win) AS wins, SUM(gf) AS gf, SUM(ga) AS ga
            FROM team_decade
            WHERE team IS NOT NULL
            GROUP BY team, decade
            HAVING COUNT(*) >= 3
            ORDER BY team, decade
        """)
        for team, decade, n, wins, gf, ga in cur.fetchall():
            decade = int(decade) if decade else 0
            yield "team_decade", f"{team}:{decade}", {
                "team": team, "decade": decade, "matches": int(n),
                "wins": int(wins or 0),
                "gf": int(gf or 0), "ga": int(ga or 0),
            }


def _flush(sm: SemanticMemory, batch: list) -> None:
    summaries = [b[2] for b in batch]
    embs = embed_many(summaries)
    for (ftype, key, summary, src), e in zip(batch, embs):
        sm.upsert(Fact(fact_type=ftype, subject_key=key,
                       summary=summary, source=src, embedding=e))


def main() -> None:
    sm = SemanticMemory()
    pending: list[tuple[str, str, str, dict]] = []
    total = 0
    for ftype, key, src in team_profile_facts():
        summary = (
            f"{src['team']} in the {src['decade']}s World Cups: "
            f"{src['matches']} matches, {src['wins']} wins, "
            f"{src['gf']} goals scored, {src['ga']} conceded."
        )
        pending.append((ftype, key, summary, src))
        if len(pending) >= BATCH:
            _flush(sm, pending)
            total += len(pending)
            pending = []
    if pending:
        _flush(sm, pending)
        total += len(pending)
    print(f"Inserted {total} semantic facts.")


if __name__ == "__main__":
    main()
