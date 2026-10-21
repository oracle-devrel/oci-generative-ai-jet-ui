# TODO 2: fill in the two marked lines (the rest is written for you).
#   Line 1: set `flt` to the metadata filter: the dict {"kind": kind} when `kind` is given, otherwise None.
#   Line 2: set `hits = memory_client.search(query, ...)` and pass these keyword arguments:
#     user_id=USER_ID, agent_id=AGENT_ID  -> whose memories to search (the operator and this agent)
#     record_types=["memory"]             -> stored facts only, not chat messages
#     metadata_filter=flt                 -> dict a memory's metadata must match, e.g. {"kind": "column"}; None = no filter
#     max_results=k                       -> how many hits to return
#   `hits` is a list of results with .id, .content, .distance and .metadata (a dict or None).
#   Guide: docs/part-2-oamp-memory.md#todo-2-recall_memories
def recall_memories(query, k=3, kind=None):
    flt = ...  # TODO 2a: {"kind": kind} if kind is given, else None
    raise NotImplementedError("TODO 2b: hits = memory_client.search(query, user_id=..., agent_id=..., record_types=..., metadata_filter=flt, max_results=k)")
    return [{"id": h.id, "kind": (h.metadata or {}).get("kind"),
             "subject": (h.metadata or {}).get("subject"),
             "body": h.content, "distance": h.distance} for h in hits]
