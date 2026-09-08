# Agent Memory Reviewed Concept Packet

**Topic:** Agent Memory  
**Grounding label:** Agent Memory research  
**Source report:** `content/research/agent-memory.md`

## Episodic Memory

### Summary
Episodic memory stores specific prior experiences, action traces, and outcomes so an agent can remember what happened before and learn from it.

### Supporting snippets
- "Episodic memory stores records of specific experiences, including prior conversations, action-observation traces, failed attempts, successful workflows, timestamps, outcomes, and contextual narratives of what happened."
- "If an agent remembers that on March 4 it attempted a database migration, hit a permission error, and resolved it by switching credentials, that is episodic memory."

### Diagnostic prompts
- What is episodic memory in an AI agent, in your own words?
- How is episodic memory different from semantic memory?
- Give me an example of something an agent should store as an episode rather than a fact.

### Hint / reframe ladder
- Think about a specific event an agent went through, not a general rule.
- Reframe it as the agent's memory of a past attempt, failure, or success.
- Try again using the words event, experience, or prior run.

### Related concepts
- `semantic-memory`
- `evaluation`
- `memory-update`

## Semantic Memory

### Summary
Semantic memory stores generalized knowledge such as user preferences, domain facts, policies, and stable concepts that should persist across sessions.

### Supporting snippets
- "Semantic memory stores generalized knowledge, including factual information about the user, domain concepts, world knowledge, business rules, environment state, and distilled abstractions derived from repeated experience."
- "Semantic memory is what gives an agent stability. Without it, every interaction becomes an exercise in rediscovery."

### Diagnostic prompts
- What does semantic memory hold in an agent system?
- Why isn't a long context window the same thing as semantic memory?
- Give an example of a stable fact or preference an agent should remember semantically.

### Hint / reframe ladder
- Think about generalized knowledge, not one-off events.
- Reframe around facts, preferences, or rules that should stay true across sessions.
- Try again using the phrase stable knowledge.

### Related concepts
- `episodic-memory`
- `procedural-memory`
- `context-retrieval`

## Procedural Memory

### Summary
Procedural memory stores how-to knowledge: reusable action patterns, tool routines, workflow templates, and skill-like behaviors that let an agent carry out tasks more reliably over time.

### Supporting snippets
- "Procedural memory stores how-to knowledge. It is the memory of action patterns, tool-usage sequences, reusable plans, workflow templates, prompts, routing heuristics, and learned policies."
- "An agent that remembers facts but forgets methods remains fragile."

### Diagnostic prompts
- What is procedural memory in an agent, and how is it different from semantic memory?
- Why does procedural memory matter for tool-using agents?
- Can you connect procedural memory to skills, routines, or reusable workflows?

### Hint / reframe ladder
- Think about how to do something, not what something is.
- Reframe it as repeatable behavior: tools, routines, workflows, or skills.
- Try again by contrasting facts with methods.

### Related concepts
- `semantic-memory`
- `tool-selection`
- `execution`
