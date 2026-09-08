"""Tests for strategy recommender."""

import pytest

from agent_reasoning.recommender import recommend, recommend_one


class TestRecommender:
    def test_puzzle_recommends_tot(self):
        recs = recommend("I have a 3-gallon jug and a 5-gallon jug puzzle")
        assert recs[0].strategy == "tot"

    def test_calculation_recommends_react(self):
        recs = recommend("Calculate the square root of 144 and look up current CEO of Google")
        strategies = [r.strategy for r in recs]
        assert "react" in strategies

    def test_philosophy_recommends_consistency(self):
        recs = recommend("What is the meaning of life from a philosophical perspective?")
        strategies = [r.strategy for r in recs]
        assert "consistency" in strategies

    def test_planning_recommends_decomposed(self):
        recs = recommend("Plan a 3-day itinerary for Tokyo")
        assert recs[0].strategy == "decomposed"

    def test_writing_recommends_reflection(self):
        recs = recommend("Write an essay about climate change and review it")
        strategies = [r.strategy for r in recs]
        assert "reflection" in strategies

    def test_debate_recommends_debate(self):
        recs = recommend("What are the pros and cons of remote work?")
        assert recs[0].strategy == "debate"

    def test_empty_query_returns_standard(self):
        recs = recommend("")
        assert recs[0].strategy == "standard"

    def test_generic_query_includes_standard_fallback(self):
        recs = recommend("Hello world")
        strategies = [r.strategy for r in recs]
        assert "standard" in strategies

    def test_recommend_one_returns_string(self):
        result = recommend_one("Solve this riddle about river crossing")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_top_k_limits_results(self):
        recs = recommend("Complex puzzle with philosophy and planning", top_k=2)
        assert len(recs) <= 2

    def test_confidence_range(self):
        recs = recommend("What are the pros and cons of AI debate?")
        for r in recs:
            assert 0.0 <= r.confidence <= 1.0

    def test_recommendation_has_reason(self):
        recs = recommend("Plan a project schedule")
        for r in recs:
            assert len(r.reason) > 0

    def test_physics_recommends_least_to_most(self):
        recs = recommend("A complex physics problem about relativistic time dilation")
        strategies = [r.strategy for r in recs]
        assert "least_to_most" in strategies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
