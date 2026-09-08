"""Reasoning Circuits: compose agents into multi-stage reasoning pipelines."""

from typing import Any, Dict, Generator, List

from agent_reasoning.visualization.models import CircuitNode, StreamEvent, TaskStatus

CIRCUIT_TEMPLATES = {
    "deep_analysis": [
        {"step": "decompose", "agent": "decomposed"},
        {"step": "solve_each", "agent": "cot"},
        {"step": "verify", "agent": "reflection"},
    ],
    "robust_answer": [
        {"step": "parallel_solve", "agent": ["cot", "tot", "react"], "parallel": True},
        {"step": "verify", "agent": "reflection"},
    ],
    "creative_exploration": [
        {"step": "brainstorm", "agent": "analogical"},
        {"step": "debate", "agent": "debate"},
        {"step": "refine", "agent": "refinement"},
    ],
}


class ReasoningCircuit:
    """A composable reasoning pipeline defined as a sequence of agent steps."""

    def __init__(self, steps: List[Dict[str, Any]], model: str = "gemma3:latest"):
        self.steps = steps
        self.model = model

    @classmethod
    def from_template(cls, template_name: str, model: str = "gemma3:latest"):
        if template_name not in CIRCUIT_TEMPLATES:
            raise ValueError(
                f"Unknown template: {template_name}. Available: {list(CIRCUIT_TEMPLATES.keys())}"
            )
        return cls(CIRCUIT_TEMPLATES[template_name], model=model)

    def run(self, query: str) -> str:
        """Execute the circuit and return final answer."""
        result = ""
        for event in self.stream_structured(query):
            if event.event_type == "final":
                result = event.data
        return result

    def stream(self, query: str) -> Generator[str, None, None]:
        """Legacy text streaming."""
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data

    def stream_structured(self, query: str) -> Generator[StreamEvent, None, None]:
        """Execute circuit with structured event streaming."""
        # Import AGENT_MAP lazily to avoid circular imports
        from agent_reasoning.agents import AGENT_MAP

        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(
            event_type="text", data=f"Reasoning Circuit ({len(self.steps)} steps)...\n"
        )

        context = query  # Accumulated context passed between steps
        final_answer = ""

        for i, step in enumerate(self.steps):
            step_name = step.get("step", f"step_{i}")
            agent_spec = step.get("agent", "standard")

            node = CircuitNode(
                node_id=f"circuit_{i}",
                node_type="parallel_map" if step.get("parallel") else "agent",
                strategy=str(agent_spec),
                status=TaskStatus.RUNNING,
                input_summary=context[:100],
            )
            yield StreamEvent(event_type="circuit_node", data=node)
            yield StreamEvent(
                event_type="text",
                data=f"\n--- Circuit Step {i + 1}: {step_name} ({agent_spec}) ---\n",
            )

            if isinstance(agent_spec, list) and step.get("parallel"):
                # Parallel execution of multiple agents
                results = []
                for agent_name in agent_spec:
                    agent_class = AGENT_MAP.get(agent_name)
                    if not agent_class:
                        yield StreamEvent(
                            event_type="text", data=f"  Unknown agent: {agent_name}, skipping\n"
                        )
                        continue
                    agent = agent_class(model=self.model)
                    result = agent.run(context)
                    results.append((agent_name, result))
                    yield StreamEvent(
                        event_type="text", data=f"  [{agent_name}]: {result[:100]}...\n"
                    )

                # Combine results as context for next step
                context = "\n\n".join([f"[{name}]: {r}" for name, r in results])
                final_answer = context
            else:
                # Single agent execution
                agent_name = agent_spec if isinstance(agent_spec, str) else agent_spec[0]
                agent_class = AGENT_MAP.get(agent_name)
                if not agent_class:
                    yield StreamEvent(event_type="text", data=f"  Unknown agent: {agent_name}\n")
                    continue

                agent = agent_class(model=self.model)

                # Forward structured events from sub-agent
                step_result = ""
                for event in agent.stream_structured(context):
                    if event.event_type == "final":
                        step_result = event.data
                    elif event.event_type == "text":
                        yield event

                context = step_result if step_result else context
                final_answer = context

            node.status = TaskStatus.COMPLETED
            node.output_summary = final_answer[:100] if final_answer else ""
            yield StreamEvent(event_type="circuit_node", data=node, is_update=True)

        yield StreamEvent(event_type="text", data="\n--- Circuit Complete ---\n")
        yield StreamEvent(event_type="final", data=final_answer)
