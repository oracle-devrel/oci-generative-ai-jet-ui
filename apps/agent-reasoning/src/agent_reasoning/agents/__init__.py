"""
Reasoning strategy agents.

Available agents:
- StandardAgent: Direct LLM generation (baseline)
- CoTAgent: Chain-of-Thought reasoning
- ToTAgent: Tree of Thoughts exploration
- ReActAgent: Reason + Act with tools
- SelfReflectionAgent: Draft → Critique → Refine
- ConsistencyAgent: Self-consistency voting
- DecomposedAgent: Problem decomposition
- LeastToMostAgent: Least-to-most reasoning
- RecursiveAgent: Recursive processing
"""

from agent_reasoning.agents.analogical import AnalogicalAgent
from agent_reasoning.agents.base import BaseAgent
from agent_reasoning.agents.consistency import ConsistencyAgent
from agent_reasoning.agents.cot import CoTAgent
from agent_reasoning.agents.debate import DebateAgent
from agent_reasoning.agents.decomposed import DecomposedAgent
from agent_reasoning.agents.least_to_most import LeastToMostAgent
from agent_reasoning.agents.mcts import MCTSAgent
from agent_reasoning.agents.meta import MetaReasoningAgent
from agent_reasoning.agents.react import ReActAgent
from agent_reasoning.agents.recursive import RecursiveAgent
from agent_reasoning.agents.self_reflection import SelfReflectionAgent
from agent_reasoning.agents.socratic import SocraticAgent
from agent_reasoning.agents.standard import StandardAgent
from agent_reasoning.agents.tot import ToTAgent

AGENT_MAP = {
    "standard": StandardAgent,
    "cot": CoTAgent,
    "chain_of_thought": CoTAgent,
    "tot": ToTAgent,
    "tree_of_thoughts": ToTAgent,
    "react": ReActAgent,
    "self_reflection": SelfReflectionAgent,
    "reflection": SelfReflectionAgent,
    "consistency": ConsistencyAgent,
    "self_consistency": ConsistencyAgent,
    "decomposed": DecomposedAgent,
    "least_to_most": LeastToMostAgent,
    "ltm": LeastToMostAgent,
    "recursive": RecursiveAgent,
    "rlm": RecursiveAgent,
    "mcts": MCTSAgent,
    "monte_carlo": MCTSAgent,
    "debate": DebateAgent,
    "adversarial": DebateAgent,
    "analogical": AnalogicalAgent,
    "analogy": AnalogicalAgent,
    "socratic": SocraticAgent,
    "questioning": SocraticAgent,
    "meta": MetaReasoningAgent,
    "auto": MetaReasoningAgent,
}

__all__ = [
    "BaseAgent",
    "StandardAgent",
    "CoTAgent",
    "ToTAgent",
    "ReActAgent",
    "SelfReflectionAgent",
    "ConsistencyAgent",
    "DecomposedAgent",
    "LeastToMostAgent",
    "RecursiveAgent",
    "MCTSAgent",
    "AnalogicalAgent",
    "DebateAgent",
    "SocraticAgent",
    "MetaReasoningAgent",
    "AGENT_MAP",
]
