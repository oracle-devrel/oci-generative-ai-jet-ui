# TODO 2: implement recall_memories(query, k=3, kind=None) -> list[dict]
def recall_memories(query, k=3, kind=None):
    flt = {"kind": kind} if kind else None
    hits = memory_client.search(
        query, user_id=USER_ID, agent_id=AGENT_ID, record_types=["memory"],
        metadata_filter=flt, max_results=k)
    return [{"id": h.id, "kind": (h.metadata or {}).get("kind"),
             "subject": (h.metadata or {}).get("subject"),
             "body": h.content, "distance": h.distance} for h in hits]
