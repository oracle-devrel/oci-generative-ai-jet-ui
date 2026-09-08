# Part 11 — `OracleChatMessageHistory` — durable session transcripts

## When _not_ to reach for LangGraph

The whole notebook so far has been about LangGraph state machines —
supervisor, specialists, checkpointed turns, hierarchical memory. But
plenty of real apps don't need that. Customer-support chatbots,
internal Slack-style assistants, single-prompt agents — these are
linear conversations where all you want is:

> _"Append this message to session `X` and persist it. Replay session `X`
> on reconnect."_

That's `OracleChatMessageHistory`. It's a separate, lower-level
primitive — not part of any LangGraph loop.

## How it differs from the checkpointer

|             | `AsyncOracleSaver` (LangGraph)                                         | `OracleChatMessageHistory`                         |
| ----------- | ---------------------------------------------------------------------- | -------------------------------------------------- |
| Stores      | Full agent graph state (channel writes, tool outputs, sub-graph state) | Just the chat messages                             |
| Keyed by    | `thread_id` (LangGraph internal)                                       | `session_id` (your choice)                         |
| API style   | `agent.ainvoke(..., config={"thread_id": ...})`                        | `history.add_messages([...])` + `history.messages` |
| Async-only? | Yes                                                                    | No — **sync only**                                 |
| When to use | Multi-step agent                                                       | Plain chatbot                                      |

## How it's wired

```python
from langchain_core.messages import AIMessage, HumanMessage
from langchain_oracledb.chat_message_histories import OracleChatMessageHistory

session_id = "planner-priya-2026Q3"
history = OracleChatMessageHistory(
    session_id=session_id,
    client=oracle_client,            # reuse the sync OracleVS connection
    table_name="langchain_planner_chat",
)
history.clear()                      # idempotent

history.add_messages([
    HumanMessage(content="..."),
    AIMessage(content="..."),
])
```

Reopening with the same `session_id` returns the same conversation:

```python
history2 = OracleChatMessageHistory(
    session_id=session_id,
    client=oracle_client,
    table_name="langchain_planner_chat",
)
assert len(history2.messages) == len(history.messages)
```

That's the whole API. No `setup()`, no migrations, no index config —
just one table per `table_name`, keyed by `session_id`.

## Connection sharing

Notice we pass the same `oracle_client` we used for `OracleVS` and
`OracleSemanticCache`. All three sync primitives share one connection
to keep the workshop's surface area small. In production you'd
typically pass an `oracledb.ConnectionPool` instead so concurrent
sessions don't serialize on a single connection.

## Why this primitive exists at all

LangChain has a notion of `BaseChatMessageHistory` that pre-dates
LangGraph. Many older chains, retrievers, and `RunnableWithMessageHistory`
wrappers expect this exact interface. Having an Oracle-backed
implementation means those older patterns work without a custom
adapter.

## No TODO in this part

This part is reference material. Read the cell, run it, watch the
"reopened session" recovery work. Move on.

## Next

→ **[Part 12 — Teardown](TODO-checklist.md#part-12--teardown)** — close the three connections and you're done.
