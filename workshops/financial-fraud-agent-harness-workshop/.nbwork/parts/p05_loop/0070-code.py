def build_context(thread_id, user_query, k_knowledge=3):
    manifest = build_skill_manifest(user_query, k=3)
    card = store.context_card(thread_id)
    hits = retrieve_knowledge(user_query, k=k_knowledge)
    parts = [manifest.rstrip()] if manifest else []
    if card:
        parts += ["## Memory context (from OAMP)", card]
    if hits:
        parts.append("\n## Institutional knowledge (top matches)")
        parts += [f"- ({h['kind']}) {h['subject']} - {h['body'][:280]}" for h in hits]
    return "\n".join(parts + ["\n## User question", user_query])
