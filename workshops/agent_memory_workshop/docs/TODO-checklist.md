# Workshop TODO Checklist

16 hands-on tasks across Parts 2–6. Complete them in order — each builds on the last.

Part 1 (Oracle setup) is pre-built — just run the cells to connect.

---

### Part 2 — Vector Search ([Guide](part-2-vector-search.md))

1. Initialise `OracleVS` vector store (TODO 1)
2. Append to the three ingestion lists (TODO 2)
3. Basic similarity search, `k=3` (TODO 3)
4. Similarity search with scores (TODO 4)
5. Filtered search by ID list (TODO 5)

### Part 3 — Memory Engineering ([Guide](part-3-memory-engineering.md))

6. Create conversational history SQL table (TODO 6)
7. Create 5 `OracleVS` memory stores (TODO 7)
8. `write_conversational_memory` — SQL INSERT (TODO 8)
9. `write_knowledge_base` — vector add (TODO 9)
10. `write_workflow` — structured vector add (TODO 10)
11. `write_entity` — direct entity storage (TODO 11)

### Part 4 — Context Engineering ([Guide](part-4-context-engineering.md))

12. Implement `calculate_context_usage` (TODO 12)
13. Write the summarisation prompt (TODO 13)

### Part 5 — Web Search ([Guide](part-5-web-search.md))

14. Register `search_tavily` tool with Tavily (TODO 14)

### Part 6 — Agent Execution ([Guide](part-6-agent-execution.md))

15. Assemble `build_context()` from all memory types (TODO 15)
16. Run 5 test questions before memory recall (TODO 16)
