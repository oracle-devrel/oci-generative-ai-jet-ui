import logging

from agent_reasoning.agents.analogical import AnalogicalAgent
from agent_reasoning.agents.complex_refinement import ComplexRefinementLoopAgent
from agent_reasoning.agents.consistency import ConsistencyAgent
from agent_reasoning.agents.cot import CoTAgent
from agent_reasoning.agents.debate import DebateAgent
from agent_reasoning.agents.decomposed import DecomposedAgent
from agent_reasoning.agents.least_to_most import LeastToMostAgent
from agent_reasoning.agents.mcts import MCTSAgent
from agent_reasoning.agents.meta import MetaReasoningAgent
from agent_reasoning.agents.react import ReActAgent
from agent_reasoning.agents.recursive import RecursiveAgent
from agent_reasoning.agents.refinement_loop import RefinementLoopAgent
from agent_reasoning.agents.self_reflection import SelfReflectionAgent
from agent_reasoning.agents.socratic import SocraticAgent
from agent_reasoning.agents.standard import StandardAgent
from agent_reasoning.agents.tot import ToTAgent

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReasoningInterceptor")

AGENT_MAP = {
    "standard": StandardAgent,
    "cot": CoTAgent,
    "chain_of_thought": CoTAgent,
    "reflection": SelfReflectionAgent,
    "self_reflection": SelfReflectionAgent,
    "react": ReActAgent,
    "tot": ToTAgent,
    "tree_of_thoughts": ToTAgent,
    "recursive": RecursiveAgent,
    "rlm": RecursiveAgent,
    "consistency": ConsistencyAgent,
    "self_consistency": ConsistencyAgent,
    "decomposed": DecomposedAgent,
    "least_to_most": LeastToMostAgent,
    "ltm": LeastToMostAgent,
    "refinement": RefinementLoopAgent,
    "refinement_loop": RefinementLoopAgent,
    "iterative_refinement": RefinementLoopAgent,
    "complex_refinement": ComplexRefinementLoopAgent,
    "pipeline": ComplexRefinementLoopAgent,
    "pipeline_refinement": ComplexRefinementLoopAgent,
    "debate": DebateAgent,
    "adversarial": DebateAgent,
    "mcts": MCTSAgent,
    "monte_carlo": MCTSAgent,
    "analogical": AnalogicalAgent,
    "analogy": AnalogicalAgent,
    "socratic": SocraticAgent,
    "questioning": SocraticAgent,
    "meta": MetaReasoningAgent,
    "auto": MetaReasoningAgent,
}


class ReasoningInterceptor:
    """
    A drop-in replacement for a standard Ollama client object.
    It intercepts 'generate' and 'chat' calls, checks for reasoning strategies
    in the model name (e.g. 'gemma+cot'), and routes to the appropriate Agent.
    """

    def __init__(self, host=None):
        if host is None:
            from agent_reasoning.config import get_ollama_host

            host = get_ollama_host()
        self.host = host

    def generate(self, model, prompt, system=None, stream=False, **kwargs):
        """
        Mimics ollama.generate signature.
        """
        # 1. Parse Strategy
        base_model = model
        strategy = "standard"

        if "+" in model:
            base_model, strategy_tag = model.split("+", 1)
            strategy = strategy_tag.lower().strip()

        if strategy not in AGENT_MAP:
            logger.warning(f"Unknown strategy '{strategy}', falling back to standard.")
            strategy = "standard"

        # 2. Instantiate Agent
        agent_class = AGENT_MAP[strategy]
        agent = agent_class(model=base_model)

        # 3. Execution
        # If stream=True, return a generator
        if stream:
            return self._stream_generator(agent, prompt)
        else:
            # Accumulate result
            full_response = ""
            for chunk in agent.stream(prompt):
                full_response += chunk

            return {"model": model, "response": full_response, "done": True}

    def chat(self, model, messages, stream=False, **kwargs):
        """
        Mimics ollama.chat signature.
        Flattens the messages list into a single prompt string for the Agents.
        """
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt += f"{role.upper()}: {content}\n"
        prompt += "ASSISTANT: "

        # Reuse generate logic
        return self.generate(model=model, prompt=prompt, stream=stream, **kwargs)

    def _stream_generator(self, agent, prompt):
        for chunk in agent.stream(prompt):
            yield {
                "model": agent.name,  # Meta info
                "response": chunk,
                "done": False,
            }
        yield {"done": True, "response": ""}


# Usage alias to look like the module
class Client(ReasoningInterceptor):
    pass
