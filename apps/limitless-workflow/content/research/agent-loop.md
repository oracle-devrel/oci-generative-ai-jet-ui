# Agent Loop: The Operating Cycle of a Tool-Using Developer Agent

## Why the agent loop matters

An agent is not just a model call. It is a repeating operating cycle that turns a goal into action, evaluates the result, and updates state before continuing. In developer workflows, the quality of an agent often depends less on one clever prompt and more on whether the loop is structured well enough to keep context, pick the right tools, inspect results, and learn from what happened.

For the Limitless demo, the agent loop is the secondary topic that proves the system can map knowledge across more than one subject. It is intentionally lighter than `agent memory`, but it still needs a real conceptual shape.

## Core loop

The tool-using developer agent loop for this project is:

1. **Goal** — what the agent is trying to achieve
2. **Context retrieval** — what information it needs right now
3. **Tool selection** — which capability should be used
4. **Execution** — the action taken in the environment
5. **Evaluation** — whether the outcome was useful or correct
6. **Memory update** — what should persist after the turn

## Why it connects to memory

The loop only becomes stateful when it can carry useful information across turns and sessions. That is why `agent loop` and `agent memory` belong together.

- `semantic memory` supports **context retrieval**
- `procedural memory` supports **tool selection** and **execution**
- `episodic memory` supports **evaluation** and **memory update**

## Friday role in the demo

`agent loop` is not the deep live learning topic for Friday. Instead, it acts as the visible secondary topic in Oracle and Obsidian so the audience can see that the knowledge graph is a broader system rather than a single curated note stack.
