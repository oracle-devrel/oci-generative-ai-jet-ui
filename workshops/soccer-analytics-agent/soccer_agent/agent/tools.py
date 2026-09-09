"""Tool schemas and dispatch for the soccer agent."""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any


from soccer_agent.agent.embeddings import embed_one
from soccer_agent.agent.feature_runtime import get_runtime
from soccer_agent.db import get_connection
from soccer_agent.inference.bulk import lookup as bulk_lookup
from soccer_agent.inference.live import predict as live_predict
from soccer_agent.memory.episodic import EpisodicMemory
from soccer_agent.memory.semantic import Fact, SemanticMemory

ALLOWED_TABLES = {
    "MATCH_RESULTS", "GOALSCORERS", "SHOOTOUTS", "WC2026_VENUES",
    "PREDICCIONES_FINAL", "VW_COMPETITIVE_MATCHES", "VW_TEAM_STATISTICS",
    "AGENT_SESSIONS", "WORKING_MEMORY", "EPISODIC_MEMORY", "SEMANTIC_MEMORY",
    "SOCCER_LANGCHAIN_DOCS",
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "sql_query",
        "description": ("Run a read-only SELECT against the soccer schema. "
                        "Allowlisted tables only. Returns up to 50 rows."),
        "parameters": {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        },
    },
    {
        "name": "vector_search",
        "description": (
            "Semantic-only baseline over distilled match/team facts in "
            "semantic_memory. Use this to contrast against hybrid_retrieve or "
            "as a fallback, not as the primary evidence path when cached ML "
            "prediction documents are needed."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
                "fact_type": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "hybrid_retrieve",
        "description": (
            "Default explanatory retrieval over the langchain-oracledb OracleVS "
            "vector store. Combines Oracle vector similarity with keyword/text "
            "evidence over cached ML prediction documents and football facts. "
            "Prefer this over raw vector_search for final answers, evidence "
            "comparisons, and model rationale unless the user explicitly asks "
            "for the semantic-only baseline."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
                "search_mode": {
                    "type": "string",
                    "enum": ["hybrid", "semantic", "keyword"],
                    "default": "hybrid",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "predict_match",
        "description": ("On-demand XGBoost prediction for a hypothetical match. "
                        "Internally assembles the full 92-feature row (Elo, form, "
                        "H2H, momentum, Poisson xG, venue, tournament context) "
                        "from enhanced_features.py and runs the trained model. "
                        "Returns win/draw/loss probabilities."),
        "parameters": {
            "type": "object",
            "properties": {
                "home_team": {"type": "string"},
                "away_team": {"type": "string"},
                "neutral": {"type": "boolean", "default": True},
            },
            "required": ["home_team", "away_team"],
        },
    },
    {
        "name": "build_match_briefing",
        "description": (
            "Build a structured analyst briefing for a match. Combines live "
            "92-feature predict_match output, Elo/form/H2H/momentum/Poisson/"
            "tournament-context tool results, hybrid OracleVS evidence, and the "
            "semantic-only baseline. Use this for the workshop's broadcast, "
            "coach, sponsor, or executive briefing use case."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "home_team": {"type": "string"},
                "away_team": {"type": "string"},
                "neutral": {"type": "boolean", "default": True},
                "focus": {
                    "type": "string",
                    "default": "broadcast",
                    "description": "Audience focus, e.g. broadcast, coach, sponsor, executive.",
                },
            },
            "required": ["home_team", "away_team"],
        },
    },
    {
        "name": "get_elo",
        "description": ("FootballElo rating for one team (enhanced_features.py "
                        "family 0). Tier-aware K-factors (WC=60, continental=50, "
                        "qualifier=40, friendly=20), home advantage = 100, goal-diff "
                        "multiplier. Returns global Elo plus per-tier ratings."),
        "parameters": {
            "type": "object",
            "properties": {"team": {"type": "string"}},
            "required": ["team"],
        },
    },
    {
        "name": "get_team_form",
        "description": ("Rolling form and goal averages from TeamTracker "
                        "(enhanced_features.py family 0). pts = W:1 D:0.5 L:0 "
                        "over last n matches plus exponentially-weighted variant."),
        "parameters": {
            "type": "object",
            "properties": {
                "team": {"type": "string"},
                "n": {"type": "integer", "default": 10},
            },
            "required": ["team"],
        },
    },
    {
        "name": "get_h2h",
        "description": ("Head-to-head record from H2HTracker (enhanced_features.py "
                        "family 0). Returns win rate from team_a's perspective, "
                        "total matches, and goal-diff per match."),
        "parameters": {
            "type": "object",
            "properties": {
                "team_a": {"type": "string"},
                "team_b": {"type": "string"},
            },
            "required": ["team_a", "team_b"],
        },
    },
    {
        "name": "get_momentum",
        "description": ("Psychological/momentum signals from MomentumTracker "
                        "(enhanced_features.py family 2): streak, unbeaten run, "
                        "clean-sheet pct, comeback rate, draw tendency, blowouts."),
        "parameters": {
            "type": "object",
            "properties": {
                "team": {"type": "string"},
                "n": {"type": "integer", "default": 15},
            },
            "required": ["team"],
        },
    },
    {
        "name": "get_poisson_xg",
        "description": ("Poisson expected-goals model from PoissonTracker "
                        "(enhanced_features.py family 3). Returns home/away "
                        "lambdas (attack vs opponent defense), Poisson outcome "
                        "probabilities, and over/underperformance vs actuals."),
        "parameters": {
            "type": "object",
            "properties": {
                "home_team": {"type": "string"},
                "away_team": {"type": "string"},
                "n": {"type": "integer", "default": 20},
            },
            "required": ["home_team", "away_team"],
        },
    },
    {
        "name": "get_tournament_context",
        "description": ("Tournament-stage context from TournamentTracker "
                        "(enhanced_features.py family 5): WC-finals form vs "
                        "continental vs qualifying vs friendly, plus the "
                        "big-game factor (competitive minus friendly)."),
        "parameters": {
            "type": "object",
            "properties": {"team": {"type": "string"}},
            "required": ["team"],
        },
    },
    {
        "name": "lookup_prediction",
        "description": "Read precomputed prediction from PREDICCIONES_FINAL.",
        "parameters": {
            "type": "object",
            "properties": {
                "home_team": {"type": "string"},
                "away_team": {"type": "string"},
            },
            "required": ["home_team", "away_team"],
        },
    },
    {
        "name": "remember",
        "description": "Write a fact to semantic memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "fact_type": {"type": "string"},
                "subject_key": {"type": "string"},
                "summary": {"type": "string"},
                "source": {"type": "object"},
            },
            "required": ["fact_type", "subject_key", "summary"],
        },
    },
    {
        "name": "recall",
        "description": "Recent N turns of episodic memory.",
        "parameters": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 8}},
        },
    },
]

_SELECT_RE = re.compile(r"^\s*SELECT\s", re.IGNORECASE | re.DOTALL)
_HAS_LIMIT = re.compile(r"\bFETCH\s+FIRST\b|\bROWNUM\b", re.IGNORECASE)
_FORBIDDEN = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
    "GRANT", "REVOKE", "MERGE", "CREATE",
}


def _enforce_select(sql: str) -> str:
    if not _SELECT_RE.match(sql):
        raise ValueError("only SELECT statements are allowed")
    if ";" in sql.rstrip().rstrip(";"):
        raise ValueError("multiple statements not allowed")
    cleaned = sql.upper()
    for token in re.findall(r"\b[A-Z_][A-Z0-9_]*\b", cleaned):
        if token in _FORBIDDEN:
            raise ValueError(f"keyword not allowed: {token}")
    return sql


def _maybe_inject_limit(sql: str, limit: int) -> str:
    if _HAS_LIMIT.search(sql):
        return sql
    return f"SELECT * FROM ({sql}) WHERE ROWNUM <= {limit}"


def _safe_tool(name: str, args: dict[str, Any], *, session_id: str) -> dict[str, Any]:
    """Call another tool while preserving briefing progress on optional failures."""
    try:
        return dispatch(name, args, session_id=session_id)
    except Exception as exc:  # pragma: no cover - defensive workshop resilience
        return {"error": f"{name} failed: {type(exc).__name__}: {str(exc)[:300]}"}


def _winner_from_prediction(prediction: dict[str, Any], home: str, away: str) -> tuple[str, float]:
    probs = {
        home: float(prediction.get("prob_home_win", 0.0) or 0.0),
        "Draw": float(prediction.get("prob_draw", 0.0) or 0.0),
        away: float(prediction.get("prob_away_win", 0.0) or 0.0),
    }
    winner = max(probs, key=probs.get)
    return winner, probs[winner]


def _compact_hybrid_docs(result: dict[str, Any]) -> list[dict[str, Any]]:
    docs = result.get("documents") if isinstance(result, dict) else None
    if not isinstance(docs, list):
        return []
    compact = []
    for doc in docs[:3]:
        metadata = doc.get("metadata", {}) if isinstance(doc, dict) else {}
        compact.append({
            "doc_id": metadata.get("doc_id"),
            "doc_type": metadata.get("doc_type"),
            "retrieval_mode": doc.get("retrieval_mode"),
            "score": doc.get("score"),
            "content": str(doc.get("content", ""))[:320],
        })
    return compact


def _compact_semantic_facts(result: dict[str, Any]) -> list[dict[str, Any]]:
    facts = result.get("facts") if isinstance(result, dict) else None
    if not isinstance(facts, list):
        return []
    return [
        {
            "fact_type": fact.get("fact_type"),
            "subject_key": fact.get("subject_key"),
            "summary": fact.get("summary"),
        }
        for fact in facts[:3]
        if isinstance(fact, dict)
    ]


def _build_briefing_bullets(
    home: str,
    away: str,
    prediction: dict[str, Any],
    h2h: dict[str, Any],
    poisson: dict[str, Any],
    hybrid_docs: list[dict[str, Any]],
) -> list[str]:
    if "error" in prediction:
        return [f"Prediction unavailable: {prediction['error']}"]
    winner, confidence = _winner_from_prediction(prediction, home, away)
    bullets = [
        (
            f"Live model headline: {winner} is the top outcome at "
            f"{confidence:.1%}; the prediction used "
            f"{prediction.get('features_used', 'unknown')} engineered features."
        ),
        (
            f"Probability split: {home} {float(prediction.get('prob_home_win', 0.0)):.1%}, "
            f"draw {float(prediction.get('prob_draw', 0.0)):.1%}, "
            f"{away} {float(prediction.get('prob_away_win', 0.0)):.1%}."
        ),
    ]
    if "h2h_matches" in h2h:
        bullets.append(
            f"Head-to-head sample: {int(h2h.get('h2h_matches', 0))} historical matches, "
            f"{home} win-rate signal {float(h2h.get('h2h_win_rate', 0.0)):.1%}."
        )
    if "home_lambda" in poisson and "away_lambda" in poisson:
        bullets.append(
            f"Poisson xG cross-check: {home} λ={float(poisson['home_lambda']):.2f}, "
            f"{away} λ={float(poisson['away_lambda']):.2f}."
        )
    bullets.append(
        "Hybrid retrieval evidence: "
        + (
            f"{len(hybrid_docs)} OracleVS document(s), first={hybrid_docs[0].get('doc_id')}."
            if hybrid_docs else "no hybrid documents returned; rerun load_langchain_vectors.py --reset."
        )
    )
    return bullets


def _build_match_briefing(args: dict[str, Any], *, session_id: str) -> dict[str, Any]:
    home = args["home_team"]
    away = args["away_team"]
    neutral = bool(args.get("neutral", True))
    focus = str(args.get("focus", "broadcast"))
    evidence_query = f"{home} {away} World Cup prediction evidence"

    prediction = _safe_tool(
        "predict_match",
        {"home_team": home, "away_team": away, "neutral": neutral},
        session_id=session_id,
    )
    h2h = _safe_tool("get_h2h", {"team_a": home, "team_b": away}, session_id=session_id)
    poisson = _safe_tool(
        "get_poisson_xg",
        {"home_team": home, "away_team": away, "n": 20},
        session_id=session_id,
    )
    hybrid = _safe_tool(
        "hybrid_retrieve",
        {"query": evidence_query, "limit": 3, "search_mode": "hybrid"},
        session_id=session_id,
    )
    semantic = _safe_tool(
        "vector_search",
        {"query": evidence_query, "limit": 3},
        session_id=session_id,
    )

    team_snapshots = {
        team: {
            "elo": _safe_tool("get_elo", {"team": team}, session_id=session_id),
            "form": _safe_tool("get_team_form", {"team": team, "n": 10}, session_id=session_id),
            "momentum": _safe_tool("get_momentum", {"team": team, "n": 15}, session_id=session_id),
            "tournament_context": _safe_tool(
                "get_tournament_context", {"team": team}, session_id=session_id,
            ),
        }
        for team in (home, away)
    }
    hybrid_docs = _compact_hybrid_docs(hybrid)
    semantic_facts = _compact_semantic_facts(semantic)

    return {
        "use_case": "match_intelligence_briefing",
        "focus": focus,
        "matchup": {"home_team": home, "away_team": away, "neutral": neutral},
        "live_prediction": prediction,
        "team_snapshots": team_snapshots,
        "matchup_context": {"h2h": h2h, "poisson_xg": poisson},
        "hybrid_evidence": {
            "query": evidence_query,
            "documents": hybrid_docs,
            "error": hybrid.get("error") if isinstance(hybrid, dict) else None,
        },
        "semantic_only_baseline": {
            "query": evidence_query,
            "facts": semantic_facts,
            "error": semantic.get("error") if isinstance(semantic, dict) else None,
        },
        "narrative_bullets": _build_briefing_bullets(
            home, away, prediction, h2h, poisson, hybrid_docs,
        ),
    }


def dispatch(name: str, args: dict[str, Any], *, session_id: str) -> dict[str, Any]:
    if name == "sql_query":
        try:
            sql = _enforce_select(args["sql"])
        except ValueError as exc:
            return {"error": f"only SELECT allowed: {exc}"}
        sql = _maybe_inject_limit(sql, 50)
        with get_connection() as conn:
            cur = conn.cursor()
            cur.callTimeout = 5000
            try:
                cur.execute(sql)
                cols = [c[0] for c in cur.description]
                rows = [
                    {c: (v.read() if hasattr(v, "read") else v)
                     for c, v in zip(cols, row)}
                    for row in cur.fetchall()
                ]
            except Exception as exc:
                return {"error": f"query failed: {exc}"}
        return {"rows": rows}

    if name == "vector_search":
        q_emb = embed_one(args["query"])
        sm = SemanticMemory()
        results = sm.search(q_emb, limit=int(args.get("limit", 5)),
                            fact_type=args.get("fact_type"))
        return {"facts": [
            {"fact_type": f.fact_type, "subject_key": f.subject_key,
             "summary": f.summary, "source": f.source}
            for f in results
        ]}

    if name == "hybrid_retrieve":
        from soccer_agent.memory.langchain_hybrid import (
            LangChainOracleDBUnavailable,
            hybrid_search,
        )

        mode = args.get("search_mode", "hybrid")
        if mode not in {"hybrid", "semantic", "keyword"}:
            return {"error": "search_mode must be hybrid, semantic, or keyword"}
        try:
            results = hybrid_search(
                args["query"],
                limit=int(args.get("limit", 5)),
                search_mode=mode,
            )
        except LangChainOracleDBUnavailable as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": f"hybrid retrieval failed: {exc}"}
        return {"documents": [
            {
                "content": r.page_content,
                "metadata": r.metadata,
                "score": r.score,
                "retrieval_mode": r.retrieval_mode,
            }
            for r in results
        ]}

    if name == "predict_match":
        runtime = get_runtime()
        features = runtime.build_feature_row(
            args["home_team"], args["away_team"],
            neutral=bool(args.get("neutral", True)),
        )
        pred = live_predict(features, args["home_team"], args["away_team"])
        return {**asdict(pred), "features_used": len(features)}

    if name == "build_match_briefing":
        return _build_match_briefing(args, session_id=session_id)

    if name == "get_elo":
        return get_runtime().get_elo(args["team"])

    if name == "get_team_form":
        return get_runtime().get_team_form(args["team"], int(args.get("n", 10)))

    if name == "get_h2h":
        return get_runtime().get_h2h(args["team_a"], args["team_b"])

    if name == "get_momentum":
        return get_runtime().get_momentum(args["team"], int(args.get("n", 15)))

    if name == "get_poisson_xg":
        return get_runtime().get_poisson_xg(
            args["home_team"], args["away_team"], int(args.get("n", 20)),
        )

    if name == "get_tournament_context":
        return get_runtime().get_tournament_context(args["team"])

    if name == "lookup_prediction":
        pred = bulk_lookup(args["home_team"], args["away_team"])
        if pred is None:
            return {"error": "no precomputed prediction for that matchup"}
        return asdict(pred)

    if name == "remember":
        SemanticMemory().upsert(Fact(
            fact_type=args["fact_type"], subject_key=args["subject_key"],
            summary=args["summary"], source=args.get("source", {}),
            embedding=embed_one(args["summary"]),
        ))
        return {"ok": True}

    if name == "recall":
        turns = EpisodicMemory(session_id).recent(limit=int(args.get("limit", 8)))
        return {"turns": [
            {"role": t.role, "content": t.content,
             "tool_name": t.tool_name, "tool_args": t.tool_args}
            for t in turns
        ]}

    return {"error": f"unknown tool: {name}"}
