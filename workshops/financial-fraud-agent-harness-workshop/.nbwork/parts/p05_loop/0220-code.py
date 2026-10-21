import uuid

thread_id = f"demo-{uuid.uuid4().hex[:8]}"   # a fresh thread, so no earlier run answers for the model
questions = [
    "What's in the FINANCE schema? Briefly: list the entities and how they relate.",
    "Which branch regions have the most FLAGGED or BLOCKED transactions? Show me a small table sorted by count desc.",
]
for q in questions:
    print("USER:", q)
    print("\nASSISTANT:", agent_turn(q, thread_id=thread_id), "\n")
