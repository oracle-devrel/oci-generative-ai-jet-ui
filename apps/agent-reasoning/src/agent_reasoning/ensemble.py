"""
ReasoningEnsemble: Run multiple reasoning strategies in parallel with majority voting.

Usage:
    from agent_reasoning.ensemble import ReasoningEnsemble

    ensemble = ReasoningEnsemble(model_name="gemma3:270m")
    result = await ensemble.run(
        query="What is 2+2?",
        strategies=["cot", "tot", "consistency"]
    )
    print(result["winner"]["response"])
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from agent_reasoning.agents import AGENT_MAP


class ReasoningEnsemble:
    """
    Orchestrates multiple reasoning strategies in parallel and aggregates
    results via majority voting using semantic similarity clustering.
    """

    def __init__(
        self,
        model_name: str = "gemma3:270m",
        similarity_threshold: float = 0.85,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize the ensemble.

        Args:
            model_name: Base LLM model to use for all strategies
            similarity_threshold: Cosine similarity threshold for clustering (0.0-1.0)
            embedding_model: Sentence transformer model for response embeddings
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.embedding_model_name = embedding_model
        self._embedding_model = None
        self._executor = ThreadPoolExecutor(max_workers=10)

    @property
    def embedding_model(self):
        """Lazy load embedding model."""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._embedding_model = SentenceTransformer(self.embedding_model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers required for ensemble voting. "
                    "Install with: pip install sentence-transformers"
                )
        return self._embedding_model

    @property
    def available_strategies(self) -> List[str]:
        """Return list of available strategy names."""
        return list(set(AGENT_MAP.keys()))

    async def run(
        self, query: str, strategies: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run ensemble of reasoning strategies.

        Args:
            query: The question/prompt to process
            strategies: List of strategy names to run (e.g., ["cot", "tot"])
            config: Optional per-strategy configuration
                   e.g., {"tot": {"depth": 3}, "consistency": {"samples": 5}}

        Returns:
            Dict with keys:
                - winner: {strategy, response, vote_count}
                - all_responses: [{strategy, response, duration_ms}, ...]
                - total_duration_ms: float
                - voting_details: {clusters, threshold}
        """
        config = config or {}
        start_time = time.time()

        # Validate strategies
        valid_strategies = []
        for s in strategies:
            if s in AGENT_MAP:
                valid_strategies.append(s)
            else:
                print(f"Warning: Unknown strategy '{s}', skipping")

        if not valid_strategies:
            return {
                "winner": {
                    "strategy": None,
                    "response": "No valid strategies provided",
                    "vote_count": 0,
                },
                "all_responses": [],
                "total_duration_ms": 0,
                "voting_details": None,
            }

        # Single strategy - return directly without voting
        if len(valid_strategies) == 1:
            strategy = valid_strategies[0]
            strategy_config = config.get(strategy, {})
            response, duration = await self._run_single_strategy(query, strategy, strategy_config)

            return {
                "winner": {"strategy": strategy, "response": response, "vote_count": 1},
                "all_responses": [
                    {"strategy": strategy, "response": response, "duration_ms": duration}
                ],
                "total_duration_ms": (time.time() - start_time) * 1000,
                "voting_details": None,  # No voting for single strategy
            }

        # Multiple strategies - run in parallel
        responses = await self._run_parallel(query, valid_strategies, config)

        # Perform majority voting
        winner, voting_details = self._majority_vote(responses)

        total_duration = (time.time() - start_time) * 1000

        return {
            "winner": winner,
            "all_responses": responses,
            "total_duration_ms": total_duration,
            "voting_details": voting_details,
        }

    async def _run_single_strategy(
        self, query: str, strategy: str, config: Dict[str, Any]
    ) -> tuple:
        """Run a single strategy and return (response, duration_ms)."""
        start = time.time()

        # Get agent class and instantiate with config
        agent_class = AGENT_MAP[strategy]

        # Pass config params to agent constructor if supported
        try:
            agent = agent_class(model=self.model_name, **config)
        except TypeError:
            # Agent doesn't accept extra kwargs
            agent = agent_class(model=self.model_name)

        # Run in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(self._executor, agent.run, query)

        duration = (time.time() - start) * 1000
        return response, duration

    async def _run_parallel(
        self, query: str, strategies: List[str], config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Run multiple strategies in parallel."""
        tasks = []
        for strategy in strategies:
            strategy_config = config.get(strategy, {})
            task = self._run_single_strategy(query, strategy, strategy_config)
            tasks.append((strategy, task))

        responses = []
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

        for (strategy, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                responses.append(
                    {
                        "strategy": strategy,
                        "response": f"Error: {str(result)}",
                        "duration_ms": 0,
                        "error": True,
                    }
                )
            else:
                response, duration = result
                responses.append(
                    {
                        "strategy": strategy,
                        "response": response,
                        "duration_ms": duration,
                        "error": False,
                    }
                )

        return responses

    def _majority_vote(self, responses: List[Dict[str, Any]]) -> tuple:
        """
        Cluster responses by semantic similarity and return the most common answer.

        Returns:
            (winner_dict, voting_details_dict)
        """
        # Filter out error responses
        valid_responses = [r for r in responses if not r.get("error", False)]

        if not valid_responses:
            return {"strategy": None, "response": "All strategies failed", "vote_count": 0}, {
                "clusters": [],
                "threshold": self.similarity_threshold,
            }

        if len(valid_responses) == 1:
            r = valid_responses[0]
            return {"strategy": r["strategy"], "response": r["response"], "vote_count": 1}, {
                "clusters": [[0]],
                "threshold": self.similarity_threshold,
            }

        # Get embeddings for all responses
        texts = [r["response"] for r in valid_responses]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)

        # Cluster by cosine similarity
        clusters = self._cluster_by_similarity(embeddings)

        # Find largest cluster
        largest_cluster = max(clusters, key=len)
        winner_idx = largest_cluster[0]

        # Handle ties - prefer CoT as fallback
        if len([c for c in clusters if len(c) == len(largest_cluster)]) > 1:
            # Multiple clusters of same size - prefer CoT
            for cluster in clusters:
                if len(cluster) == len(largest_cluster):
                    for idx in cluster:
                        if valid_responses[idx]["strategy"] in ["cot", "chain_of_thought"]:
                            winner_idx = idx
                            largest_cluster = cluster
                            break

        winner = valid_responses[winner_idx]

        return {
            "strategy": winner["strategy"],
            "response": winner["response"],
            "vote_count": len(largest_cluster),
        }, {
            "clusters": clusters,
            "threshold": self.similarity_threshold,
            "total_responses": len(valid_responses),
        }

    def _cluster_by_similarity(self, embeddings) -> List[List[int]]:
        """
        Cluster embeddings by cosine similarity.

        Returns list of clusters, where each cluster is a list of indices.
        """
        n = len(embeddings)

        import numpy as np

        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-10)

        # Compute similarity matrix
        similarity_matrix = np.dot(normalized, normalized.T)

        # Greedy clustering
        assigned = [False] * n
        clusters = []

        for i in range(n):
            if assigned[i]:
                continue

            # Start new cluster with this response
            cluster = [i]
            assigned[i] = True

            # Find all similar responses
            for j in range(i + 1, n):
                if not assigned[j] and similarity_matrix[i, j] >= self.similarity_threshold:
                    cluster.append(j)
                    assigned[j] = True

            clusters.append(cluster)

        return clusters

    def run_sync(
        self, query: str, strategies: List[str], config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for run()."""
        return asyncio.run(self.run(query, strategies, config))
