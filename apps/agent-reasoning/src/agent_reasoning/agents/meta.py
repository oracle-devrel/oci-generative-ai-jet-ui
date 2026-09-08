import re

from termcolor import colored

from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.visualization.models import MetaClassification, StreamEvent


class MetaReasoningAgent(BaseAgent):
    """Meta-reasoning: classifies queries and routes to optimal strategy."""

    ROUTING_TABLE = {
        "math": "cot",
        "logic": "tot",
        "creative": "reflection",
        "factual": "react",
        "multi_step": "decomposed",
        "code": "recursive",
        "debate_worthy": "debate",
        "analogical": "analogical",
        "philosophical": "socratic",
        "planning": "least_to_most",
        "general": "cot",
    }

    def __init__(self, model="gemma3:270m", **kwargs):
        super().__init__(model, **kwargs)
        self.name = "MetaReasoningAgent"
        self.color = "white"

    def _classify_query(self, query):
        """Classify query into a category using a single LLM call."""
        categories = ", ".join(self.ROUTING_TABLE.keys())
        prompt = (
            f"Classify this query into exactly ONE category.\n"
            f"Categories: {categories}\n\n"
            f"Query: {query}\n\n"
            f"Output format:\nCATEGORY: <category>\nCONFIDENCE: <0.0-1.0>\nREASON: <brief reason>"
        )
        response = ""
        for chunk in self.client.generate(prompt, stream=False):
            response += chunk

        cat_match = re.search(r"CATEGORY:\s*(\w+)", response, re.IGNORECASE)
        conf_match = re.search(r"CONFIDENCE:\s*([\d.]+)", response)
        reason_match = re.search(r"REASON:\s*(.*?)(?:\n|$)", response)

        query_type = cat_match.group(1).lower() if cat_match else "general"
        if query_type not in self.ROUTING_TABLE:
            query_type = "general"

        return {
            "query_type": query_type,
            "confidence": float(conf_match.group(1)) if conf_match else 0.5,
            "reasoning": reason_match.group(1).strip() if reason_match else "",
        }

    def run(self, query):
        self.log_thought(f"Meta-reasoning on query: {query}")
        full_response = ""
        for chunk in self.stream(query):
            print(colored(chunk, self.color), end="", flush=True)
            full_response += chunk
        print()
        return full_response

    def stream(self, query):
        """Yield text chunks for terminal streaming."""
        for event in self.stream_structured(query):
            if event.event_type == "text":
                yield event.data

    def stream_structured(self, query):
        """Structured event streaming for visualization."""
        # Lazy import to avoid circular dependency with agents __init__
        from agent_reasoning.agents import AGENT_MAP

        yield StreamEvent(event_type="query", data=query)
        yield StreamEvent(event_type="text", data="Meta-Reasoning: classifying query...\n")

        # Classify
        classification = self._classify_query(query)
        strategy = self.ROUTING_TABLE[classification["query_type"]]

        meta = MetaClassification(
            query_type=classification["query_type"],
            confidence=classification["confidence"],
            selected_strategy=strategy,
            reasoning=classification["reasoning"],
        )
        yield StreamEvent(event_type="meta_classification", data=meta)
        yield StreamEvent(
            event_type="text",
            data=f"\nClassification: {classification['query_type']} "
            f"(confidence: {classification['confidence']:.1f})\n"
            f"Selected strategy: {strategy}\n"
            f"Reason: {classification['reasoning']}\n\n",
        )

        # Route to selected agent
        agent_class = AGENT_MAP.get(strategy)
        if not agent_class:
            yield StreamEvent(
                event_type="text",
                data=f"Unknown strategy {strategy}, falling back to CoT\n",
            )
            from agent_reasoning.agents.cot import CoTAgent

            agent_class = CoTAgent

        agent = agent_class(model=self.client.model)

        yield StreamEvent(event_type="text", data=f"--- Delegating to {agent.name} ---\n\n")

        # Delegate and forward all events
        for event in agent.stream_structured(query):
            yield event
