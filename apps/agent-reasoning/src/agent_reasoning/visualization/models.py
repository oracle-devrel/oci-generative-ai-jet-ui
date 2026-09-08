# src/visualization/models.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TreeNode:
    """Tree of Thoughts node."""

    id: str
    depth: int
    content: str
    score: Optional[float] = None
    parent_id: Optional[str] = None
    is_best: bool = False
    is_pruned: bool = False


@dataclass
class SubTask:
    """Decomposed/Least-to-Most/Recursive task."""

    id: int
    description: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    progress: float = 0.0
    parent_id: Optional[int] = None


@dataclass
class VotingSample:
    """Self-Consistency voting sample."""

    id: int
    answer: str = ""
    reasoning: str = ""
    votes: int = 0
    is_winner: bool = False
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class ReflectionIteration:
    """Self-Reflection iteration."""

    iteration: int
    draft: str = ""
    critique: Optional[str] = None
    improvement: Optional[str] = None
    is_correct: bool = False


@dataclass
class RefinementIteration:
    """Refinement Loop iteration with score-based feedback."""

    iteration: int
    draft: str = ""
    critique: Optional[str] = None
    feedback: Optional[str] = None
    score: float = 0.0
    is_accepted: bool = False


@dataclass
class PipelineIteration:
    """Complex Refinement Pipeline iteration tracking."""

    stage_index: int
    stage_name: str
    iteration_in_stage: int
    draft: str = ""
    critique: Optional[str] = None
    feedback: Optional[str] = None
    score: float = 0.0
    is_stage_complete: bool = False
    is_pipeline_complete: bool = False


@dataclass
class ReActStep:
    """ReAct reasoning step."""

    step: int
    thought: str = ""
    action: Optional[str] = None
    action_input: Optional[str] = None
    observation: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class ChainStep:
    """Chain-of-Thought step."""

    step: int
    content: str = ""
    total_steps: Optional[int] = None
    is_final: bool = False
    icon: str = "🔢"


@dataclass
class DebateRound:
    """Adversarial Debate round."""

    round_num: int
    pro_argument: str = ""
    con_argument: str = ""
    judge_score_pro: float = 0.0
    judge_score_con: float = 0.0
    judge_commentary: str = ""
    winner: Optional[str] = None  # "pro", "con", or None


@dataclass
class MCTSNode:
    """Monte Carlo Tree Search node."""

    id: str
    depth: int
    content: str
    visits: int = 0
    wins: float = 0.0
    score: Optional[float] = None
    parent_id: Optional[str] = None
    is_best: bool = False
    is_expanded: bool = False


@dataclass
class AnalogyMapping:
    """Analogical reasoning mapping."""

    step: int
    source_domain: str = ""
    target_domain: str = ""
    abstract_structure: str = ""
    mapping: str = ""
    solution_transfer: str = ""
    phase: str = "identify"  # "identify", "generate", "transfer"


@dataclass
class SocraticExchange:
    """Socratic method Q&A exchange."""

    question_num: int
    question: str = ""
    answer: str = ""
    narrows_to: str = ""
    is_final_synthesis: bool = False


@dataclass
class MetaClassification:
    """Meta-reasoning query classification."""

    query_type: str = ""
    confidence: float = 0.0
    selected_strategy: str = ""
    reasoning: str = ""


@dataclass
class CircuitNode:
    """Reasoning circuit/DAG node."""

    node_id: str
    node_type: str = ""  # "agent", "parallel_map", "vote", "gate"
    strategy: str = ""
    status: TaskStatus = TaskStatus.PENDING
    input_summary: str = ""
    output_summary: str = ""


@dataclass
class StreamEvent:
    """Wrapper for streaming events."""

    # Event types: "node", "task", "sample", "iteration", "refinement",
    # "pipeline", "react_step", "chain_step", "debate_round", "mcts_node",
    # "analogy", "socratic", "meta_classification", "circuit_node",
    # "text", "final"
    event_type: str
    data: Union[
        TreeNode,
        SubTask,
        VotingSample,
        ReflectionIteration,
        RefinementIteration,
        PipelineIteration,
        ReActStep,
        ChainStep,
        DebateRound,
        MCTSNode,
        AnalogyMapping,
        SocraticExchange,
        MetaClassification,
        CircuitNode,
        str,
    ]
    is_update: bool = False  # True if updating existing item

    def to_dict(self):
        """Serialize for NDJSON streaming."""
        data = self.data
        if hasattr(data, "__dict__") and not isinstance(data, Enum):
            data = {}
            for k, v in self.data.__dict__.items():
                if isinstance(v, Enum):
                    data[k] = v.value
                elif isinstance(v, list):
                    data[k] = [
                        item.__dict__
                        if (hasattr(item, "__dict__") and not isinstance(item, Enum))
                        else (item.value if isinstance(item, Enum) else item)
                        for item in v
                    ]
                elif hasattr(v, "__dict__"):
                    data[k] = v.__dict__
                else:
                    data[k] = v
        return {
            "event_type": self.event_type,
            "data": data,
            "is_update": self.is_update,
        }
