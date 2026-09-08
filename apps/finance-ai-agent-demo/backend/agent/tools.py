"""Agent tool definitions and execution."""

import json
import os

from database.query_helper import execute_query

# Tool schemas for OpenAI function calling
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_account_details",
            "description": "Look up account details including client name, risk profile, AUM, and holdings count. Use for any account-specific query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "Account ID (e.g. 'ACC-001') or client name to search for",
                    }
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_risk",
            "description": "Analyze portfolio holdings and risk exposure for an account. Returns asset allocation, position concentrations, and risk ratings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "The account ID to analyze risk for",
                    }
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_compliance",
            "description": "Check an account's portfolio against all active compliance rules. Returns violations and warnings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "The account ID to check compliance for",
                    }
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_similar_accounts",
            "description": "Find accounts with similar risk profiles, portfolio compositions, or shared relationship managers using graph traversal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "The account ID to find similar accounts for",
                    }
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search the knowledge base for financial research, market analysis, regulatory documents using semantic vector search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "strategy": {
                        "type": "string",
                        "enum": ["vector", "text", "hybrid"],
                        "description": "Search strategy: 'vector' for semantic, 'text' for keyword, 'hybrid' for combined",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_investment_preferences",
            "description": "Retrieve investment preferences, ESG mandates, and restricted securities from account JSON metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "The account ID to look up preferences for",
                    }
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_compliance_rules",
            "description": "Search compliance rules by category or keyword to find applicable regulations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Keyword to search in compliance rule descriptions (e.g. 'concentration', 'ESG', 'AML')",
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category filter: 'concentration', 'suitability', 'reporting', 'aml'",
                    },
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expand_summary",
            "description": "Retrieve the full content of a compressed summary by its ID. Use when your Summary Memory shows entries like [ID: abc12345] and you need the complete details to answer accurately. Returns the full summary text with preserved facts, entities, and decisions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary_id": {
                        "type": "string",
                        "description": "The summary ID to expand (e.g. 'abc12345' from [ID: abc12345] in Summary Memory)",
                    }
                },
                "required": ["summary_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_conversation",
            "description": "Compact the conversation history by summarizing older messages into a compressed snapshot. Reduces context window usage while preserving key facts, entities, account IDs, and decisions. Use when the conversation is long or when you want to free up context space. The thread_id is available in the context header.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thread_id": {
                        "type": "string",
                        "description": "The thread ID to compact (found in Conversation Memory header)",
                    }
                },
                "required": ["thread_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_tavily",
            "description": "Search the web for current information using Tavily. Use for real-time market data or news.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The web search query",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_nearby_clients",
            "description": "Find client accounts geographically near a given account using Oracle Spatial SDO_GEOMETRY and spatial indexing. Returns nearby clients with distance in km, risk profile, and AUM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "The account ID to search around (e.g. 'ACC-003')",
                    },
                    "radius_km": {
                        "type": "number",
                        "description": "Search radius in kilometers (default 500)",
                    },
                },
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convergent_search",
            "description": (
                "Run a SINGLE convergent SQL query that combines Relational data, "
                "Graph traversal, Vector search, and Spatial proximity in one statement against Oracle AI Database. "
                "Use this to demonstrate Oracle's convergent database capability: "
                "it returns account details (relational), connected accounts via graph (GRAPH_TABLE), "
                "relevant knowledge base documents (VECTOR_DISTANCE), and geographically nearby clients "
                "(SDO_WITHIN_DISTANCE) all in one query."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "The account ID to search around (e.g. 'ACC-003')",
                    },
                    "search_phrase": {
                        "type": "string",
                        "description": "Natural language phrase to search the knowledge base for relevant documents",
                    },
                },
                "required": ["account_id", "search_phrase"],
            },
        },
    },
]

# Preloaded tools: always available to the LLM regardless of query or DB state.
# With only 12 tools, all are preloaded to avoid reliance on TOOLBOX_MEMORY
# retrieval which can silently fail and leave the agent without core DB tools.
PRELOADED_TOOLS = list(TOOL_SCHEMAS)


def create_tool_executor(
    conn, embedding_model, memory_manager, llm_client, query_logger=None, extra_connections=None
):
    """Create a tool executor function with all dependencies injected."""
    from config import ARCH_MODE

    extra = extra_connections or {}
    is_sprawl = ARCH_MODE == "sprawl"

    if is_sprawl:
        from agent.sprawl_tools import (
            check_compliance_sprawl,
            convergent_search_sprawl,
            find_nearby_clients_sprawl,
            find_similar_accounts_sprawl,
            get_account_details_sprawl,
            get_investment_preferences_sprawl,
            get_portfolio_risk_sprawl,
            search_compliance_rules_sprawl,
            search_knowledge_base_sprawl,
        )

    def execute_tool(tool_name, tool_args):
        """Execute a tool by name with given arguments."""
        # DB-independent tools
        if tool_name == "expand_summary":
            return _expand_summary(memory_manager, tool_args)
        elif tool_name == "summarize_conversation":
            return _summarize_conversation(memory_manager, llm_client, tool_args)
        elif tool_name == "search_tavily":
            return _search_tavily(tool_args)

        if is_sprawl:
            pg_conn = extra.get("pg_conn") or conn
            neo4j_driver = extra.get("neo4j_driver")
            qdrant_client = extra.get("qdrant_client")

            if tool_name == "get_account_details":
                return get_account_details_sprawl(pg_conn, tool_args, query_logger)
            elif tool_name == "get_portfolio_risk":
                return get_portfolio_risk_sprawl(pg_conn, tool_args, query_logger)
            elif tool_name == "check_compliance":
                return check_compliance_sprawl(pg_conn, tool_args, query_logger)
            elif tool_name == "find_similar_accounts":
                return find_similar_accounts_sprawl(neo4j_driver, pg_conn, tool_args, query_logger)
            elif tool_name == "search_knowledge_base":
                return search_knowledge_base_sprawl(
                    qdrant_client, embedding_model, pg_conn, tool_args, query_logger
                )
            elif tool_name == "get_investment_preferences":
                return get_investment_preferences_sprawl(pg_conn, tool_args, query_logger)
            elif tool_name == "search_compliance_rules":
                return search_compliance_rules_sprawl(pg_conn, tool_args, query_logger)
            elif tool_name == "find_nearby_clients":
                return find_nearby_clients_sprawl(pg_conn, tool_args, query_logger)
            elif tool_name == "convergent_search":
                return convergent_search_sprawl(
                    pg_conn, neo4j_driver, qdrant_client, embedding_model, tool_args, query_logger
                )
            else:
                return f"Error: Unknown tool '{tool_name}'"
        else:
            # Oracle converged mode
            if tool_name == "get_account_details":
                return _get_account_details(conn, tool_args, query_logger)
            elif tool_name == "get_portfolio_risk":
                return _get_portfolio_risk(conn, tool_args, query_logger)
            elif tool_name == "check_compliance":
                return _check_compliance(conn, tool_args, query_logger)
            elif tool_name == "find_similar_accounts":
                return _find_similar_accounts(conn, tool_args, query_logger)
            elif tool_name == "search_knowledge_base":
                return _search_knowledge_base(conn, embedding_model, tool_args, query_logger)
            elif tool_name == "get_investment_preferences":
                return _get_investment_preferences(conn, tool_args, query_logger)
            elif tool_name == "search_compliance_rules":
                return _search_compliance_rules(conn, tool_args, query_logger)
            elif tool_name == "find_nearby_clients":
                return _find_nearby_clients(conn, tool_args, query_logger)
            elif tool_name == "convergent_search":
                return _convergent_search(conn, embedding_model, tool_args, query_logger)
            else:
                return f"Error: Unknown tool '{tool_name}'"

    return execute_tool


def _get_account_details(conn, args, query_logger):
    account_id = args.get("account_id", "")

    # Unified query: Relational + JSON document store in one statement
    # Uses subquery for aggregation to avoid GROUP BY on CLOB metadata column (ORA-22848)
    sql = """
        SELECT ca.account_id, ca.client_name, ca.account_type, ca.risk_profile, ca.aum,
               ca.relationship_manager, ca.status,
               JSON_VALUE(ca.metadata, '$.investment_preferences.esg_mandate') AS esg_mandate,
               JSON_VALUE(ca.metadata, '$.investment_preferences.max_single_position') AS max_position,
               JSON_QUERY(ca.metadata, '$.investment_preferences.preferred_sectors') AS preferred_sectors,
               JSON_QUERY(ca.metadata, '$.investment_preferences.excluded_sectors') AS excluded_sectors,
               NVL(h.num_holdings, 0) AS num_holdings,
               NVL(h.total_holdings_value, 0) AS total_holdings_value
        FROM client_accounts ca
        LEFT JOIN (
            SELECT account_id,
                   COUNT(holding_id) AS num_holdings,
                   SUM(current_value) AS total_holdings_value
            FROM portfolio_holdings
            GROUP BY account_id
        ) h ON ca.account_id = h.account_id
        WHERE ca.account_id = :account_id
           OR UPPER(ca.client_name) LIKE '%' || UPPER(:name_search) || '%'
    """

    rows, columns = execute_query(
        conn,
        sql,
        {"account_id": account_id, "name_search": account_id},
        query_logger,
        description=f"Unified account lookup (Relational + JSON): {account_id}",
    )

    if not rows:
        return f"No account found for '{account_id}'"
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


def _get_portfolio_risk(conn, args, query_logger):
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
        WHERE ph.account_id = :account_id
        ORDER BY ph.current_value DESC
    """

    rows, columns = execute_query(
        conn,
        sql,
        {"account_id": account_id},
        query_logger,
        description=f"Portfolio risk analysis: {account_id}",
    )

    if not rows:
        return f"No holdings found for account '{account_id}'"
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


def _check_compliance(conn, args, query_logger):
    account_id = args.get("account_id", "")

    # Unified query: Relational + JSON + Analytics in ONE statement
    # Demonstrates Oracle AI Database handling multiple data types in a single query
    sql = """
        WITH holdings AS (
            SELECT
                ca.account_id, ca.risk_profile, ca.aum,
                JSON_VALUE(ca.metadata, '$.investment_preferences.max_single_position') AS max_position,
                JSON_VALUE(ca.metadata, '$.investment_preferences.esg_mandate') AS esg_mandate,
                ph.holding_id, ph.asset_class, ph.instrument_name, ph.ticker,
                ph.current_value, ph.sector, ph.risk_rating,
                ROUND(ph.current_value / NULLIF(SUM(ph.current_value) OVER (), 0) * 100, 2) AS position_pct
            FROM client_accounts ca
            LEFT JOIN portfolio_holdings ph ON ca.account_id = ph.account_id
            WHERE ca.account_id = :account_id
        )
        SELECT h.*,
               cr.rule_id, cr.rule_name, cr.category AS rule_category,
               cr.threshold_type, cr.threshold_value,
               (SELECT COUNT(*) FROM compliance_rules WHERE status = 'active') AS total_active_rules
        FROM holdings h
        CROSS JOIN compliance_rules cr
        WHERE cr.status = 'active'
          AND cr.threshold_type = 'MAX_POSITION'
        ORDER BY h.current_value DESC NULLS LAST
    """

    rows, columns = execute_query(
        conn,
        sql,
        {"account_id": account_id},
        query_logger,
        description=f"Unified compliance check (Relational + JSON + Analytics): {account_id}",
    )

    if not rows:
        return f"No data found for account '{account_id}'"

    results = [dict(zip(columns, r, strict=False)) for r in rows]
    total_rules = results[0].get("TOTAL_ACTIVE_RULES", 0) if results else 0

    # Check violations using data from the unified query
    seen_holdings = set()
    violations = []
    for r in results:
        hid = r.get("HOLDING_ID")
        if hid and hid not in seen_holdings:
            seen_holdings.add(hid)
            pos_pct = r.get("POSITION_PCT") or 0
            # MAX_POSITION is stored as a decimal (e.g. 0.10 = 10%); convert to %
            threshold_pct = float(r.get("MAX_POSITION") or r.get("THRESHOLD_VALUE") or 0.10) * 100
            if pos_pct > threshold_pct:
                violations.append(
                    {
                        "rule": r.get("RULE_ID", "CR-001"),
                        "rule_name": r.get("RULE_NAME", "Single Position Concentration Limit"),
                        "holding": r.get("INSTRUMENT_NAME"),
                        "ticker": r.get("TICKER"),
                        "position_pct": pos_pct,
                        "threshold_pct": threshold_pct,
                        "severity": "warning" if pos_pct < 12 else "violation",
                    }
                )

    return json.dumps(
        {"account_id": account_id, "violations": violations, "rules_checked": total_rules},
        default=str,
    )


def _find_similar_accounts(conn, args, query_logger):
    from retrieval.graph_search import find_similar_accounts as graph_find

    account_id = args.get("account_id", "")
    rows, columns = graph_find(conn, account_id, top_k=5, query_logger=query_logger)

    if not rows:
        return f"No similar accounts found for '{account_id}'"
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


def _search_knowledge_base(conn, embedding_model, args, query_logger):
    query = args.get("query", "")
    strategy = args.get("strategy", "vector")

    from retrieval.retrieval_router import route_and_retrieve

    rows, columns = route_and_retrieve(
        conn, embedding_model, query, strategy=strategy, query_logger=query_logger, top_k=5
    )
    if not rows:
        return "No results found."
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


def _get_investment_preferences(conn, args, query_logger):
    account_id = args.get("account_id", "")

    sql = """
        SELECT
            account_id, client_name,
            JSON_VALUE(metadata, '$.investment_preferences.esg_mandate') AS esg_mandate,
            JSON_VALUE(metadata, '$.investment_preferences.max_single_position') AS max_position,
            JSON_QUERY(metadata, '$.investment_preferences.preferred_sectors') AS preferred_sectors,
            JSON_QUERY(metadata, '$.investment_preferences.excluded_sectors') AS excluded_sectors,
            JSON_QUERY(metadata, '$.restricted_securities') AS restricted_list
        FROM client_accounts
        WHERE account_id = :account_id
    """

    rows, columns = execute_query(
        conn,
        sql,
        {"account_id": account_id},
        query_logger,
        description=f"JSON preferences: {account_id}",
    )

    if not rows:
        return f"No preferences found for '{account_id}'"
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


def _search_compliance_rules(conn, args, query_logger):
    keyword = args.get("keyword", "")
    category = args.get("category")

    sql = """
        SELECT rule_id, rule_name, category, description,
               threshold_type, threshold_value, regulatory_body
        FROM compliance_rules
        WHERE status = 'active'
          AND (UPPER(description) LIKE '%' || UPPER(:keyword) || '%'
               OR UPPER(rule_name) LIKE '%' || UPPER(:keyword) || '%')
    """
    params = {"keyword": keyword}

    if category:
        sql += " AND category = :category"
        params["category"] = category

    sql += " ORDER BY rule_id"

    rows, columns = execute_query(
        conn,
        sql,
        params,
        query_logger,
        description=f"Compliance rules search: {keyword}",
    )

    if not rows:
        return f"No compliance rules found for '{keyword}'"
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


def _expand_summary(memory_manager, args):
    summary_id = args.get("summary_id", "")
    summary_text = memory_manager.read_summary_memory(summary_id)
    original_msgs = memory_manager.get_messages_by_summary_id(summary_id)
    if original_msgs:
        lines = [f"[{m['role']}] {m['content']}" for m in original_msgs]
        return (
            f"Summary:\n{summary_text}\n\nOriginal messages ({len(original_msgs)}):\n"
            + "\n".join(lines)
        )
    return summary_text


def _summarize_conversation(memory_manager, llm_client, args):
    from agent.context_engineering import summarize_context_window

    thread_id = args.get("thread_id", "")
    unsummarized = memory_manager.get_unsummarized_messages(thread_id, limit=200)
    if not unsummarized:
        return "No unsummarized conversation found."

    full_text = "\n".join([f"[{m['role']}] {m['content']}" for m in unsummarized])
    result = summarize_context_window(full_text, memory_manager, llm_client)

    message_ids = [m["id"] for m in unsummarized]
    memory_manager.mark_as_summarized(thread_id, result["id"], message_ids=message_ids)

    return f"Conversation summarized as [Summary ID: {result['id']}] {result['description']} ({len(unsummarized)} messages compacted)"


def _search_tavily(args):
    """Search the web using Tavily API."""
    query = args.get("query", "")
    api_key = os.getenv("TAVILY_API_KEY", "")

    if not api_key:
        return "Tavily API key not configured. Set TAVILY_API_KEY in your .env file."

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        response = client.search(query, max_results=5)
        results = []
        for r in response.get("results", []):
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:500],
                }
            )
        return json.dumps(results, default=str)
    except Exception as e:
        return f"Tavily search error: {e}"


def _find_nearby_clients(conn, args, query_logger):
    from retrieval.spatial_search import find_nearby_clients as spatial_find

    account_id = args.get("account_id", "")
    radius_km = args.get("radius_km", 500)
    rows, columns = spatial_find(
        conn, account_id, radius_km=radius_km, top_k=10, query_logger=query_logger
    )

    if not rows:
        return f"No clients found within {radius_km}km of '{account_id}'"
    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)


def _convergent_search(conn, embedding_model, args, query_logger):
    """Convergent query: Relational + Graph + Vector + Spatial in a single SQL statement.

    Demonstrates four Oracle AI Database paradigms (relational, property graph,
    vector, spatial) in one query.  The vector CTE uses the raw-column subquery
    pattern to avoid an oracledb thin-mode bug where wrapping columns in
    functions (TO_CHAR, SUBSTR, arithmetic) in the same SELECT as
    vector_distance() causes ORA-00932.
    """
    import array

    account_id = args.get("account_id", "")
    search_phrase = args.get("search_phrase", "")

    qv = embedding_model.embed_query(search_phrase)
    query_array = array.array("f", qv)

    sql = """
        WITH
        account_info AS (
            SELECT ca.account_id, ca.client_name, ca.risk_profile,
                   ca.aum, ca.relationship_manager, ca.status,
                   JSON_VALUE(ca.metadata, '$.investment_preferences.esg_mandate') AS esg_mandate
            FROM client_accounts ca
            WHERE ca.account_id = :account_id
        ),
        graph_network AS (
            SELECT gt.target_id AS connected_account,
                   ca.client_name AS connected_name,
                   ca.risk_profile AS connected_risk,
                   gt.sim_type AS connection_type
            FROM GRAPH_TABLE(
                financial_graph
                MATCH (src IS client)-[e IS similar_to]->(dst IS client)
                WHERE src.account_id = :account_id
                COLUMNS (
                    dst.account_id AS target_id,
                    e.sim_type AS sim_type
                )
            ) gt
            JOIN client_accounts ca ON ca.account_id = gt.target_id
            FETCH FIRST 5 ROWS ONLY
        ),
        vector_results AS (
            SELECT text, metadata,
                   vector_distance(embedding, :q, COSINE) as distance
            FROM KNOWLEDGE_BASE
            ORDER BY distance
            FETCH APPROX FIRST 5 ROWS ONLY
        ),
        nearby_clients AS (
            SELECT b.account_id AS nearby_id, b.client_name AS nearby_name,
                   b.risk_profile AS nearby_risk,
                   ROUND(SDO_GEOM.SDO_DISTANCE(a.location, b.location, 0.005, 'unit=KM'), 1)
                       AS distance_km
            FROM client_accounts a, client_accounts b
            WHERE a.account_id = :account_id
              AND b.account_id <> a.account_id
              AND a.location IS NOT NULL
              AND b.location IS NOT NULL
              AND SDO_WITHIN_DISTANCE(b.location, a.location, 'distance=500 unit=KM') = 'TRUE'
            FETCH FIRST 5 ROWS ONLY
        )
        SELECT 'ACCOUNT' AS source_type, account_id AS id,
               client_name || ' | ' || risk_profile || ' | RM: ' || relationship_manager
                   || ' | AUM: ' || TO_CHAR(aum) || ' | ESG: ' || NVL(esg_mandate, 'N/A') AS detail
        FROM account_info
        UNION ALL
        SELECT 'GRAPH' AS source_type, connected_account AS id,
               connected_name || ' | ' || connected_risk || ' | via: ' || connection_type AS detail
        FROM graph_network
        UNION ALL
        SELECT 'VECTOR' AS source_type, '' AS id,
               CAST(SUBSTR(text, 1, 200) AS VARCHAR2(200)) AS detail
        FROM vector_results
        UNION ALL
        SELECT 'SPATIAL' AS source_type, nearby_id AS id,
               nearby_name || ' | ' || nearby_risk || ' | ' || TO_CHAR(distance_km) || ' km away' AS detail
        FROM nearby_clients
    """

    columns = ["SOURCE_TYPE", "ID", "DETAIL"]
    params = {"account_id": account_id, "q": query_array}

    try:
        rows, _ = execute_query(
            conn,
            sql,
            params,
            query_logger,
            description=f"Convergent (Relational + Graph + Vector + Spatial): {account_id} / '{search_phrase[:40]}'",
        )
    except Exception as e:
        return f"Convergent search error: {e}"

    if not rows:
        return f"No results found for account '{account_id}'"

    results = [dict(zip(columns, row, strict=False)) for row in rows]
    return json.dumps(results, default=str)
