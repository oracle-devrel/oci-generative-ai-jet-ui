@register
def tool_remember(subject: str, body: str, kind: str = "correction", supersedes: str = "") -> str:
    """Persist a correction or learning. Pass `supersedes` (id or phrase) when it replaces an earlier memory: OAMP retires the old one."""
    return wt.remember(agent_conn, memory_client, write_facts, Fact, USER_ID, AGENT_ID, subject, body, kind, supersedes)

@register
def tool_link_memories(source: str, target: str, link_type: str = "supports", reason: str = "") -> str:
    """Link two memories (ids or phrases). supports/contradicts keep both current; supersedes/refines/duplicates retire the target."""
    return wt.link_memories(memory_client, USER_ID, AGENT_ID, source, target, link_type, reason)

@register
def tool_fetch_tool_output(tool_call_id: str) -> str:
    """Recover the full output of an earlier tool call when the prompt shows a truncation marker (the id is printed in the marker)."""
    return store.fetch_tool_output(tool_call_id)   # `store` is created in 5.1
