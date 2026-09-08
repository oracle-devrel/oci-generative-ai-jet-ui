"""Sprawl-mode tool implementations using PostgreSQL, Neo4j, Qdrant, and PostGIS."""

import json
import time
import uuid

import eventlet
from database.query_helper import execute_query

# ---------------------------------------------------------------------------
# Helper: log a non-SQL query (Neo4j / Qdrant) through the QueryLogger
# ---------------------------------------------------------------------------


def _log_external_query(
    query_logger, query_text, params, description, query_type, rows_count=0, elapsed_ms=0
):
    """Manually log a non-SQL query so the UI Database pane shows it."""
    if not query_logger:
        return
    record = {
        "id": str(uuid.uuid4())[:8],
        "type": query_type,
        "sql": query_text.strip(),
        "params": str(params) if params else None,
        "elapsed_ms": elapsed_ms,
        "result_count": rows_count,
        "top_result_preview": None,
        "timestamp": time.time(),
        "description": description,
    }
    query_logger.queries.append(record)
    if query_logger.socketio:
        query_logger.socketio.emit("query_executed", record)
        eventlet.sleep(0)


# ---------------------------------------------------------------------------
# 1. Account details (Relational + JSONB)
# ---------------------------------------------------------------------------


def get_account_details_sprawl(pg_conn, args, query_logger):
    account_id = args.get("account_id", "")

    sql = """
        SELECT ca.account_id, ca.client_name, ca.account_type, ca.risk_profile, ca.aum,
               ca.relationship_manager, ca.status,
               ca.metadata->'investment_preferences'->>'esg_mandate' AS esg_mandate,
               ca.metadata->'investment_preferences'->>'max_single_position' AS max_position,
               ca.metadata->'investment_preferences'->'preferred_sectors' AS preferred_sectors,
               ca.metadata->'investment_preferences'->'excluded_sectors' AS excluded_sectors,
               COALESCE(h.num_holdings, 0) AS num_holdings,
               COALESCE(h.total_holdings_value, 0) AS total_holdings_value
        FROM client_accounts ca
        LEFT JOIN (
            SELECT account_id,
                   COUNT(holding_id) AS num_holdings,
                   SUM(current_value) AS total_holdings_value
            FROM portfolio_holdings
            GROUP BY account_id
        ) h ON ca.account_id = h.account_id
        WHERE ca.account_id = %(account_id)s
           OR UPPER(ca.client_name) LIKE '%%' || UPPER(%(name_search)s) || '%%'
    """

    rows, columns = execute_query(
        pg_conn,
        sql,
        {"account_id": account_id, "name_search": account_id},
        query_logger,
        description=f"Unified account lookup (Relational + JSONB): {account_id}",
    )

    if not rows:
        return f"No account found for '{account_id}'"
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


# ---------------------------------------------------------------------------
# 2. Portfolio risk analysis (Relational)
# ---------------------------------------------------------------------------


def get_portfolio_risk_sprawl(pg_conn, args, query_logger):
    account_id = args.get("account_id", "")

    sql = """
        SELECT
            ph.holding_id, ph.asset_class, ph.instrument_name, ph.ticker,
            ph.quantity, ph.current_value, ph.purchase_price, ph.sector,
            ph.region, ph.risk_rating,
            ROUND(ph.current_value / NULLIF(SUM(ph.current_value) OVER (), 0) * 100, 2) AS pct_of_portfolio,
            ROUND((ph.current_value - ph.purchase_price * ph.quantity) /
                  NULLIF(ph.purchase_price * ph.quantity, 0) * 100, 2) AS unrealized_gain_pct
        FROM portfolio_holdings ph
        WHERE ph.account_id = %(account_id)s
        ORDER BY ph.current_value DESC
    """

    rows, columns = execute_query(
        pg_conn,
        sql,
        {"account_id": account_id},
        query_logger,
        description=f"Portfolio risk analysis: {account_id}",
    )

    if not rows:
        return f"No holdings found for account '{account_id}'"
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


# ---------------------------------------------------------------------------
# 3. Compliance check (Relational + JSONB + Analytics)
# ---------------------------------------------------------------------------


def check_compliance_sprawl(pg_conn, args, query_logger):
    account_id = args.get("account_id", "")

    sql = """
        WITH holdings AS (
            SELECT
                ca.account_id, ca.risk_profile, ca.aum,
                ca.metadata->'investment_preferences'->>'max_single_position' AS max_position,
                ca.metadata->'investment_preferences'->>'esg_mandate' AS esg_mandate,
                ph.holding_id, ph.asset_class, ph.instrument_name, ph.ticker,
                ph.current_value, ph.sector, ph.risk_rating,
                ROUND(ph.current_value / NULLIF(SUM(ph.current_value) OVER (), 0) * 100, 2) AS position_pct
            FROM client_accounts ca
            LEFT JOIN portfolio_holdings ph ON ca.account_id = ph.account_id
            WHERE ca.account_id = %(account_id)s
        )
        SELECT h.*,
               cr.rule_id, cr.rule_name, cr.category AS rule_category,
               cr.threshold_type, cr.threshold_value,
               (SELECT COUNT(*) FROM compliance_rules WHERE status = 'active') AS total_active_rules
        FROM holdings h
        CROSS JOIN compliance_rules cr
        WHERE cr.status = 'active'
          AND cr.threshold_type = 'percentage'
          AND cr.category = 'concentration'
        ORDER BY h.current_value DESC NULLS LAST
    """

    rows, columns = execute_query(
        pg_conn,
        sql,
        {"account_id": account_id},
        query_logger,
        description=f"Unified compliance check (Relational + JSONB + Analytics): {account_id}",
    )

    if not rows:
        return f"No data found for account '{account_id}'"

    results = [dict(zip(columns, r, strict=False)) for r in rows]
    total_rules = results[0].get("total_active_rules", 0) if results else 0

    # Check violations using data from the unified query
    seen_holdings = set()
    violations = []
    for r in results:
        hid = r.get("holding_id")
        if hid and hid not in seen_holdings:
            seen_holdings.add(hid)
            pos_pct = r.get("position_pct") or 0
            # max_position stored as decimal (e.g. 0.10 = 10%); convert to %
            threshold_pct = float(r.get("max_position") or r.get("threshold_value") or 0.10) * 100
            if pos_pct > threshold_pct:
                violations.append(
                    {
                        "rule": r.get("rule_id", "CR-001"),
                        "rule_name": r.get("rule_name", "Single Position Concentration Limit"),
                        "holding": r.get("instrument_name"),
                        "ticker": r.get("ticker"),
                        "position_pct": pos_pct,
                        "threshold_pct": threshold_pct,
                        "severity": "warning" if pos_pct < 12 else "violation",
                    }
                )

    return json.dumps(
        {"account_id": account_id, "violations": violations, "rules_checked": total_rules},
        default=str,
    )


# ---------------------------------------------------------------------------
# 4. Find similar accounts (Neo4j graph)
# ---------------------------------------------------------------------------


def find_similar_accounts_sprawl(neo4j_driver, pg_conn, args, query_logger):
    account_id = args.get("account_id", "")

    if not neo4j_driver:
        return "Graph database (Neo4j) not available."

    # Query Neo4j for similar accounts via SIMILAR_TO edges and shared managers
    cypher = """
        MATCH (src:Client {account_id: $account_id})-[r:SIMILAR_TO]->(dst:Client)
        RETURN dst.account_id AS candidate, dst.client_name AS client_name,
               dst.risk_profile AS risk_profile, dst.aum AS aum,
               r.sim_score AS best_score, r.sim_type AS match_types
        ORDER BY r.sim_score DESC
        LIMIT 5
        UNION
        MATCH (src:Client {account_id: $account_id})-[:MANAGED_BY]->(m:Manager)<-[:MANAGED_BY]-(dst:Client)
        WHERE dst.account_id <> $account_id
        RETURN dst.account_id AS candidate, dst.client_name AS client_name,
               dst.risk_profile AS risk_profile, dst.aum AS aum,
               1.0 AS best_score, 'shared_manager' AS match_types
        LIMIT 5
    """

    start = time.time()
    with neo4j_driver.session() as session:
        result = session.run(cypher, account_id=account_id)
        records = [dict(r) for r in result]
    elapsed_ms = round((time.time() - start) * 1000, 1)

    _log_external_query(
        query_logger,
        cypher,
        {"account_id": account_id},
        description=f"Neo4j graph: similar accounts for {account_id}",
        query_type="graph",
        rows_count=len(records),
        elapsed_ms=elapsed_ms,
    )

    if not records:
        return f"No similar accounts found for '{account_id}'"
    return json.dumps(records, default=str)


# ---------------------------------------------------------------------------
# 5. Knowledge base search (Qdrant vector / PG full-text)
# ---------------------------------------------------------------------------


def search_knowledge_base_sprawl(qdrant_client, embedding_model, pg_conn, args, query_logger):
    query = args.get("query", "")
    strategy = args.get("strategy", "vector")

    if strategy in ("vector", "hybrid"):
        # Vector search via Qdrant
        start = time.time()
        query_embedding = embedding_model.embed_query(query)
        results = qdrant_client.search(
            collection_name="knowledge_base",
            query_vector=query_embedding,
            limit=5,
        )
        elapsed_ms = round((time.time() - start) * 1000, 1)

        records = [
            {
                "text": r.payload.get("text", "")[:200],
                "score": round(r.score, 4),
                **{k: v for k, v in r.payload.items() if k != "text"},
            }
            for r in results
        ]

        _log_external_query(
            query_logger,
            f"Qdrant vector search: '{query[:50]}'",
            {},
            description=f"Vector search (Qdrant): '{query[:50]}'",
            query_type="vector",
            rows_count=len(records),
            elapsed_ms=elapsed_ms,
        )
    else:
        # Text/keyword search — try PG full-text search, fall back to Qdrant vector
        try:
            sql = """
                SELECT text, metadata
                FROM knowledge_base_docs
                WHERE to_tsvector('english', text) @@ plainto_tsquery('english', %(query)s)
                ORDER BY ts_rank(to_tsvector('english', text), plainto_tsquery('english', %(query)s)) DESC
                LIMIT 5
            """
            rows, columns = execute_query(
                pg_conn,
                sql,
                {"query": query},
                query_logger,
                description=f"PG full-text search: '{query[:50]}'",
            )
            records = [dict(zip(columns, row, strict=False)) for row in rows]
        except Exception:
            # Fallback to Qdrant vector search if PG table doesn't exist
            start = time.time()
            query_embedding = embedding_model.embed_query(query)
            results = qdrant_client.search(
                collection_name="knowledge_base",
                query_vector=query_embedding,
                limit=5,
            )
            elapsed_ms = round((time.time() - start) * 1000, 1)
            records = [
                {"text": r.payload.get("text", "")[:200], "score": round(r.score, 4)}
                for r in results
            ]
            _log_external_query(
                query_logger,
                f"Qdrant vector fallback: '{query[:50]}'",
                {},
                description=f"Vector fallback (Qdrant): '{query[:50]}'",
                query_type="vector",
                rows_count=len(records),
                elapsed_ms=elapsed_ms,
            )

    if not records:
        return "No results found."
    return json.dumps(records, default=str)


# ---------------------------------------------------------------------------
# 6. Investment preferences (JSONB)
# ---------------------------------------------------------------------------


def get_investment_preferences_sprawl(pg_conn, args, query_logger):
    account_id = args.get("account_id", "")

    sql = """
        SELECT account_id, client_name,
               metadata->'investment_preferences'->>'esg_mandate' AS esg_mandate,
               metadata->'investment_preferences'->>'max_single_position' AS max_position,
               metadata->'investment_preferences'->'preferred_sectors' AS preferred_sectors,
               metadata->'investment_preferences'->'excluded_sectors' AS excluded_sectors,
               metadata->'restricted_securities' AS restricted_list
        FROM client_accounts
        WHERE account_id = %(account_id)s
    """

    rows, columns = execute_query(
        pg_conn,
        sql,
        {"account_id": account_id},
        query_logger,
        description=f"JSONB preferences: {account_id}",
    )

    if not rows:
        return f"No preferences found for '{account_id}'"
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


# ---------------------------------------------------------------------------
# 7. Search compliance rules (Relational)
# ---------------------------------------------------------------------------


def search_compliance_rules_sprawl(pg_conn, args, query_logger):
    keyword = args.get("keyword", "")
    category = args.get("category")

    sql = """
        SELECT rule_id, rule_name, category, description,
               threshold_type, threshold_value, regulatory_body
        FROM compliance_rules
        WHERE status = 'active'
          AND (UPPER(description) LIKE '%%' || UPPER(%(keyword)s) || '%%'
               OR UPPER(rule_name) LIKE '%%' || UPPER(%(keyword)s) || '%%')
    """
    params = {"keyword": keyword}

    if category:
        sql += " AND category = %(category)s"
        params["category"] = category

    sql += " ORDER BY rule_id"

    rows, columns = execute_query(
        pg_conn,
        sql,
        params,
        query_logger,
        description=f"Compliance rules search: {keyword}",
    )

    if not rows:
        return f"No compliance rules found for '{keyword}'"
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


# ---------------------------------------------------------------------------
# 8. Find nearby clients (PostGIS spatial)
# ---------------------------------------------------------------------------


def find_nearby_clients_sprawl(pg_conn, args, query_logger):
    account_id = args.get("account_id", "")
    radius_km = args.get("radius_km", 500)
    top_k = args.get("top_k", 10)

    radius_m = radius_km * 1000

    sql = """
        SELECT b.account_id, b.client_name, b.risk_profile, b.aum,
               ROUND(CAST(ST_DistanceSphere(a.location, b.location) / 1000.0 AS numeric), 1) AS distance_km
        FROM client_accounts a, client_accounts b
        WHERE a.account_id = %(account_id)s
          AND b.account_id <> a.account_id
          AND a.location IS NOT NULL
          AND b.location IS NOT NULL
          AND ST_DWithin(a.location::geography, b.location::geography, %(radius_m)s)
        ORDER BY ST_DistanceSphere(a.location, b.location)
        LIMIT %(top_k)s
    """

    rows, columns = execute_query(
        pg_conn,
        sql,
        {"account_id": account_id, "radius_m": radius_m, "top_k": top_k},
        query_logger,
        description=f"PostGIS spatial: nearby clients within {radius_km}km of {account_id}",
    )

    if not rows:
        return f"No clients found within {radius_km}km of '{account_id}'"
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


# ---------------------------------------------------------------------------
# 9. Convergent search (Relational + Graph + Vector + Spatial across databases)
# ---------------------------------------------------------------------------


def convergent_search_sprawl(
    pg_conn, neo4j_driver, qdrant_client, embedding_model, args, query_logger
):
    """Sprawl-mode convergent query: combines Relational (PG), Graph (Neo4j),
    Vector (Qdrant), and Spatial (PostGIS) results from separate databases
    into the unified [{source_type, id, detail}] format."""

    account_id = args.get("account_id", "")
    search_phrase = args.get("search_phrase", "")

    all_results = []

    # --- Relational: account info from PostgreSQL ---
    acct_sql = """
        SELECT ca.account_id, ca.client_name, ca.risk_profile,
               ca.aum, ca.relationship_manager, ca.status,
               ca.metadata->'investment_preferences'->>'esg_mandate' AS esg_mandate
        FROM client_accounts ca
        WHERE ca.account_id = %(account_id)s
    """
    try:
        rows, columns = execute_query(
            pg_conn,
            acct_sql,
            {"account_id": account_id},
            query_logger,
            description=f"Convergent/Relational: account info for {account_id}",
        )
        for row in rows:
            r = dict(zip(columns, row, strict=False))
            detail = (
                f"{r.get('client_name', '')} | {r.get('risk_profile', '')} "
                f"| RM: {r.get('relationship_manager', '')} "
                f"| AUM: {r.get('aum', '')} "
                f"| ESG: {r.get('esg_mandate') or 'N/A'}"
            )
            all_results.append(
                {"source_type": "ACCOUNT", "id": r.get("account_id", ""), "detail": detail}
            )
    except Exception:
        pass

    # --- Graph: connected accounts from Neo4j ---
    if neo4j_driver:
        cypher = """
            MATCH (src:Client {account_id: $account_id})-[r:SIMILAR_TO]->(dst:Client)
            RETURN dst.account_id AS target_id, dst.client_name AS client_name,
                   dst.risk_profile AS risk_profile, r.sim_type AS connection_type
            ORDER BY r.sim_score DESC
            LIMIT 5
        """
        try:
            start = time.time()
            with neo4j_driver.session() as session:
                result = session.run(cypher, account_id=account_id)
                graph_rows = [dict(rec) for rec in result]
            elapsed_ms = round((time.time() - start) * 1000, 1)

            _log_external_query(
                query_logger,
                cypher,
                {"account_id": account_id},
                description=f"Convergent/Graph: connected accounts for {account_id}",
                query_type="graph",
                rows_count=len(graph_rows),
                elapsed_ms=elapsed_ms,
            )
            for gr in graph_rows:
                detail = (
                    f"{gr.get('client_name', '')} | {gr.get('risk_profile', '')} "
                    f"| via: {gr.get('connection_type', '')}"
                )
                all_results.append(
                    {"source_type": "GRAPH", "id": gr.get("target_id", ""), "detail": detail}
                )
        except Exception:
            pass

    # --- Vector: knowledge base search from Qdrant ---
    if qdrant_client and embedding_model and search_phrase:
        try:
            start = time.time()
            query_embedding = embedding_model.embed_query(search_phrase)
            vec_results = qdrant_client.search(
                collection_name="knowledge_base",
                query_vector=query_embedding,
                limit=5,
            )
            elapsed_ms = round((time.time() - start) * 1000, 1)

            _log_external_query(
                query_logger,
                f"Qdrant vector search: '{search_phrase[:50]}'",
                {},
                description=f"Convergent/Vector: '{search_phrase[:50]}'",
                query_type="vector",
                rows_count=len(vec_results),
                elapsed_ms=elapsed_ms,
            )
            for vr in vec_results:
                text_preview = vr.payload.get("text", "")[:200]
                all_results.append({"source_type": "VECTOR", "id": "", "detail": text_preview})
        except Exception:
            pass

    # --- Spatial: nearby clients from PostGIS ---
    spatial_sql = """
        SELECT b.account_id, b.client_name, b.risk_profile,
               ROUND(CAST(ST_DistanceSphere(a.location, b.location) / 1000.0 AS numeric), 1) AS distance_km
        FROM client_accounts a, client_accounts b
        WHERE a.account_id = %(account_id)s
          AND b.account_id <> a.account_id
          AND a.location IS NOT NULL
          AND b.location IS NOT NULL
          AND ST_DWithin(a.location::geography, b.location::geography, 500000)
        ORDER BY ST_DistanceSphere(a.location, b.location)
        LIMIT 5
    """
    try:
        rows, columns = execute_query(
            pg_conn,
            spatial_sql,
            {"account_id": account_id},
            query_logger,
            description=f"Convergent/Spatial: nearby clients for {account_id}",
        )
        for row in rows:
            r = dict(zip(columns, row, strict=False))
            detail = (
                f"{r.get('client_name', '')} | {r.get('risk_profile', '')} "
                f"| {r.get('distance_km', '')} km away"
            )
            all_results.append(
                {"source_type": "SPATIAL", "id": r.get("account_id", ""), "detail": detail}
            )
    except Exception:
        pass

    if not all_results:
        return f"No results found for account '{account_id}'"

    return json.dumps(all_results, default=str)
