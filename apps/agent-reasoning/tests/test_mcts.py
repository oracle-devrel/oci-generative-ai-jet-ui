"""Tests for MCTSAgent."""

import math
from unittest.mock import MagicMock, patch

import pytest


def _make_agent(max_simulations=3, exploration_constant=1.414, max_children=2):
    """Create an MCTSAgent with mocked internals."""
    with patch("agent_reasoning.agents.mcts.BaseAgent.__init__", return_value=None):
        from agent_reasoning.agents.mcts import MCTSAgent

        agent = MCTSAgent.__new__(MCTSAgent)
        agent.name = "MCTSAgent"
        agent.color = "blue"
        agent.max_simulations = max_simulations
        agent.exploration_constant = exploration_constant
        agent.max_children = max_children
        agent.client = MagicMock()
        return agent


def test_mcts_agent_emits_nodes():
    """MCTSAgent should emit mcts_node events."""
    agent = _make_agent(max_simulations=3)
    agent.client.generate = MagicMock(return_value=iter(["Test response 0.7"]))

    events = list(agent.stream_structured("Solve: 2+2"))
    event_types = [e.event_type for e in events]
    assert "mcts_node" in event_types
    assert "final" in event_types


def test_mcts_ucb1_prefers_unexplored():
    """UCB1 should prefer unexplored nodes over well-explored ones."""
    agent = _make_agent()
    # Unexplored node (visits=0) should return infinity
    score_unexplored = agent._ucb1(wins=0, visits=0, parent_visits=20)
    assert score_unexplored == float("inf")
    # Explored node should return finite value
    score_explored = agent._ucb1(wins=5, visits=10, parent_visits=20)
    expected = 5 / 10 + 1.414 * math.sqrt(math.log(20) / 10)
    assert abs(score_explored - expected) < 0.01


def test_mcts_run_returns_string():
    """MCTSAgent.run() should return a string."""
    agent = _make_agent(max_simulations=2)
    agent.client.generate = MagicMock(return_value=iter(["0.7"]))

    result = agent.run("test")
    assert isinstance(result, str)


def test_mcts_backpropagation():
    """Backpropagation should update visits and wins from leaf to root."""
    from agent_reasoning.visualization.models import MCTSNode

    agent = _make_agent()

    root = MCTSNode(id="N0", depth=0, content="root")
    child = MCTSNode(id="N1", depth=1, content="child", parent_id="N0")
    grandchild = MCTSNode(id="N2", depth=2, content="grandchild", parent_id="N1")

    tree = {
        "N0": {"node": root, "children": ["N1"], "thought_path": "root"},
        "N1": {"node": child, "children": ["N2"], "thought_path": "root\nchild"},
        "N2": {"node": grandchild, "children": [], "thought_path": "root\nchild\ngrandchild"},
    }

    agent._backpropagate(tree, "N2", 0.8)

    assert grandchild.visits == 1
    assert grandchild.wins == 0.8
    assert child.visits == 1
    assert child.wins == 0.8
    assert root.visits == 1
    assert root.wins == 0.8


def test_mcts_selection_picks_unexplored():
    """Selection should prefer nodes that can still be expanded."""
    from agent_reasoning.visualization.models import MCTSNode

    agent = _make_agent(max_children=2)

    root = MCTSNode(id="N0", depth=0, content="root", visits=5, wins=2.0)
    child1 = MCTSNode(id="N1", depth=1, content="child1", parent_id="N0", visits=3, wins=1.5)

    tree = {
        "N0": {"node": root, "children": ["N1"], "thought_path": "root"},
        "N1": {"node": child1, "children": [], "thought_path": "root\nchild1"},
    }

    # Root has only 1 child but max_children=2, so root should be selected
    selected = agent._select(tree, "N0")
    assert selected == "N0"


def test_mcts_selection_uses_ucb1():
    """Selection should use UCB1 to pick among fully-expanded children."""
    from agent_reasoning.visualization.models import MCTSNode

    agent = _make_agent(max_children=2)

    root = MCTSNode(id="N0", depth=0, content="root", visits=10, wins=5.0)
    child1 = MCTSNode(id="N1", depth=1, content="child1", parent_id="N0", visits=5, wins=4.0)
    child2 = MCTSNode(id="N2", depth=1, content="child2", parent_id="N0", visits=5, wins=1.0)

    tree = {
        "N0": {"node": root, "children": ["N1", "N2"], "thought_path": "root"},
        "N1": {"node": child1, "children": [], "thought_path": "root\nchild1"},
        "N2": {"node": child2, "children": [], "thought_path": "root\nchild2"},
    }

    # Root is fully expanded (2 children == max_children), so selection should
    # descend to a child. child1 has better win rate (4/5 vs 1/5).
    selected = agent._select(tree, "N0")
    assert selected == "N1"


def test_mcts_best_path():
    """Best path should follow highest win-rate children from root."""
    from agent_reasoning.visualization.models import MCTSNode

    agent = _make_agent()

    root = MCTSNode(id="N0", depth=0, content="root", visits=10, wins=5.0)
    child1 = MCTSNode(id="N1", depth=1, content="good", parent_id="N0", visits=7, wins=6.0)
    child2 = MCTSNode(id="N2", depth=1, content="bad", parent_id="N0", visits=3, wins=0.5)
    grandchild = MCTSNode(id="N3", depth=2, content="great", parent_id="N1", visits=4, wins=3.5)

    tree = {
        "N0": {"node": root, "children": ["N1", "N2"], "thought_path": "root"},
        "N1": {"node": child1, "children": ["N3"], "thought_path": "root\ngood"},
        "N2": {"node": child2, "children": [], "thought_path": "root\nbad"},
        "N3": {"node": grandchild, "children": [], "thought_path": "root\ngood\ngreat"},
    }

    path = agent._best_path(tree, "N0")
    assert path == ["N0", "N1", "N3"]


def test_mcts_stream_yields_text():
    """MCTSAgent.stream() should yield text strings."""
    agent = _make_agent(max_simulations=2)
    agent.client.generate = MagicMock(return_value=iter(["0.7"]))

    chunks = list(agent.stream("test"))
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_mcts_ucb1_values():
    """UCB1 should compute correct values for various inputs."""
    agent = _make_agent(exploration_constant=1.0)

    # With exploration_constant=1.0, the formula is: wins/visits + sqrt(ln(parent)/visits)
    score = agent._ucb1(wins=3, visits=6, parent_visits=10)
    expected = 3 / 6 + 1.0 * math.sqrt(math.log(10) / 6)
    assert abs(score - expected) < 0.001

    # Higher exploration constant should increase the exploration term
    agent.exploration_constant = 2.0
    score_high_c = agent._ucb1(wins=3, visits=6, parent_visits=10)
    assert score_high_c > score


def test_mcts_event_count():
    """MCTSAgent should emit the right number of mcts_node events."""
    num_sims = 4
    agent = _make_agent(max_simulations=num_sims)
    agent.client.generate = MagicMock(return_value=iter(["0.6"]))

    events = list(agent.stream_structured("test query"))
    mcts_events = [e for e in events if e.event_type == "mcts_node"]

    # At minimum: 1 root + 1 per simulation (expansion) + 1 per simulation (update)
    # + best path updates
    assert len(mcts_events) >= 1 + num_sims


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
