# Part 6: Agent Execution

## Two TODOs in This Part

Part 6 has two TODOs. Complete them in order before running the agent.

---

## TODO 15: `build_context()`

This is the most important function in the entire workshop. It assembles everything you built across Parts 1-5 into a single string that gets sent to the LLM on every inference call.

**Complete solution:**

```python
def build_context() -> str:
    ctx = f"# Question\n{query}\n\n"
    ctx += memory_manager.read_conversational_memory(thread_id) + "\n\n"
    ctx += memory_manager.read_knowledge_base(query) + "\n\n"
    ctx += memory_manager.read_workflow(query) + "\n\n"
    ctx += memory_manager.read_entity(query) + "\n\n"
    ctx += memory_manager.read_summary_context(query) + "\n\n"
    return ctx
```

**Why this order matters:** The LLM reads the context top to bottom. The current question comes first so the model always knows what it is answering. Conversational memory follows — the most immediately relevant context. Knowledge base, workflow, and entity memory provide supporting detail. Summary context comes last because it is the least dense — just reference pointers the agent can choose to expand if needed.

**Why it is rebuilt on every iteration:** Memory state changes during the tool-call loop. After a web search, new content is written to the knowledge base. After a summarisation, the conversational memory shrinks. Rebuilding from scratch ensures the LLM always sees the current state of memory, not a stale snapshot from the start of the turn.

---

## TODO 16: Five Questions Before the Memory Recall Test

The final test cell asks the agent `"What was my first question to you"`. For this to work, the agent needs prior conversational memory to recall — which means you need to ask it questions first.

Your task is to add 5 `call_agent()` calls using the same `thread_id="0022"` before the recall question. All 6 calls form a single thread of conversation that the agent accumulates in memory.

**Why the same thread_id matters:** Every read and write in the `MemoryManager` is scoped to `thread_id`. If you use different thread IDs, each call starts with an empty memory slate and the recall question will always fail. Using the same ID across all 6 calls is what builds the conversation the agent needs to remember.

**Choosing good questions:** Pick questions that demonstrate different memory types in action:

| Question type                 | Memory type it exercises           |
| ----------------------------- | ---------------------------------- |
| "Find papers about X"         | Knowledge base, entity memory      |
| "What did we just discuss?"   | Conversational memory              |
| "Search the web for Y"        | Tavily tool, knowledge base write  |
| "Summarise everything so far" | Summary memory, context compaction |
| "Tell me more about Z"        | Workflow memory, entity memory     |

**Example solution** (use your own questions — the content matters for the comparison chart):

```python
call_agent("Find me research papers about reinforcement learning for robotics", thread_id="0022")
call_agent("What were the main themes in those papers?", thread_id="0022")
call_agent("Search the web for recent advances in robot locomotion in 2025", thread_id="0022")
call_agent("Which authors appear most frequently in this research area?", thread_id="0022")
call_agent("Summarise everything we have discussed so far", thread_id="0022")

# Final question — tests whether conversational memory is working correctly
call_agent("What was my first question to you", thread_id="0022")
```

The agent should correctly recall your first question. If it cannot, check that all calls used the same `thread_id` and that `write_conversational_memory` was correctly implemented in Part 3.

---

## The Agent Harness Architecture

`call_agent()` implements a turn-level agent loop. Here is the full flow on each call:

```
1. BUILD CONTEXT (programmatic — always runs)
   ├── Read conversational memory (recent unsummarised turns for this thread)
   ├── Read knowledge base (top-k relevant documents for the current query)
   ├── Read workflow memory (relevant procedural patterns)
   ├── Read entity memory (relevant named entities)
   └── Assemble system prompt with all retrieved context  ← YOUR TODO 16

2. TOOL SELECTION (programmatic)
   └── Retrieve relevant tools from TOOLBOX_MEMORY using the query as a search key
       (semantic retrieval — only tools relevant to this task)

3. LLM CALL
   └── Send assembled context + tool definitions to the model

4. TOOL-CALL LOOP (agent-triggered)
   ├── If the model returns tool_calls:
   │   ├── Execute each tool
   │   ├── Log output to TOOL_LOG (programmatic)
   │   ├── Check context window usage
   │   ├── Offload to summary if usage > 80% (programmatic)
   │   └── Loop back to LLM with tool results
   └── If no tool_calls: proceed to final response

5. WRITE MEMORY (programmatic — always runs)
   ├── Write user message to CONVERSATIONAL_MEMORY
   └── Write assistant response to CONVERSATIONAL_MEMORY

6. RETURN final response
```

## Key Design Decisions to Notice

**Thread isolation:** Each call takes a `thread_id`. All memory reads and writes are scoped to that thread. Two concurrent users with different thread IDs have completely separate memory spaces.

**Iteration cap:** `max_iterations=10` prevents infinite tool-call loops. If the agent has not resolved the task in 10 iterations, it returns whatever it has. Adjust this for complex tasks.

**Context window tracking:** `context_size_history` is a list that persists across calls. The chart after the agent calls reads from this list to show cumulative context growth across all 6 turns.

**Programmatic vs agent-triggered boundary:** Memory writes always happen (programmatic). Memory reads for knowledge, workflow, and entities happen programmatically at the start of each turn. Tool calls happen only when the model decides to invoke them.

## The Naive Baseline Comparison

After your 6-question sequence, the notebook runs `call_agent_naive()` — an identical agent except it:

- Does not read or write any memory
- Appends every message and tool result to a single growing list
- Makes no attempt to manage context window size

The comparison chart plots context token growth for both agents across the same queries. You should see:

- **Memory-engineered agent:** relatively flat or controlled growth due to summarisation and selective retrieval
- **Naive agent:** continuous upward growth until it would eventually hit the token limit

This chart is the clearest visual argument for why memory engineering matters. The more questions you ask in TODO 16, the more pronounced the difference will be.

## Key Takeaways

**Memory is infrastructure, not a feature.** The `MemoryManager` is not an optional add-on — without it the agent cannot function across turns. Oracle AI Database provides the persistence layer that makes this infrastructure reliable, queryable, and scalable.

**Context engineering is the other half.** Storing memory is easy. Deciding what to retrieve, when to retrieve it, and when to compress is where the engineering work lives.

**The database is the right abstraction.** You could implement this with flat files or Redis. But Oracle gives you SQL queries over your memory, ACID consistency, vector search, and a single system of record. For production agents, that matters.

**The toolbox pattern scales.** With 5 tools it feels like overhead. With 50 tools it becomes essential. The toolbox pattern is the foundation for building agents that can operate across large, composable tool libraries.
