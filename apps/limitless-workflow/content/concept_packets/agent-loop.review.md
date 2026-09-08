# Agent Loop Reviewed Concept Packet

**Topic:** Agent Loop  
**Grounding label:** Agent Loop brief  
**Source report:** `content/research/agent-loop.md`

## Goal
- Summary: The explicit objective the agent is trying to achieve in the current loop.
- Supporting snippet: "A tool-using developer agent starts by orienting around a clear goal rather than wandering through tools without intent."
- Diagnostic prompt: What role does a goal play in an agent loop?
- Hint / reframe: Think about what the agent is trying to accomplish before it chooses any tools.
- Related concepts: `context-retrieval`

## Context Retrieval
- Summary: The step where the agent pulls in the relevant state, memory, or research needed for the current turn.
- Supporting snippet: "The loop becomes stateful when the agent can retrieve the right context instead of reprocessing everything every time."
- Diagnostic prompt: Why is context retrieval a distinct step in the loop?
- Hint / reframe: Think about bringing the right information into the active context at the right time.
- Related concepts: `semantic-memory`, `goal`

## Tool Selection
- Summary: The choice of which capability or tool best fits the current subproblem.
- Supporting snippet: "A strong agent loop does not just think; it chooses the right capability for the situation."
- Diagnostic prompt: What makes tool selection different from execution?
- Hint / reframe: Think about deciding what to use before you actually use it.
- Related concepts: `procedural-memory`, `execution`

## Execution
- Summary: The moment where the agent acts in the environment by running a tool, querying data, or changing state.
- Supporting snippet: "Execution is the point where an agent turns intention into action."
- Diagnostic prompt: What happens during execution in an agent loop?
- Hint / reframe: Think about the difference between planning an action and actually doing it.
- Related concepts: `tool-selection`, `procedural-memory`

## Evaluation
- Summary: The judgment step where the agent checks whether the result was useful, correct, or complete.
- Supporting snippet: "An agent loop remains brittle if it cannot inspect the result and judge whether it worked."
- Diagnostic prompt: Why is evaluation necessary after execution?
- Hint / reframe: Think about checking the result rather than assuming the action succeeded.
- Related concepts: `episodic-memory`, `memory-update`

## Memory Update
- Summary: The persistence step where the agent decides what should be retained after the loop finishes.
- Supporting snippet: "The loop only becomes stateful when the system decides what should persist after the turn."
- Diagnostic prompt: What should happen during memory update in an agent loop?
- Hint / reframe: Think about what information deserves to survive beyond the current turn.
- Related concepts: `episodic-memory`, `evaluation`
