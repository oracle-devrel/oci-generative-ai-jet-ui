"""Oracle Text CONTAINS() full-text keyword search."""

import re

from database.query_helper import execute_query

_ORACLE_TEXT_RESERVED = {
    "and",
    "or",
    "not",
    "near",
    "within",
    "about",
    "fuzzy",
    "soundex",
    "stem",
    "syn",
    "tr",
    "trsyn",
    "tt",
    "bt",
    "nt",
    "rt",
    "sq",
    "pt",
    "equiv",
    "minus",
    "threshold",
    "weight",
    "accum",
    "haspath",
    "inpath",
    "definescore",
    "sdata",
}


def _sanitize_for_oracle_text(query, max_terms=12):
    """Sanitize a natural-language query for use in Oracle Text CONTAINS().

    Oracle Text special characters like ( ) : % { } [ ] & | ! ~ * ? $ > , . ; /
    crash the parser if passed raw.  Words like 'and', 'or', 'not' are reserved
    operators and also cause syntax errors when mixed with the AND join.

    This function:
    1. Strips all special characters
    2. Removes Oracle Text reserved words
    3. Wraps each word in {} to force literal interpretation
    4. Limits to max_terms most significant words
    5. Joins with ACCUM (score by number of matching terms, not all-must-match)
    """
    # Remove all non-alphanumeric characters except spaces
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", query)
    # Split into words, drop empties, short tokens, and reserved words
    words = [w for w in cleaned.split() if len(w) >= 2 and w.lower() not in _ORACLE_TEXT_RESERVED]
    if not words:
        return "{search}"
    # Deduplicate while preserving order, limit length
    seen = set()
    unique = []
    for w in words:
        wl = w.lower()
        if wl not in seen:
            seen.add(wl)
            unique.append(w)
    unique = unique[:max_terms]
    # Wrap each term in {} for literal escaping, join with ACCUM
    # ACCUM scores by how many terms match (better for natural language)
    return " ACCUM ".join(f"{{{w}}}" for w in unique)


def keyword_search(conn, keyword, top_k=10, query_logger=None):
    """Full-text keyword search using Oracle Text index on KNOWLEDGE_BASE."""
    safe_keyword = _sanitize_for_oracle_text(keyword)

    sql = """
        SELECT
            id, text,
            SUBSTR(text, 1, 200) AS snippet,
            SCORE(1) AS relevance_score
        FROM KNOWLEDGE_BASE
        WHERE CONTAINS(text, :keyword, 1) > 0
        ORDER BY SCORE(1) DESC
        FETCH FIRST :top_k ROWS ONLY
    """

    return execute_query(
        conn,
        sql,
        {"keyword": safe_keyword, "top_k": top_k},
        query_logger,
        description=f"Oracle Text search: '{keyword[:50]}'",
    )


def keyword_search_accounts(conn, keyword, top_k=10, query_logger=None):
    """Full-text keyword search on client account metadata."""
    safe_keyword = _sanitize_for_oracle_text(keyword)

    sql = """
        SELECT
            account_id, client_name,
            SUBSTR(metadata, 1, 200) AS snippet,
            SCORE(1) AS relevance_score
        FROM client_accounts
        WHERE CONTAINS(metadata, :keyword, 1) > 0
        ORDER BY SCORE(1) DESC
        FETCH FIRST :top_k ROWS ONLY
    """

    return execute_query(
        conn,
        sql,
        {"keyword": safe_keyword, "top_k": top_k},
        query_logger,
        description=f"Account text search: '{keyword[:50]}'",
    )
