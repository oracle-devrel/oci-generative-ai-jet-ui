"""
Agent cards for reasoning strategies.

Enables A2A discovery of all reasoning agents.
"""

from typing import Dict, Any


def get_reasoning_ensemble_card(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Get agent card for the reasoning ensemble orchestrator."""
    return {
        "agent_id": "reasoning_ensemble_v1",
        "name": "Reasoning Ensemble Orchestrator",
        "version": "1.0.0",
        "description": "Executes multiple reasoning strategies in parallel and aggregates via majority voting",
        "capabilities": [
            {
                "name": "reasoning.execute",
                "description": "Run ensemble of reasoning strategies with voting",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The question to answer"},
                        "strategies": {"type": "array", "items": {"type": "string"}, "description": "List of strategy names"},
                        "use_rag": {"type": "boolean", "description": "Whether to use RAG context"},
                        "collection": {"type": "string", "description": "Collection to query (PDF, Web, Repository, General)"},
                        "config": {"type": "object", "description": "Per-strategy configuration"}
                    },
                    "required": ["query", "strategies"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "winner": {"type": "object"},
                        "all_responses": {"type": "array"},
                        "total_duration_ms": {"type": "number"}
                    }
                }
            },
            {
                "name": "reasoning.list",
                "description": "List available reasoning strategies",
                "input_schema": {"type": "object", "properties": {}},
                "output_schema": {"type": "array", "items": {"type": "string"}}
            }
        ],
        "endpoints": {
            "base_url": base_url,
            "authentication": {"type": "none"}
        },
        "metadata": {
            "type": "orchestrator",
            "strategies_available": 9
        }
    }


def get_strategy_agent_card(
    strategy_key: str,
    base_url: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """Get agent card for a specific reasoning strategy."""

    STRATEGY_INFO = {
        "standard": {
            "name": "Standard Generator",
            "description": "Direct LLM generation without reasoning enhancement (baseline)",
            "best_for": ["simple_queries", "baseline"],
            "params": {}
        },
        "cot": {
            "name": "Chain-of-Thought Reasoner",
            "description": "Step-by-step reasoning using Chain-of-Thought prompting (Wei et al. 2022)",
            "best_for": ["math", "logic", "explanations"],
            "params": {}
        },
        "tot": {
            "name": "Tree of Thoughts Explorer",
            "description": "Explores multiple reasoning branches using BFS (Yao et al. 2023)",
            "best_for": ["complex_riddles", "strategy"],
            "params": {"depth": 3, "width": 2}
        },
        "react": {
            "name": "ReAct Agent",
            "description": "Interleaves reasoning and tool usage (Yao et al. 2022)",
            "best_for": ["fact_checking", "calculations"],
            "params": {},
            "tools": ["web_search", "calculate"]
        },
        "self_reflection": {
            "name": "Self-Reflection Agent",
            "description": "Draft -> Critique -> Refine loop (Shinn et al. 2023)",
            "best_for": ["creative_writing", "high_accuracy"],
            "params": {"max_turns": 3}
        },
        "consistency": {
            "name": "Self-Consistency Voter",
            "description": "Generates multiple samples and votes for best answer (Wang et al. 2022)",
            "best_for": ["diverse_problems"],
            "params": {"samples": 3}
        },
        "decomposed": {
            "name": "Problem Decomposer",
            "description": "Breaks complex queries into sub-tasks (Khot et al. 2022)",
            "best_for": ["planning", "long_form"],
            "params": {}
        },
        "least_to_most": {
            "name": "Least-to-Most Reasoner",
            "description": "Solves from simplest to most complex (Zhou et al. 2022)",
            "best_for": ["complex_reasoning"],
            "params": {}
        },
        "recursive": {
            "name": "Recursive LM Agent",
            "description": "Recursively processes using Python REPL",
            "best_for": ["long_context"],
            "params": {}
        }
    }

    info = STRATEGY_INFO.get(strategy_key, {
        "name": strategy_key.title(),
        "description": f"Reasoning strategy: {strategy_key}",
        "best_for": [],
        "params": {}
    })

    return {
        "agent_id": f"reasoning_{strategy_key}_v1",
        "name": info["name"],
        "version": "1.0.0",
        "description": info["description"],
        "capabilities": [
            {
                "name": "reasoning.strategy",
                "description": f"Execute {info['name']} reasoning",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "config": {"type": "object"}
                    },
                    "required": ["query"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "response": {"type": "string"},
                        "duration_ms": {"type": "number"}
                    }
                }
            }
        ],
        "endpoints": {
            "base_url": base_url,
            "authentication": {"type": "none"}
        },
        "metadata": {
            "type": "strategy",
            "strategy_key": strategy_key,
            "best_for": info["best_for"],
            "params": info["params"]
        }
    }


def get_all_reasoning_agent_cards(base_url: str = "http://localhost:8000") -> Dict[str, Dict[str, Any]]:
    """Get all reasoning agent cards."""
    cards = {}

    # Ensemble orchestrator
    ensemble_card = get_reasoning_ensemble_card(base_url)
    cards[ensemble_card["agent_id"]] = ensemble_card

    # Individual strategies
    strategies = ["standard", "cot", "tot", "react", "self_reflection",
                  "consistency", "decomposed", "least_to_most", "recursive"]

    for strategy in strategies:
        card = get_strategy_agent_card(strategy, base_url)
        cards[card["agent_id"]] = card

    return cards


def get_reasoning_agent_card_by_id(agent_id: str, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """Get a specific reasoning agent card by ID."""
    all_cards = get_all_reasoning_agent_cards(base_url)
    return all_cards.get(agent_id)
