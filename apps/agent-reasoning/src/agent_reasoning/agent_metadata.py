"""Shared agent metadata module.

Combines static metadata with AGENT_MAP and VISUALIZER_MAP to produce
a fully-enriched agent list for API consumers (e.g. /api/agents, TUI sidebar).
"""

AGENT_METADATA = {
    "standard": {
        "name": "Standard",
        "description": "Direct generation without reasoning enhancement. Baseline for comparison.",
        "reference": "N/A",
        "best_for": "Simple queries, speed-critical tasks, baseline comparisons",
        "tradeoffs": "Fastest, but no structured reasoning. May miss nuance on complex problems.",
        "parameters": {},
    },
    "cot": {
        "name": "Chain of Thought",
        "description": "Step-by-step reasoning decomposition injected via prompt.",
        "reference": "Wei et al. (2022)",
        "best_for": "Math problems, logical deduction, multi-step reasoning",
        "tradeoffs": "Slower than standard; intermediate steps increase token usage.",
        "parameters": {},
    },
    "tot": {
        "name": "Tree of Thoughts",
        "description": "Branching exploration of reasoning paths with scoring and pruning.",
        "reference": "Yao et al. (2023)",
        "best_for": "Complex riddles, planning, problems with multiple viable approaches",
        "tradeoffs": "High token cost (width × depth LLM calls). Overkill for simple queries.",
        "parameters": {
            "width": {
                "type": "int",
                "default": 2,
                "min": 1,
                "max": 5,
                "description": "Number of branches to explore at each step",
            },
            "depth": {
                "type": "int",
                "default": 3,
                "min": 1,
                "max": 6,
                "description": "Maximum depth of the reasoning tree",
            },
        },
    },
    "react": {
        "name": "ReAct",
        "description": "Interleaved reasoning and tool-use actions (Reason + Act).",
        "reference": "Yao et al. (2022)",
        "best_for": "Fact-checking, tasks requiring external tool calls, information retrieval",
        "tradeoffs": "Tool calls add latency; mock tools limit utility without real integration.",
        "parameters": {
            "max_steps": {
                "type": "int",
                "default": 5,
                "min": 1,
                "max": 10,
                "description": "Maximum number of Thought/Action/Observation cycles",
            },
        },
    },
    "recursive": {
        "name": "Recursive LM",
        "description": "Code-generation REPL loop with recursive LLM calls for self-correction.",
        "reference": "Author et al. (2025)",
        "best_for": "Code generation, iterative problem solving, long-context tasks",
        "tradeoffs": "Can loop if termination condition is never met. Needs a capable base model.",
        "parameters": {},
    },
    "reflection": {
        "name": "Self-Reflection",
        "description": "Draft, critique, and refine loop until the answer satisfies a quality bar.",
        "reference": "Shinn et al. (2023)",
        "best_for": "Creative writing, open-ended questions, tasks where first drafts rarely shine",
        "tradeoffs": "Multiple LLM calls; quality gain diminishes after a few turns.",
        "parameters": {
            "max_turns": {
                "type": "int",
                "default": 5,
                "min": 1,
                "max": 10,
                "description": "Maximum draft-critique-refine iterations",
            },
        },
    },
    "consistency": {
        "name": "Self-Consistency",
        "description": "Generate multiple independent samples and select the majority answer.",
        "reference": "Wang et al. (2022)",
        "best_for": "Reducing answer variance, any task with a definite ground-truth answer",
        "tradeoffs": "Token cost scales linearly with samples. Majority vote can still be wrong.",
        "parameters": {
            "samples": {
                "type": "int",
                "default": 5,
                "min": 2,
                "max": 10,
                "description": "Number of independent samples to generate before voting",
            },
        },
    },
    "decomposed": {
        "name": "Decomposed Prompting",
        "description": "Break the problem into sub-tasks and solve each sequentially.",
        "reference": "Khot et al. (2022)",
        "best_for": "Planning, multi-part questions, tasks with clear sub-components",
        "tradeoffs": "Decomposition quality depends on the model; bad splits hurt final quality.",
        "parameters": {},
    },
    "least_to_most": {
        "name": "Least-to-Most",
        "description": "Identify sub-questions ordered from easiest to hardest, solve in sequence.",
        "reference": "Zhou et al. (2022)",
        "best_for": "Complex reasoning chains where building blocks need to be established first",
        "tradeoffs": "Requires a model that can reliably order sub-questions by difficulty.",
        "parameters": {},
    },
    "refinement": {
        "name": "Refinement Loop",
        "description": "Iterative score-based generation: generate, score, refine until threshold.",
        "reference": "Madaan et al. (2023)",
        "best_for": "Technical writing, structured outputs, tasks with a measurable quality metric",
        "tradeoffs": "Can stall if score threshold is too high for the base model to reach.",
        "parameters": {
            "score_threshold": {
                "type": "float",
                "default": 0.9,
                "min": 0.1,
                "max": 1.0,
                "description": "Minimum score (0.0-1.0) required to stop refinement",
            },
            "max_iterations": {
                "type": "int",
                "default": 10,
                "min": 1,
                "max": 20,
                "description": "Maximum refinement iterations before returning best result",
            },
        },
    },
    "complex_refinement": {
        "name": "Complex Pipeline",
        "description": "5-stage refinement pipeline with specialized critics at each stage.",
        "reference": "Multi-Stage Refinement",
        "best_for": "Production content, long-form writing, multi-dimensional quality requirements",
        "tradeoffs": "Highest token cost. 5 × max_iterations_per_stage LLM calls at minimum.",
        "parameters": {
            "score_threshold": {
                "type": "float",
                "default": 0.9,
                "min": 0.1,
                "max": 1.0,
                "description": "Minimum score required to advance past each pipeline stage",
            },
            "max_iterations_per_stage": {
                "type": "int",
                "default": 3,
                "min": 1,
                "max": 5,
                "description": "Maximum refinement iterations allowed within each stage",
            },
        },
    },
    "debate": {
        "name": "Debate",
        "description": "Two adversarial agents argue opposing positions; a judge picks the winner.",
        "reference": "Irving et al. (2018)",
        "best_for": "Controversial topics, decision analysis, stress-testing an argument",
        "tradeoffs": "Multiple LLM calls per round. Quality depends on judge impartiality.",
        "parameters": {
            "num_rounds": {
                "type": "int",
                "default": 3,
                "min": 1,
                "max": 5,
                "description": "Number of debate rounds before the judge renders a verdict",
            },
        },
    },
    "mcts": {
        "name": "Monte Carlo Tree Search",
        "description": "MCTS-based reasoning: simulate many paths and back-propagate scores.",
        "reference": "Silver et al. (2016) adapted for LLMs",
        "best_for": "Game-like reasoning, strategic planning, problems with well-defined outcomes",
        "tradeoffs": "Expensive. Exploration-exploitation balance is sensitive to tuning.",
        "parameters": {
            "num_simulations": {
                "type": "int",
                "default": 10,
                "min": 1,
                "max": 30,
                "description": "Number of MCTS simulation rollouts to perform",
            },
            "exploration_weight": {
                "type": "float",
                "default": 1.414,
                "min": 0.1,
                "max": 3.0,
                "description": "UCB exploration constant (higher = more exploration)",
            },
        },
    },
    "analogical": {
        "name": "Analogical Reasoning",
        "description": "Solve by finding and applying analogous problems from different domains.",
        "reference": "Webb et al. (2023)",
        "best_for": "Novel problems, creative problem-solving, cross-domain solution transfer",
        "tradeoffs": "Analogy quality is unpredictable; poor analogies lead the model astray.",
        "parameters": {},
    },
    "socratic": {
        "name": "Socratic Questioning",
        "description": "Probe assumptions with guided questions before converging on an answer.",
        "reference": "Socratic Method",
        "best_for": "Clarifying vague problems, ethics, philosophical questions, ill-defined tasks",
        "tradeoffs": "Multiple question rounds before a final answer; slow for simple tasks.",
        "parameters": {
            "num_rounds": {
                "type": "int",
                "default": 2,
                "min": 1,
                "max": 4,
                "description": "Socratic questioning rounds before synthesizing the final answer",
            },
        },
    },
    "meta": {
        "name": "Meta Reasoning",
        "description": "Automatically selects the best reasoning strategy for the given query.",
        "reference": "Auto-routing heuristic",
        "best_for": "Mixed workloads, uncertain query types, exploratory sessions",
        "tradeoffs": "Strategy selection adds an LLM round-trip; choice may not be optimal.",
        "parameters": {},
    },
}

# Primary agent IDs (canonical names, no aliases)
PRIMARY_AGENT_IDS = list(AGENT_METADATA.keys())


def get_agent_list() -> list[dict]:
    """Return a fully-enriched list of agent dicts for API consumers.

    Each entry combines AGENT_METADATA with live data from AGENT_MAP
    (to confirm the agent is registered) and VISUALIZER_MAP (for
    has_visualizer).  Only primary IDs are returned (no aliases).
    """
    from agent_reasoning.interceptor import AGENT_MAP
    from agent_reasoning.visualization import VISUALIZER_MAP

    agents = []
    for agent_id, meta in AGENT_METADATA.items():
        # Guard: only include agents that are actually registered
        if agent_id not in AGENT_MAP:
            continue

        viz_value = VISUALIZER_MAP.get(agent_id)
        # has_visualizer is True only when there's a real class (not None)
        has_visualizer = viz_value is not None

        agents.append(
            {
                "id": agent_id,
                "name": meta["name"],
                "description": meta["description"],
                "reference": meta["reference"],
                "best_for": meta["best_for"],
                "tradeoffs": meta["tradeoffs"],
                "has_visualizer": has_visualizer,
                "parameters": meta["parameters"],
            }
        )

    return agents
