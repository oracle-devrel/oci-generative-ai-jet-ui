@register
def tool_scan_database(owner: str) -> str:
    """Scan a schema and update institutional knowledge. Use it for a schema you have never seen or when knowledge is stale."""
    return json.dumps(run_scan(agent_conn, owner=owner))

@register
def tool_search_knowledge(query: str, k: int = 5, kinds: list[str] | None = None) -> str:
    """Search institutional knowledge by semantic similarity. Use it BEFORE running SQL to find relevant tables and columns."""
    return wt.search_knowledge(retrieve_knowledge, query, k, kinds)

@register
def tool_load_skill(name: str) -> str:
    """Load the full content of a named skill from the skillbox. `name` is the full namespace, e.g. "agent/schema-discovery"."""
    return wt.load_skill(agent_conn, name)
