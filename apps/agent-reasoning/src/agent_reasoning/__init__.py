"""
Agent Reasoning: Transform LLMs into robust problem-solving agents.

Usage:
    from agent_reasoning import ReasoningInterceptor
    from agent_reasoning.agents import CoTAgent, ToTAgent, DebateAgent
    from agent_reasoning.ensemble import ReasoningEnsemble
    from agent_reasoning.circuits import ReasoningCircuit, CIRCUIT_TEMPLATES
    from agent_reasoning.config import get_ollama_host, set_ollama_host
"""

from agent_reasoning.agents import (
    AnalogicalAgent,
    DebateAgent,
    MCTSAgent,
    MetaReasoningAgent,
    SocraticAgent,
)
from agent_reasoning.circuits import CIRCUIT_TEMPLATES, ReasoningCircuit
from agent_reasoning.client import OllamaClient
from agent_reasoning.config import get_ollama_host, load_config, save_config, set_ollama_host
from agent_reasoning.ensemble import ReasoningEnsemble
from agent_reasoning.interceptor import AGENT_MAP, ReasoningInterceptor

__version__ = "1.0.8"
__all__ = [
    "ReasoningInterceptor",
    "ReasoningEnsemble",
    "ReasoningCircuit",
    "CIRCUIT_TEMPLATES",
    "OllamaClient",
    "AGENT_MAP",
    "DebateAgent",
    "MCTSAgent",
    "AnalogicalAgent",
    "SocraticAgent",
    "MetaReasoningAgent",
    "get_ollama_host",
    "set_ollama_host",
    "load_config",
    "save_config",
]
