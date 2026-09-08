"""SQL Property Graph traversal using GRAPH_TABLE."""

import array

from database.query_helper import execute_query


def graph_search(conn, embedding_model, query, top_k=10, seed_k=25, query_logger=None):
    """Graph retrieval: seed with vector similarity, expand via graph paths."""
    seed_k = max(seed_k, top_k)

    query_embedding = embedding_model.embed_query(query)
    query_array = array.array("f", query_embedding)

    # Subquery pattern: inner query uses raw vector_distance for bind compat
    sql = f"""
        WITH seed_raw AS (
            SELECT account_id,
                   vector_distance(embedding, :q, COSINE) as distance
            FROM client_accounts
            ORDER BY distance
            FETCH APPROX FIRST {seed_k} ROWS ONLY WITH TARGET ACCURACY 90
        ),
        seed AS (
            SELECT account_id, 1 - distance AS seed_score
            FROM seed_raw
        ),
        sim_hops AS (
            SELECT
                s.account_id AS source,
                gt.target_id AS candidate,
                s.seed_score,
                'similar_to' AS relation,
                gt.edge_score
            FROM seed s
            JOIN GRAPH_TABLE(
                financial_graph
                MATCH (src IS client)-[e IS similar_to]->(dst IS client)
                COLUMNS (
                    src.account_id AS source_id,
                    dst.account_id AS target_id,
                    e.sim_score AS edge_score
                )
            ) gt ON gt.source_id = s.account_id
        ),
        rm_hops AS (
            SELECT
                s.account_id AS source,
                gt.target_id AS candidate,
                s.seed_score,
                'shared_rm' AS relation,
                1.0 AS edge_score
            FROM seed s
            JOIN GRAPH_TABLE(
                financial_graph
                MATCH (src IS client)-[e1 IS managed_by]->(mgr IS manager)
                      <-[e2 IS managed_by]-(dst IS client)
                WHERE src.account_id <> dst.account_id
                COLUMNS (
                    src.account_id AS source_id,
                    dst.account_id AS target_id
                )
            ) gt ON gt.source_id = s.account_id
        ),
        all_candidates AS (
            SELECT * FROM sim_hops UNION ALL SELECT * FROM rm_hops
        )
        SELECT
            candidate,
            MAX(seed_score) AS best_seed,
            COUNT(DISTINCT relation) AS path_types,
            ROUND(MAX(seed_score) * 0.6 + MAX(edge_score) * 0.4, 4) AS combined_score
        FROM all_candidates
        GROUP BY candidate
        ORDER BY combined_score DESC
        FETCH FIRST {top_k} ROWS ONLY
    """

    return execute_query(
        conn, sql, {"q": query_array}, query_logger, description=f"Graph search: '{query[:50]}'"
    )


def find_similar_accounts(conn, account_id, top_k=5, query_logger=None):
    """Find similar accounts via graph traversal from a specific account."""
    sql = f"""
        WITH
        sim_hops AS (
            SELECT
                gt.target_id AS candidate,
                'similar_to' AS relation,
                gt.edge_score AS sim_score,
                gt.sim_type
            FROM GRAPH_TABLE(
                financial_graph
                MATCH (src IS client)-[e IS similar_to]->(dst IS client)
                WHERE src.account_id = :account_id
                COLUMNS (
                    dst.account_id AS target_id,
                    e.sim_score AS edge_score,
                    e.sim_type AS sim_type
                )
            ) gt
        ),
        rm_hops AS (
            SELECT
                gt.target_id AS candidate,
                'shared_rm' AS relation,
                1.0 AS sim_score,
                'shared_manager' AS sim_type
            FROM GRAPH_TABLE(
                financial_graph
                MATCH (src IS client)-[e1 IS managed_by]->(mgr IS manager)
                      <-[e2 IS managed_by]-(dst IS client)
                WHERE src.account_id = :account_id
                  AND dst.account_id <> src.account_id
                COLUMNS (
                    dst.account_id AS target_id
                )
            ) gt
        ),
        all_matches AS (
            SELECT * FROM sim_hops UNION ALL SELECT * FROM rm_hops
        )
        SELECT
            a.candidate,
            ca.client_name,
            ca.risk_profile,
            ca.aum,
            MAX(a.sim_score) AS best_score,
            LISTAGG(a.sim_type, ', ') WITHIN GROUP (ORDER BY a.sim_type) AS match_types
        FROM all_matches a
        JOIN client_accounts ca ON ca.account_id = a.candidate
        GROUP BY a.candidate, ca.client_name, ca.risk_profile, ca.aum
        ORDER BY best_score DESC
        FETCH FIRST {top_k} ROWS ONLY
    """

    return execute_query(
        conn,
        sql,
        {"account_id": account_id},
        query_logger,
        description=f"Similar accounts for {account_id}",
    )
