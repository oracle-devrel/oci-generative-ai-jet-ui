"""Agent chaining: compose multiple reasoning strategies sequentially.

Allows piping the output of one agent into the next, building
multi-strategy pipelines. Example: decompose -> reflect -> refine.
"""

from dataclasses import dataclass, field

from agent_reasoning.interceptor import AGENT_MAP


@dataclass
class ChainStep:
    """One step in an agent chain."""

    strategy: str
    output: str = ""
    elapsed_ms: float = 0.0


@dataclass
class ChainResult:
    """Result from running an agent chain."""

    steps: list[ChainStep] = field(default_factory=list)
    final_output: str = ""
    total_ms: float = 0.0

    @property
    def step_count(self) -> int:
        return len(self.steps)


class AgentChain:
    """Chain multiple reasoning strategies together.

    Each strategy receives the output of the previous one as context,
    building on prior reasoning.

    Args:
        strategies: List of strategy names (must be in AGENT_MAP)
        model: LLM model name (default "gemma3:270m")

    Example:
        chain = AgentChain(["decomposed", "reflection"], model="gemma3:270m")
        result = chain.run("Plan and review a project timeline")
        print(result.final_output)
    """

    def __init__(self, strategies: list[str], model: str = "gemma3:270m"):
        # Validate strategies
        for s in strategies:
            if s not in AGENT_MAP:
                raise ValueError(f"Unknown strategy: {s}")
        self.strategies = strategies
        self.model = model

    def run(self, query: str) -> ChainResult:
        """Run the chain synchronously, piping outputs forward."""
        import time

        result = ChainResult()
        current_input = query
        total_start = time.time()

        for strategy_name in self.strategies:
            step_start = time.time()
            agent_class = AGENT_MAP[strategy_name]
            agent = agent_class(model=self.model)

            # Build prompt that includes prior context
            if result.steps:
                prompt = (
                    f"Previous analysis:\n{current_input}\n\n"
                    f"Using {strategy_name} strategy, continue with:\n{query}"
                )
            else:
                prompt = query

            # Collect output
            output_chunks = []
            for chunk in agent.stream(prompt):
                output_chunks.append(chunk)
            output = "".join(output_chunks)

            step = ChainStep(
                strategy=strategy_name,
                output=output,
                elapsed_ms=(time.time() - step_start) * 1000,
            )
            result.steps.append(step)
            current_input = output

        result.final_output = current_input
        result.total_ms = (time.time() - total_start) * 1000
        return result

    def stream(self, query: str):
        """Stream the chain, yielding (strategy, chunk) tuples."""
        current_input = query

        for i, strategy_name in enumerate(self.strategies):
            agent_class = AGENT_MAP[strategy_name]
            agent = agent_class(model=self.model)

            if i > 0:
                prompt = (
                    f"Previous analysis:\n{current_input}\n\n"
                    f"Using {strategy_name} strategy, continue with:\n{query}"
                )
            else:
                prompt = query

            output_chunks = []
            for chunk in agent.stream(prompt):
                output_chunks.append(chunk)
                yield strategy_name, chunk

            current_input = "".join(output_chunks)
