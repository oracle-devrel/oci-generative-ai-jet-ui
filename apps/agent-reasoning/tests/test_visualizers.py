"""Tests for visualization system - models, registry, and all visualizers."""

from rich.console import Group

from agent_reasoning.visualization.models import (
    AnalogyMapping,
    ChainStep,
    CircuitNode,
    DebateRound,
    MCTSNode,
    MetaClassification,
    PipelineIteration,
    ReActStep,
    RefinementIteration,
    ReflectionIteration,
    SocraticExchange,
    StreamEvent,
    SubTask,
    TaskStatus,
    TreeNode,
    VotingSample,
)


# ---------------------------------------------------------------------------
# StreamEvent model
# ---------------------------------------------------------------------------
class TestStreamEventModel:
    def test_create_text_event(self):
        e = StreamEvent(event_type="text", data="hello")
        assert e.event_type == "text"
        assert e.data == "hello"
        assert e.is_update is False

    def test_create_update_event(self):
        e = StreamEvent(event_type="step", data="content", is_update=True)
        assert e.is_update is True

    def test_to_dict_text(self):
        e = StreamEvent(event_type="text", data="hello")
        d = e.to_dict()
        assert d["event_type"] == "text"
        assert d["data"] == "hello"
        assert d["is_update"] is False

    def test_to_dict_dataclass(self):
        step = ChainStep(step=1, content="thinking")
        e = StreamEvent(event_type="chain_step", data=step)
        d = e.to_dict()
        assert d["data"]["step"] == 1
        assert d["data"]["content"] == "thinking"

    def test_to_dict_enum(self):
        sample = VotingSample(id=1, status=TaskStatus.RUNNING)
        e = StreamEvent(event_type="sample", data=sample)
        d = e.to_dict()
        assert d["data"]["status"] == "running"

    def test_to_dict_preserves_event_type(self):
        e = StreamEvent(event_type="final", data="done")
        d = e.to_dict()
        assert d["event_type"] == "final"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------
class TestDataModels:
    def test_chain_step_defaults(self):
        s = ChainStep(step=1, content="")
        assert s.is_final is False
        assert s.total_steps is None
        assert s.icon == "\U0001f522"  # default icon

    def test_tree_node_defaults(self):
        n = TreeNode(id="A1", depth=1, content="test", score=0.5)
        assert n.is_pruned is False
        assert n.is_best is False
        assert n.parent_id is None

    def test_react_step_defaults(self):
        s = ReActStep(step=1, status=TaskStatus.RUNNING)
        assert s.thought == ""
        assert s.action is None
        assert s.observation is None
        assert s.action_input is None

    def test_voting_sample_defaults(self):
        s = VotingSample(id=1, status=TaskStatus.PENDING)
        assert s.reasoning == ""
        assert s.answer == ""
        assert s.votes == 0
        assert s.is_winner is False

    def test_subtask_defaults(self):
        t = SubTask(id=1, description="task", status=TaskStatus.PENDING)
        assert t.result is None
        assert t.progress == 0.0
        assert t.parent_id is None

    def test_reflection_iteration(self):
        r = ReflectionIteration(iteration=1, draft="draft text")
        assert r.critique is None
        assert r.improvement is None
        assert r.is_correct is False

    def test_refinement_iteration(self):
        r = RefinementIteration(iteration=1, draft="draft")
        assert r.score == 0.0
        assert r.is_accepted is False
        assert r.feedback is None
        assert r.critique is None

    def test_pipeline_iteration(self):
        p = PipelineIteration(stage_index=0, stage_name="clarity", iteration_in_stage=1)
        assert p.draft == ""
        assert p.score == 0.0
        assert p.is_stage_complete is False
        assert p.is_pipeline_complete is False

    def test_debate_round(self):
        d = DebateRound(round_num=1)
        assert d.pro_argument == ""
        assert d.con_argument == ""
        assert d.winner is None
        assert d.judge_score_pro == 0.0
        assert d.judge_score_con == 0.0

    def test_socratic_exchange(self):
        s = SocraticExchange(question_num=1)
        assert s.question == ""
        assert s.answer == ""
        assert s.is_final_synthesis is False
        assert s.narrows_to == ""

    def test_analogy_mapping(self):
        a = AnalogyMapping(step=1)
        assert a.source_domain == ""
        assert a.target_domain == ""
        assert a.abstract_structure == ""
        assert a.phase == "identify"

    def test_mcts_node(self):
        m = MCTSNode(id="root", depth=0, content="start")
        assert m.visits == 0
        assert m.wins == 0.0
        assert m.is_best is False
        assert m.is_expanded is False

    def test_meta_classification(self):
        mc = MetaClassification()
        assert mc.query_type == ""
        assert mc.confidence == 0.0
        assert mc.selected_strategy == ""

    def test_circuit_node(self):
        cn = CircuitNode(node_id="n1")
        assert cn.node_type == ""
        assert cn.strategy == ""
        assert cn.status == TaskStatus.PENDING

    def test_task_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"


# ---------------------------------------------------------------------------
# Visualizer registry
# ---------------------------------------------------------------------------
class TestVisualizerRegistry:
    def test_visualizer_map_exists(self):
        from agent_reasoning.visualization import VISUALIZER_MAP

        assert len(VISUALIZER_MAP) > 0

    def test_all_visualizers_instantiable(self):
        from agent_reasoning.visualization import VISUALIZER_MAP

        for name, viz_class in VISUALIZER_MAP.items():
            if viz_class is None:
                continue  # complex_refinement, pipeline, standard are None
            viz = viz_class()
            assert hasattr(viz, "update")
            assert hasattr(viz, "render")

    def test_get_visualizer_known(self):
        from agent_reasoning.visualization import get_visualizer

        viz = get_visualizer("cot")
        assert viz is not None

    def test_get_visualizer_unknown(self):
        from agent_reasoning.visualization import get_visualizer

        viz = get_visualizer("nonexistent_strategy")
        assert viz is None

    def test_get_visualizer_none_entry(self):
        from agent_reasoning.visualization import get_visualizer

        viz = get_visualizer("standard")
        assert viz is None

    def test_aliases_resolve_same_class(self):
        from agent_reasoning.visualization import VISUALIZER_MAP

        assert VISUALIZER_MAP["tot"] is VISUALIZER_MAP["tree_of_thoughts"]
        assert VISUALIZER_MAP["cot"] is VISUALIZER_MAP["chain_of_thought"]
        assert VISUALIZER_MAP["debate"] is VISUALIZER_MAP["adversarial"]
        assert VISUALIZER_MAP["socratic"] is VISUALIZER_MAP["questioning"]
        assert VISUALIZER_MAP["analogy"] is VISUALIZER_MAP["analogical"]


# ---------------------------------------------------------------------------
# StepVisualizer (cot)
# ---------------------------------------------------------------------------
class TestStepVisualizer:
    def test_instantiation(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer()
        assert viz.steps == {}
        assert viz.query == ""

    def test_instantiation_with_query(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer(query="What is 2+2?")
        assert viz.query == "What is 2+2?"

    def test_render_empty(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer(query="test")
        result = viz.render()
        assert result is not None

    def test_update_chain_step(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer(query="math problem")
        step = ChainStep(step=1, content="First, calculate the sum")
        event = StreamEvent(event_type="chain_step", data=step)
        viz.update(event)
        assert 1 in viz.steps
        assert viz.steps[1].content == "First, calculate the sum"

    def test_update_query(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer()
        event = StreamEvent(event_type="query", data="new query")
        viz.update(event)
        assert viz.query == "new query"

    def test_update_final_answer(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer()
        event = StreamEvent(event_type="final_answer", data="42")
        viz.update(event)
        assert viz.final_answer == "42"

    def test_render_with_steps(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer(query="What is 2+2?")
        viz.update(
            StreamEvent(event_type="chain_step", data=ChainStep(step=1, content="Add the numbers"))
        )
        viz.update(
            StreamEvent(
                event_type="chain_step", data=ChainStep(step=2, content="Therefore the answer is 4")
            )
        )
        result = viz.render()
        assert isinstance(result, Group)

    def test_render_with_final_answer(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer(query="test")
        viz.update(StreamEvent(event_type="chain_step", data=ChainStep(step=1, content="step one")))
        viz.update(StreamEvent(event_type="final_answer", data="The answer is 42"))
        result = viz.render()
        assert isinstance(result, Group)

    def test_detect_icon_calculate(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer()
        assert viz._detect_icon("calculate the total") == "\U0001f522"

    def test_detect_icon_conclude(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer()
        assert viz._detect_icon("therefore the answer is") == "\U0001f4a1"

    def test_detect_icon_default(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer()
        assert viz._detect_icon("some random text") == "\U0001f4cc"

    def test_raw_content_fallback(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer(query="test")
        viz.update(StreamEvent(event_type="raw_content", data="Step 1: Do this. Step 2: Do that."))
        result = viz.render()
        assert isinstance(result, Group)

    def test_multiple_steps_ordering(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer(query="test")
        viz.update(StreamEvent(event_type="chain_step", data=ChainStep(step=3, content="third")))
        viz.update(StreamEvent(event_type="chain_step", data=ChainStep(step=1, content="first")))
        viz.update(StreamEvent(event_type="chain_step", data=ChainStep(step=2, content="second")))
        assert len(viz.steps) == 3
        result = viz.render()
        assert isinstance(result, Group)


# ---------------------------------------------------------------------------
# TreeVisualizer (tot / mcts)
# ---------------------------------------------------------------------------
class TestTreeVisualizer:
    def test_instantiation(self):
        from agent_reasoning.visualization.tree_viz import TreeVisualizer

        viz = TreeVisualizer()
        assert viz.nodes == {}
        assert viz.best_path == set()

    def test_render_empty(self):
        from agent_reasoning.visualization.tree_viz import TreeVisualizer

        viz = TreeVisualizer(query="test")
        result = viz.render()
        assert result is not None

    def test_update_node(self):
        from agent_reasoning.visualization.tree_viz import TreeVisualizer

        viz = TreeVisualizer()
        node = TreeNode(id="A1", depth=1, content="branch A", score=0.8)
        event = StreamEvent(event_type="node", data=node)
        viz.update(event)
        assert "A1" in viz.nodes
        assert viz.nodes["A1"].score == 0.8

    def test_update_best_node(self):
        from agent_reasoning.visualization.tree_viz import TreeVisualizer

        viz = TreeVisualizer()
        node = TreeNode(id="B1", depth=1, content="best branch", score=0.95, is_best=True)
        viz.update(StreamEvent(event_type="node", data=node))
        assert "B1" in viz.best_path

    def test_update_query(self):
        from agent_reasoning.visualization.tree_viz import TreeVisualizer

        viz = TreeVisualizer()
        viz.update(StreamEvent(event_type="query", data="solve this"))
        assert viz.query == "solve this"

    def test_render_with_nodes(self):
        from agent_reasoning.visualization.tree_viz import TreeVisualizer

        viz = TreeVisualizer(query="test")
        viz.update(
            StreamEvent(
                event_type="node", data=TreeNode(id="A1", depth=1, content="branch A", score=0.7)
            )
        )
        viz.update(
            StreamEvent(
                event_type="node",
                data=TreeNode(id="A2", depth=1, content="branch B", score=0.3, is_pruned=True),
            )
        )
        viz.update(
            StreamEvent(
                event_type="node",
                data=TreeNode(
                    id="A1-1",
                    depth=2,
                    content="sub-branch",
                    score=0.9,
                    parent_id="A1",
                    is_best=True,
                ),
            )
        )
        result = viz.render()
        assert isinstance(result, Group)

    def test_score_to_color(self):
        from agent_reasoning.visualization.tree_viz import TreeVisualizer

        viz = TreeVisualizer()
        assert viz._score_to_color(0.9) == "green"
        assert viz._score_to_color(0.6) == "yellow"
        assert viz._score_to_color(0.3) == "red"
        assert viz._score_to_color(None) == "white"

    def test_score_to_style_pruned(self):
        from agent_reasoning.visualization.tree_viz import TreeVisualizer

        viz = TreeVisualizer()
        assert viz._score_to_style(0.9, False, True) == "dim red"

    def test_score_to_style_best(self):
        from agent_reasoning.visualization.tree_viz import TreeVisualizer

        viz = TreeVisualizer()
        assert viz._score_to_style(0.9, True, False) == "bold green"


# ---------------------------------------------------------------------------
# SwimlaneVisualizer (react)
# ---------------------------------------------------------------------------
class TestSwimlaneVisualizer:
    def test_instantiation(self):
        from agent_reasoning.visualization.swimlane_viz import SwimlaneVisualizer

        viz = SwimlaneVisualizer()
        assert viz.steps == {}
        assert viz.max_steps == 5

    def test_render_empty(self):
        from agent_reasoning.visualization.swimlane_viz import SwimlaneVisualizer

        viz = SwimlaneVisualizer(query="test")
        result = viz.render()
        assert result is not None

    def test_update_react_step(self):
        from agent_reasoning.visualization.swimlane_viz import SwimlaneVisualizer

        viz = SwimlaneVisualizer()
        step = ReActStep(
            step=1,
            thought="I need to search",
            action="web_search",
            action_input="query",
            status=TaskStatus.RUNNING,
        )
        viz.update(StreamEvent(event_type="react_step", data=step))
        assert 1 in viz.steps
        assert viz.steps[1].thought == "I need to search"

    def test_tool_usage_tracking(self):
        from agent_reasoning.visualization.swimlane_viz import SwimlaneVisualizer

        viz = SwimlaneVisualizer()
        viz.update(
            StreamEvent(
                event_type="react_step",
                data=ReActStep(
                    step=1,
                    thought="t",
                    action="web_search",
                    action_input="q1",
                    status=TaskStatus.COMPLETED,
                ),
            )
        )
        viz.update(
            StreamEvent(
                event_type="react_step",
                data=ReActStep(
                    step=2,
                    thought="t",
                    action="web_search",
                    action_input="q2",
                    status=TaskStatus.COMPLETED,
                ),
            )
        )
        viz.update(
            StreamEvent(
                event_type="react_step",
                data=ReActStep(
                    step=3,
                    thought="t",
                    action="calculate",
                    action_input="1+1",
                    status=TaskStatus.COMPLETED,
                ),
            )
        )
        assert viz.tool_usage["web_search"] == 2
        assert viz.tool_usage["calculate"] == 1

    def test_render_with_steps(self):
        from agent_reasoning.visualization.swimlane_viz import SwimlaneVisualizer

        viz = SwimlaneVisualizer(query="What is the capital of France?")
        viz.update(
            StreamEvent(
                event_type="react_step",
                data=ReActStep(
                    step=1,
                    thought="I should search for this",
                    action="web_search",
                    action_input="capital of France",
                    observation="Paris is the capital",
                    status=TaskStatus.COMPLETED,
                ),
            )
        )
        result = viz.render()
        assert isinstance(result, Group)

    def test_render_with_final_answer(self):
        from agent_reasoning.visualization.swimlane_viz import SwimlaneVisualizer

        viz = SwimlaneVisualizer(query="test")
        viz.update(
            StreamEvent(
                event_type="react_step",
                data=ReActStep(
                    step=1,
                    thought="thinking",
                    action="search",
                    action_input="q",
                    observation="found it",
                    status=TaskStatus.COMPLETED,
                ),
            )
        )
        viz.update(StreamEvent(event_type="final_answer", data="Paris"))
        result = viz.render()
        assert isinstance(result, Group)

    def test_update_query(self):
        from agent_reasoning.visualization.swimlane_viz import SwimlaneVisualizer

        viz = SwimlaneVisualizer()
        viz.update(StreamEvent(event_type="query", data="new query"))
        assert viz.query == "new query"


# ---------------------------------------------------------------------------
# VotingVisualizer (consistency)
# ---------------------------------------------------------------------------
class TestVotingVisualizer:
    def test_instantiation(self):
        from agent_reasoning.visualization.voting_viz import VotingVisualizer

        viz = VotingVisualizer()
        assert viz.samples == {}
        assert viz.k == 5

    def test_instantiation_with_k(self):
        from agent_reasoning.visualization.voting_viz import VotingVisualizer

        viz = VotingVisualizer(k=3)
        assert viz.k == 3

    def test_render_empty(self):
        from agent_reasoning.visualization.voting_viz import VotingVisualizer

        viz = VotingVisualizer(query="test")
        result = viz.render()
        assert result is not None

    def test_update_sample(self):
        from agent_reasoning.visualization.voting_viz import VotingVisualizer

        viz = VotingVisualizer()
        sample = VotingSample(
            id=1, answer="42", reasoning="because math", status=TaskStatus.COMPLETED
        )
        viz.update(StreamEvent(event_type="sample", data=sample))
        assert 1 in viz.samples
        assert viz.samples[1].answer == "42"

    def test_update_voting_complete(self):
        from agent_reasoning.visualization.voting_viz import VotingVisualizer

        viz = VotingVisualizer()
        viz.update(StreamEvent(event_type="voting_complete", data="done"))
        assert viz.voting_complete is True

    def test_render_with_samples(self):
        from agent_reasoning.visualization.voting_viz import VotingVisualizer

        viz = VotingVisualizer(query="What is 2+2?", k=3)
        for i in range(1, 4):
            viz.update(
                StreamEvent(
                    event_type="sample",
                    data=VotingSample(
                        id=i,
                        answer="4",
                        reasoning=f"Sample {i} reasoning",
                        status=TaskStatus.COMPLETED,
                    ),
                )
            )
        result = viz.render()
        assert isinstance(result, Group)

    def test_render_with_voting_complete(self):
        from agent_reasoning.visualization.voting_viz import VotingVisualizer

        viz = VotingVisualizer(query="test", k=3)
        viz.update(
            StreamEvent(
                event_type="sample",
                data=VotingSample(id=1, answer="A", reasoning="r1", status=TaskStatus.COMPLETED),
            )
        )
        viz.update(
            StreamEvent(
                event_type="sample",
                data=VotingSample(id=2, answer="A", reasoning="r2", status=TaskStatus.COMPLETED),
            )
        )
        viz.update(
            StreamEvent(
                event_type="sample",
                data=VotingSample(id=3, answer="B", reasoning="r3", status=TaskStatus.COMPLETED),
            )
        )
        viz.update(StreamEvent(event_type="voting_complete", data="done"))
        result = viz.render()
        assert isinstance(result, Group)

    def test_progress_bar(self):
        from agent_reasoning.visualization.voting_viz import VotingVisualizer

        viz = VotingVisualizer()
        bar = viz._make_progress_bar(3, 5, width=10)
        assert "3/5" in bar

    def test_progress_bar_zero_total(self):
        from agent_reasoning.visualization.voting_viz import VotingVisualizer

        viz = VotingVisualizer()
        bar = viz._make_progress_bar(0, 0, width=10)
        assert "0/0" in bar


# ---------------------------------------------------------------------------
# TaskVisualizer (decomposed / least_to_most)
# ---------------------------------------------------------------------------
class TestTaskVisualizer:
    def test_instantiation(self):
        from agent_reasoning.visualization.task_viz import TaskVisualizer

        viz = TaskVisualizer()
        assert viz.tasks == {}

    def test_render_empty(self):
        from agent_reasoning.visualization.task_viz import TaskVisualizer

        viz = TaskVisualizer(query="test")
        result = viz.render()
        assert result is not None

    def test_update_task(self):
        from agent_reasoning.visualization.task_viz import TaskVisualizer

        viz = TaskVisualizer()
        task = SubTask(id=1, description="Parse the input", status=TaskStatus.RUNNING, progress=0.5)
        viz.update(StreamEvent(event_type="task", data=task))
        assert 1 in viz.tasks
        assert viz.tasks[1].progress == 0.5

    def test_render_with_tasks(self):
        from agent_reasoning.visualization.task_viz import TaskVisualizer

        viz = TaskVisualizer(query="Plan a trip")
        viz.update(
            StreamEvent(
                event_type="task",
                data=SubTask(
                    id=1,
                    description="Find flights",
                    status=TaskStatus.COMPLETED,
                    progress=1.0,
                    result="Found 3 flights",
                ),
            )
        )
        viz.update(
            StreamEvent(
                event_type="task",
                data=SubTask(
                    id=2, description="Book hotel", status=TaskStatus.RUNNING, progress=0.3
                ),
            )
        )
        viz.update(
            StreamEvent(
                event_type="task",
                data=SubTask(id=3, description="Plan activities", status=TaskStatus.PENDING),
            )
        )
        result = viz.render()
        assert isinstance(result, Group)

    def test_progress_bar(self):
        from agent_reasoning.visualization.task_viz import TaskVisualizer

        viz = TaskVisualizer()
        bar = viz._make_progress_bar(0.75)
        assert "75%" in bar

    def test_update_query(self):
        from agent_reasoning.visualization.task_viz import TaskVisualizer

        viz = TaskVisualizer()
        viz.update(StreamEvent(event_type="query", data="new query"))
        assert viz.query == "new query"

    def test_task_status_icons(self):
        from agent_reasoning.visualization.task_viz import TaskVisualizer

        viz = TaskVisualizer()
        for status in TaskStatus:
            assert status in viz.STATUS_ICONS


# ---------------------------------------------------------------------------
# DiffVisualizer (reflection / refinement)
# ---------------------------------------------------------------------------
class TestDiffVisualizer:
    def test_instantiation(self):
        from agent_reasoning.visualization.diff_viz import DiffVisualizer

        viz = DiffVisualizer()
        assert viz.iterations == {}
        assert viz.mode == "reflection"

    def test_render_empty(self):
        from agent_reasoning.visualization.diff_viz import DiffVisualizer

        viz = DiffVisualizer(query="test")
        result = viz.render()
        assert result is not None

    def test_update_reflection_iteration(self):
        from agent_reasoning.visualization.diff_viz import DiffVisualizer

        viz = DiffVisualizer()
        iteration = ReflectionIteration(
            iteration=1, draft="first draft", critique="needs work", improvement="better draft"
        )
        viz.update(StreamEvent(event_type="iteration", data=iteration))
        assert 1 in viz.iterations
        assert viz.mode == "reflection"

    def test_update_refinement_iteration(self):
        from agent_reasoning.visualization.diff_viz import DiffVisualizer

        viz = DiffVisualizer()
        iteration = RefinementIteration(
            iteration=1, draft="first draft", critique="needs work", score=0.6
        )
        viz.update(StreamEvent(event_type="refinement", data=iteration))
        assert 1 in viz.iterations
        assert viz.mode == "refinement"

    def test_render_reflection_with_iterations(self):
        from agent_reasoning.visualization.diff_viz import DiffVisualizer

        viz = DiffVisualizer(query="Write something good")
        viz.update(
            StreamEvent(
                event_type="iteration",
                data=ReflectionIteration(
                    iteration=1,
                    draft="draft one",
                    critique="too short",
                    improvement="draft one extended",
                ),
            )
        )
        viz.update(
            StreamEvent(
                event_type="iteration",
                data=ReflectionIteration(
                    iteration=2,
                    draft="draft one extended",
                    critique="better",
                    improvement="final version",
                    is_correct=True,
                ),
            )
        )
        result = viz.render()
        assert isinstance(result, Group)

    def test_render_refinement_with_accepted(self):
        from agent_reasoning.visualization.diff_viz import DiffVisualizer

        viz = DiffVisualizer(query="test")
        viz.update(
            StreamEvent(
                event_type="refinement",
                data=RefinementIteration(
                    iteration=1, draft="version 1", critique="low quality", score=0.4
                ),
            )
        )
        viz.update(
            StreamEvent(
                event_type="refinement",
                data=RefinementIteration(
                    iteration=2, draft="version 2", critique="great", score=0.95, is_accepted=True
                ),
            )
        )
        result = viz.render()
        assert isinstance(result, Group)

    def test_compute_diff(self):
        from agent_reasoning.visualization.diff_viz import DiffVisualizer

        viz = DiffVisualizer()
        result = viz._compute_diff("hello world", "hello beautiful world")
        # Should return a Rich Text object
        assert result is not None

    def test_update_phase(self):
        from agent_reasoning.visualization.diff_viz import DiffVisualizer

        viz = DiffVisualizer()
        viz.update(StreamEvent(event_type="phase", data="critique"))
        assert viz.current_phase == "critique"

    def test_is_iteration_complete_reflection(self):
        from agent_reasoning.visualization.diff_viz import DiffVisualizer

        viz = DiffVisualizer()
        r = ReflectionIteration(iteration=1, is_correct=True)
        assert viz._is_iteration_complete(r) is True
        r2 = ReflectionIteration(iteration=2, is_correct=False)
        assert viz._is_iteration_complete(r2) is False

    def test_is_iteration_complete_refinement(self):
        from agent_reasoning.visualization.diff_viz import DiffVisualizer

        viz = DiffVisualizer()
        r = RefinementIteration(iteration=1, is_accepted=True)
        assert viz._is_iteration_complete(r) is True
        r2 = RefinementIteration(iteration=2, is_accepted=False)
        assert viz._is_iteration_complete(r2) is False


# ---------------------------------------------------------------------------
# DebateVisualizer (debate / adversarial)
# ---------------------------------------------------------------------------
class TestDebateVisualizer:
    def test_instantiation(self):
        from agent_reasoning.visualization.debate_viz import DebateVisualizer

        viz = DebateVisualizer()
        assert viz.rounds == {}
        assert viz.rounds_config == 3

    def test_instantiation_with_rounds(self):
        from agent_reasoning.visualization.debate_viz import DebateVisualizer

        viz = DebateVisualizer(rounds=5)
        assert viz.rounds_config == 5

    def test_render_empty(self):
        from agent_reasoning.visualization.debate_viz import DebateVisualizer

        viz = DebateVisualizer(query="test")
        result = viz.render()
        assert result is not None

    def test_update_debate_round(self):
        from agent_reasoning.visualization.debate_viz import DebateVisualizer

        viz = DebateVisualizer()
        rnd = DebateRound(
            round_num=1,
            pro_argument="pro says yes",
            con_argument="con says no",
            winner="pro",
            judge_score_pro=7.5,
            judge_score_con=5.0,
            judge_commentary="Pro was stronger",
        )
        viz.update(StreamEvent(event_type="debate_round", data=rnd))
        assert 1 in viz.rounds
        assert viz.rounds[1].winner == "pro"

    def test_update_final(self):
        from agent_reasoning.visualization.debate_viz import DebateVisualizer

        viz = DebateVisualizer()
        viz.update(StreamEvent(event_type="final", data="synthesis here"))
        assert viz.final_answer == "synthesis here"

    def test_render_with_rounds(self):
        from agent_reasoning.visualization.debate_viz import DebateVisualizer

        viz = DebateVisualizer(query="Is AI good?")
        viz.update(
            StreamEvent(
                event_type="debate_round",
                data=DebateRound(
                    round_num=1,
                    pro_argument="AI helps society",
                    con_argument="AI has risks",
                    winner="pro",
                    judge_score_pro=8.0,
                    judge_score_con=6.0,
                    judge_commentary="Good points",
                ),
            )
        )
        viz.update(
            StreamEvent(
                event_type="debate_round",
                data=DebateRound(
                    round_num=2,
                    pro_argument="AI saves lives",
                    con_argument="AI replaces jobs",
                    winner="con",
                    judge_score_pro=6.0,
                    judge_score_con=7.0,
                    judge_commentary="Valid concern",
                ),
            )
        )
        result = viz.render()
        assert isinstance(result, Group)

    def test_render_with_final_answer(self):
        from agent_reasoning.visualization.debate_viz import DebateVisualizer

        viz = DebateVisualizer(query="test")
        viz.update(
            StreamEvent(
                event_type="debate_round",
                data=DebateRound(round_num=1, pro_argument="pro", con_argument="con"),
            )
        )
        viz.update(StreamEvent(event_type="final", data="Both sides have merit"))
        result = viz.render()
        assert isinstance(result, Group)


# ---------------------------------------------------------------------------
# SocraticVisualizer (socratic / questioning)
# ---------------------------------------------------------------------------
class TestSocraticVisualizer:
    def test_instantiation(self):
        from agent_reasoning.visualization.socratic_viz import SocraticVisualizer

        viz = SocraticVisualizer()
        assert viz.exchanges == {}
        assert viz.max_questions == 5

    def test_render_empty(self):
        from agent_reasoning.visualization.socratic_viz import SocraticVisualizer

        viz = SocraticVisualizer(query="test")
        result = viz.render()
        assert result is not None

    def test_update_exchange(self):
        from agent_reasoning.visualization.socratic_viz import SocraticVisualizer

        viz = SocraticVisualizer()
        exchange = SocraticExchange(
            question_num=1, question="What is X?", answer="X is Y", narrows_to="focus on Y"
        )
        viz.update(StreamEvent(event_type="socratic", data=exchange))
        assert 1 in viz.exchanges
        assert viz.exchanges[1].question == "What is X?"

    def test_update_query(self):
        from agent_reasoning.visualization.socratic_viz import SocraticVisualizer

        viz = SocraticVisualizer()
        viz.update(StreamEvent(event_type="query", data="Why is the sky blue?"))
        assert viz.query == "Why is the sky blue?"

    def test_update_final(self):
        from agent_reasoning.visualization.socratic_viz import SocraticVisualizer

        viz = SocraticVisualizer()
        viz.update(StreamEvent(event_type="final", data="final synthesis"))
        assert viz.final_answer == "final synthesis"

    def test_render_with_exchanges(self):
        from agent_reasoning.visualization.socratic_viz import SocraticVisualizer

        viz = SocraticVisualizer(query="Why is the sky blue?")
        viz.update(
            StreamEvent(
                event_type="socratic",
                data=SocraticExchange(
                    question_num=1,
                    question="What causes color?",
                    answer="Light scattering",
                    narrows_to="Rayleigh scattering",
                ),
            )
        )
        viz.update(
            StreamEvent(
                event_type="socratic",
                data=SocraticExchange(
                    question_num=2,
                    question="What is Rayleigh scattering?",
                    answer="Short wavelengths scatter more",
                ),
            )
        )
        result = viz.render()
        assert isinstance(result, Group)

    def test_render_with_synthesis(self):
        from agent_reasoning.visualization.socratic_viz import SocraticVisualizer

        viz = SocraticVisualizer(query="test")
        viz.update(
            StreamEvent(
                event_type="socratic",
                data=SocraticExchange(question_num=1, question="Q1", answer="A1"),
            )
        )
        viz.update(
            StreamEvent(
                event_type="socratic",
                data=SocraticExchange(
                    question_num=99,
                    question="",
                    answer="Final synthesis answer",
                    is_final_synthesis=True,
                ),
            )
        )
        result = viz.render()
        assert isinstance(result, Group)

    def test_render_with_final_answer_fallback(self):
        from agent_reasoning.visualization.socratic_viz import SocraticVisualizer

        viz = SocraticVisualizer(query="test")
        viz.update(
            StreamEvent(
                event_type="socratic",
                data=SocraticExchange(question_num=1, question="Q", answer="A"),
            )
        )
        viz.update(StreamEvent(event_type="final", data="Fallback final"))
        result = viz.render()
        assert isinstance(result, Group)


# ---------------------------------------------------------------------------
# AnalogyVisualizer (analogy / analogical)
# ---------------------------------------------------------------------------
class TestAnalogyVisualizer:
    def test_instantiation(self):
        from agent_reasoning.visualization.analogy_viz import AnalogyVisualizer

        viz = AnalogyVisualizer()
        assert viz.mappings == []
        assert viz.current_phase == "identify"

    def test_render_empty(self):
        from agent_reasoning.visualization.analogy_viz import AnalogyVisualizer

        viz = AnalogyVisualizer(query="test")
        result = viz.render()
        assert result is not None

    def test_update_mapping_identify(self):
        from agent_reasoning.visualization.analogy_viz import AnalogyVisualizer

        viz = AnalogyVisualizer()
        mapping = AnalogyMapping(step=1, phase="identify", abstract_structure="pattern recognition")
        viz.update(StreamEvent(event_type="analogy", data=mapping))
        assert len(viz.mappings) == 1
        assert viz.current_phase == "identify"

    def test_update_mapping_generate(self):
        from agent_reasoning.visualization.analogy_viz import AnalogyVisualizer

        viz = AnalogyVisualizer()
        mapping = AnalogyMapping(step=1, phase="generate", source_domain="biology")
        viz.update(StreamEvent(event_type="analogy", data=mapping))
        assert viz.current_phase == "generate"

    def test_update_mapping_transfer(self):
        from agent_reasoning.visualization.analogy_viz import AnalogyVisualizer

        viz = AnalogyVisualizer()
        mapping = AnalogyMapping(
            step=1, phase="transfer", solution_transfer="Apply biological pattern to software"
        )
        viz.update(StreamEvent(event_type="analogy", data=mapping))
        assert viz.current_phase == "transfer"

    def test_update_with_is_update_flag(self):
        from agent_reasoning.visualization.analogy_viz import AnalogyVisualizer

        viz = AnalogyVisualizer()
        viz.update(
            StreamEvent(
                event_type="analogy",
                data=AnalogyMapping(step=1, phase="identify", abstract_structure="v1"),
            )
        )
        assert len(viz.mappings) == 1
        viz.update(
            StreamEvent(
                event_type="analogy",
                data=AnalogyMapping(step=1, phase="identify", abstract_structure="v2"),
                is_update=True,
            )
        )
        assert len(viz.mappings) == 1
        assert viz.mappings[0].abstract_structure == "v2"

    def test_update_final(self):
        from agent_reasoning.visualization.analogy_viz import AnalogyVisualizer

        viz = AnalogyVisualizer()
        viz.update(StreamEvent(event_type="final", data="answer via analogy"))
        assert viz.final_answer == "answer via analogy"

    def test_render_full_pipeline(self):
        from agent_reasoning.visualization.analogy_viz import AnalogyVisualizer

        viz = AnalogyVisualizer(query="How to optimize a network?")
        viz.update(
            StreamEvent(
                event_type="analogy",
                data=AnalogyMapping(
                    step=1, phase="identify", abstract_structure="Flow optimization"
                ),
            )
        )
        viz.update(
            StreamEvent(
                event_type="analogy",
                data=AnalogyMapping(
                    step=2,
                    phase="generate",
                    source_domain="Plumbing: water pipes use pressure differentials",
                ),
            )
        )
        viz.update(
            StreamEvent(
                event_type="analogy",
                data=AnalogyMapping(
                    step=3,
                    phase="transfer",
                    solution_transfer="Use traffic shaping like pressure regulators",
                ),
            )
        )
        viz.update(StreamEvent(event_type="final", data="Apply traffic shaping"))
        result = viz.render()
        assert isinstance(result, Group)

    def test_phase_icons_and_colors(self):
        from agent_reasoning.visualization.analogy_viz import AnalogyVisualizer

        viz = AnalogyVisualizer()
        assert "identify" in viz.PHASE_ICONS
        assert "generate" in viz.PHASE_ICONS
        assert "transfer" in viz.PHASE_ICONS
        assert "identify" in viz.PHASE_COLORS
        assert "generate" in viz.PHASE_COLORS
        assert "transfer" in viz.PHASE_COLORS


# ---------------------------------------------------------------------------
# BaseVisualizer
# ---------------------------------------------------------------------------
class TestBaseVisualizer:
    def test_reset(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer(query="test")
        viz.state["key"] = "value"
        viz.reset()
        assert viz.state == {}

    def test_default_console(self):
        from agent_reasoning.visualization.step_viz import StepVisualizer

        viz = StepVisualizer()
        assert viz.console is not None

    def test_custom_console(self):
        from rich.console import Console

        from agent_reasoning.visualization.step_viz import StepVisualizer

        custom = Console(force_terminal=True)
        viz = StepVisualizer(console=custom)
        assert viz.console is custom
