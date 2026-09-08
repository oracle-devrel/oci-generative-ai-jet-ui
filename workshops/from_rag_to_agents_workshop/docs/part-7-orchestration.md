# Part 7: Agent Orchestration & Chat System [Multi-Agent Architecture]

## What You Are Building

A single agent with tools is powerful. Multiple specialised agents composed together are more powerful. In this part you build a production-like multi-agent system:

1. Define specialised agents with focused scope
2. Register agents as tools on an orchestrator
3. Add a synthesiser for final answer generation
4. Build a thread-aware chat system with Oracle-backed history

## Agent-as-Tools Orchestration

This mirrors a production pattern where narrow agents perform focused work and a coordinator merges outputs:

- **research_paper_agent** — retrieves and summarises academic papers using the tools from Part 6
- **research_conversation_agent** — retrieves past analytical discussions for continuity
- **orchestrator_agent** — delegates to specialists based on query intent
- **synthesizer_agent** — produces a cohesive final response from specialist outputs

**Why specialise?** A single monolithic agent with all tools and a giant instruction set becomes unreliable at scale. Splitting responsibilities means each agent has a clear mandate, fewer tools to choose from, and simpler instructions — all of which improve routing accuracy.

### Orchestration Flow

1. User query arrives
2. Orchestrator decides which specialist(s) to invoke
3. Specialists run their tools and return structured results
4. Synthesiser combines everything into a grounded response

---

## TODO 6: Implement the Orchestrator Agent

Define the orchestrator that uses `agent.as_tool()` to register specialists as callable tools:

**Why `agent.as_tool()`?** This method wraps an entire agent — with its tools, instructions, and execution loop — as a single callable tool for the orchestrator. The orchestrator does not need to know how the specialist works internally. It just calls the tool and gets a result. This is the same encapsulation principle as wrapping SQL queries behind `@function_tool`, but at the agent level.

**Complete solution:**

```python
orchestrator_agent = Agent(
    name="research_assistant_orchestrator",
    instructions=(
        "You are a Research Orchestrator responsible for coordinating information retrieval.\n\n"
        "RULES:\n"
        "1. ALWAYS use translate_to_research_papers when a query mentions research papers, studies, or findings.\n"
        "2. ALWAYS use translate_to_research_conversations when a query mentions previous discussions.\n"
        "3. If a query requests BOTH, use BOTH tools in sequence.\n"
        "4. NEVER provide summaries without using your tools.\n"
        "5. After retrieving, synthesize into a cohesive summary with citations."
    ),
    tools=[
        research_paper_agent.as_tool(
            tool_name="translate_to_research_papers",
            tool_description="Retrieve and summarize relevant academic research papers.",
        ),
        research_conversation_agent.as_tool(
            tool_name="translate_to_research_conversations",
            tool_description="Retrieve past research discussions related to the topic.",
        ),
    ],
)
```

**Key concept:** The orchestrator's instructions determine which specialist gets called. If the instructions are vague ("use the tools as needed"), the orchestrator will make inconsistent choices. If the instructions are specific ("for new research questions, call the paper agent first; for follow-up questions about prior analysis, call the conversation agent"), routing becomes reliable.

## Agentic Chat System

The chat system adds thread-aware conversation handling on top of orchestration:

1. **Store** the user's message in Oracle (`chat_history` table)
2. **Reconstruct** conversation context by `thread_id`
3. **Run** orchestration + synthesis with full context
4. **Save** the assistant response back to Oracle

This gives long-running research sessions continuity — the agent remembers what was discussed across multiple turns.

### Chat History Table

```sql
CREATE TABLE chat_history (
    id VARCHAR2(100) PRIMARY KEY,
    thread_id VARCHAR2(100) NOT NULL,
    role VARCHAR2(20) NOT NULL,
    message CLOB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Why `CLOB` for message?** Agent responses can be long — especially when synthesising multiple specialist outputs. `CLOB` stores up to 4GB of text, so message length is never a constraint.

**Why `thread_id`?** Every read and write is scoped to a thread. Two concurrent users with different thread IDs have completely separate conversation histories. This is the same isolation pattern used in production chat systems.

## Interactive Chat Session

The `research_chat_session()` function provides a REPL-style interface where you can have multi-turn conversations with the agent system. Each turn runs the full orchestration pipeline and persists both the query and response to Oracle.

## Troubleshooting

**"RuntimeError: This event loop is already running"** — Make sure `nest_asyncio.apply()` is called before running async functions in the notebook. This is a Jupyter-specific issue — the notebook already has an event loop running, and `nest_asyncio` patches it to allow nested `await` calls.

**Agent not calling specialist tools** — Review the orchestrator instructions. They must explicitly describe when to use each specialist tool. Vague instructions lead to inconsistent routing.

**Chat history not persisting** — Check that the `chat_history` table was created and that `conn.commit()` is called after each insert.
