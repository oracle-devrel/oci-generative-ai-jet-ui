"""Tests for ReasoningEnsemble."""

import asyncio
from unittest.mock import patch

import numpy as np
import pytest

from agent_reasoning.ensemble import ReasoningEnsemble


class TestReasoningEnsemble:
    """Test suite for ReasoningEnsemble."""

    def test_available_strategies(self):
        """Test that all strategies are available."""
        ensemble = ReasoningEnsemble()
        strategies = ensemble.available_strategies

        assert "cot" in strategies
        assert "tot" in strategies
        assert "react" in strategies
        assert "consistency" in strategies
        assert "standard" in strategies
        assert "debate" in strategies
        assert "adversarial" in strategies
        assert "mcts" in strategies
        assert "monte_carlo" in strategies
        assert "analogical" in strategies
        assert "analogy" in strategies
        assert "socratic" in strategies
        assert "questioning" in strategies
        assert "meta" in strategies
        assert "auto" in strategies

    def test_single_strategy_no_voting(self):
        """Test that single strategy bypasses voting."""
        ensemble = ReasoningEnsemble()

        with patch.object(ensemble, "_run_single_strategy") as mock_run:
            mock_run.return_value = ("Test response", 100.0)

            result = asyncio.run(ensemble.run("test query", ["cot"]))

            assert result["winner"]["strategy"] == "cot"
            assert result["winner"]["response"] == "Test response"
            assert result["voting_details"] is None

    def test_cluster_by_similarity(self):
        """Test similarity clustering."""
        ensemble = ReasoningEnsemble(similarity_threshold=0.9)

        # Create mock embeddings - two similar, one different
        embeddings = np.array(
            [
                [1.0, 0.0, 0.0],  # Response 0
                [0.99, 0.1, 0.0],  # Response 1 - similar to 0
                [0.0, 1.0, 0.0],  # Response 2 - different
            ]
        )

        clusters = ensemble._cluster_by_similarity(embeddings)

        # Should have 2 clusters
        assert len(clusters) == 2

    def test_invalid_strategy_skipped(self):
        """Test that invalid strategies are skipped with warning."""
        ensemble = ReasoningEnsemble()

        with patch.object(ensemble, "_run_single_strategy") as mock_run:
            mock_run.return_value = ("Test response", 100.0)

            asyncio.run(ensemble.run("test", ["cot", "invalid_strategy"]))

            # Should only run cot
            assert mock_run.call_count == 1

    def test_empty_strategies_returns_error(self):
        """Test handling of empty strategy list."""
        ensemble = ReasoningEnsemble()

        result = asyncio.run(ensemble.run("test", []))

        assert result["winner"]["strategy"] is None
        assert "No valid strategies" in result["winner"]["response"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
