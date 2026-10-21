# See retrieve_tools in action, now that the core tools are registered: for each question, the tools the agent
# would be offered on that turn. The first ones are the closest by meaning; "(always on)" ones are added every turn.
for q in ("scan the CRM schema, I have never seen it before",
          "the last tool result was cut off, show me all of it",
          "link these two memories, the second one supports the first"):
    names = [s["function"]["name"] for s in retrieve_tools(q, k=2)]
    print(f"{q}\n   -> " + ", ".join(n + (" (always on)" if n in ALWAYS_ON_TOOLS else "") for n in names))
