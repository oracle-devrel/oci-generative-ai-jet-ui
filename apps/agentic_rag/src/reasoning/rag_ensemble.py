"""
RAGReasoningEnsemble: Extends agent_reasoning.ReasoningEnsemble with RAG integration.

Adds:
- RAG context retrieval before reasoning
- Database logging of reasoning events
- Streaming execution trace for UI
"""
import asyncio
import time
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from agent_reasoning import ReasoningEnsemble


@dataclass
class ExecutionEvent:
    timestamp: str
    event_type: str
    message: str
    data: Optional[Dict[str, Any]] = None


@dataclass
class ReasoningResult:
    winner: Dict[str, Any]
    all_responses: List[Dict[str, Any]]
    execution_trace: List[ExecutionEvent]
    rag_context: Optional[Dict[str, Any]]
    total_duration_ms: float
    voting_details: Optional[Dict[str, Any]]


class RAGReasoningEnsemble:
    """
    Extends ReasoningEnsemble with RAG context retrieval and database logging.

    Usage:
        ensemble = RAGReasoningEnsemble(
            model_name="qwen3.5:9b",
            vector_store=my_vector_store,
            event_logger=my_event_logger
        )

        result = await ensemble.run(
            query="What is machine learning?",
            strategies=["cot", "tot"],
            use_rag=True,
            collection="PDF"
        )
    """
    STRATEGY_ICONS = {
        'standard': '📝',
        'cot': '🔗',
        'chain_of_thought': '🔗',
        'tot': '🌳',
        'tree_of_thoughts': '🌳',
        'react': '🛠️',
        'self_reflection': '🪞',
        'reflection': '🪞',
        'consistency': '🔄',
        'self_consistency': '🔄',
        'decomposed': '🧩',
        'least_to_most': '📈',
        'ltm': '📈',
        'recursive': '🔁',
        'rlm': '🔁',
    }
    STRATEGY_NAMES = {
        'standard': 'Standard',
        'cot': 'Chain-of-Thought',
        'chain_of_thought': 'Chain-of-Thought',
        'tot': 'Tree of Thoughts',
        'tree_of_thoughts': 'Tree of Thoughts',
        'react': 'ReAct',
        'self_reflection': 'Self-Reflection',
        'reflection': 'Self-Reflection',
        'consistency': 'Self-Consistency',
        'self_consistency': 'Self-Consistency',
        'decomposed': 'Decomposed',
        'least_to_most': 'Least-to-Most',
        'ltm': 'Least-to-Most',
        'recursive': 'Recursive',
        'rlm': 'Recursive',
    }

    def __init__(self, model_name="qwen3.5:9b", vector_store=None, event_logger=None, similarity_threshold=0.85):
        """
        Initialize RAGReasoningEnsemble.

        Args:
            model_name: Base LLM model for reasoning
            vector_store: Vector store for RAG retrieval (OraDBVectorStore)
            event_logger: OraDBEventLogger for logging reasoning events
            similarity_threshold: Threshold for majority voting clustering
        """
        self.model_name = model_name
        self.vector_store = vector_store
        self.event_logger = event_logger
        self.ensemble = ReasoningEnsemble(model_name=model_name, similarity_threshold=similarity_threshold)

    @property
    def available_strategies(self):
        """Return list of available strategy keys."""
        return [
            'standard',
            'cot',
            'tot',
            'react',
            'self_reflection',
            'consistency',
            'decomposed',
            'least_to_most',
            'recursive',
        ]

    def get_strategy_display_name(self, strategy):
        """Get human-readable name for strategy."""
        return self.STRATEGY_NAMES.get(strategy, strategy.title())

    def get_strategy_icon(self, strategy):
        """Get emoji icon for strategy."""
        return self.STRATEGY_ICONS.get(strategy, '🤖')

    async def run(
        self,
        query: str,
        strategies: List[str],
        use_rag: bool = True,
        collection: str = "PDF",
        config: Optional[Dict[str, Any]] = None,
    ) -> ReasoningResult:
        """
        Run reasoning ensemble with optional RAG context.

        Args:
            query: User's question
            strategies: List of strategy names to run
            use_rag: Whether to retrieve RAG context first
            collection: Which collection to query ("PDF", "Web", "Repository", "General")
            config: Per-strategy configuration

        Returns:
            ReasoningResult with winner, all responses, execution trace, etc.
        """
        start_time = time.time()
        execution_trace = []
        rag_context = None

        def log_event(event_type, message, data=None):
            event = ExecutionEvent(
                timestamp=datetime.now().strftime('%H:%M:%S'),
                event_type=event_type,
                message=message,
                data=data,
            )
            execution_trace.append(event)
            return event

        log_event('start', f'Starting ensemble with {len(strategies)} strategies')
        augmented_query = query
        if use_rag and self.vector_store:
            log_event('rag', f'Retrieving context from {collection} Collection...')
            rag_context = await self._retrieve_context(query, collection)
            if rag_context and rag_context.get('chunks'):
                chunks_count = len(rag_context['chunks'])
                avg_score = rag_context.get('avg_score', 0)
                log_event('rag', f'Found {chunks_count} relevant chunks (score: {avg_score:.2f})', {
                    'chunks': chunks_count,
                    'score': avg_score,
                })
                augmented_query = self._build_augmented_prompt(query, rag_context)
            else:
                log_event('rag', 'No relevant context found, proceeding without RAG')
        log_event('strategy_start', 'Launching strategies in parallel...')
        for strategy in strategies:
            icon = self.get_strategy_icon(strategy)
            name = self.get_strategy_display_name(strategy)
            log_event('strategy_start', f'{icon} {name}: Starting...')
        result = await self.ensemble.run(augmented_query, strategies, config)
        for resp in result['all_responses']:
            icon = self.get_strategy_icon(resp['strategy'])
            name = self.get_strategy_display_name(resp['strategy'])
            duration = resp['duration_ms'] / 1000
            if resp.get('error'):
                log_event('strategy_complete', f'❌ {name}: Failed', {
                    'error': True,
                })
                continue
            log_event('strategy_complete', f'✅ {name}: Complete ({duration:.1f}s)', {
                'duration_ms': resp['duration_ms'],
            })
        if result['voting_details']:
            log_event('voting', f'Clustering {len(result["all_responses"])} responses...')
            winner = result['winner']
            icon = self.get_strategy_icon(winner['strategy'])
            name = self.get_strategy_display_name(winner['strategy'])
            log_event('voting', f'🏆 Winner: {name} ({winner["vote_count"]}/{len(result["all_responses"])} votes)')
        total_duration = (time.time() - start_time) * 1000
        log_event('complete', f'Ensemble complete ({total_duration / 1000:.1f}s total)')
        if self.event_logger:
            await self._log_reasoning_event(
                query=query,
                strategies=strategies,
                result=result,
                rag_context=rag_context,
                use_rag=use_rag,
                collection=collection,
                total_duration_ms=total_duration,
            )
        return ReasoningResult(
            winner=result['winner'],
            all_responses=result['all_responses'],
            execution_trace=execution_trace,
            rag_context=rag_context,
            total_duration_ms=total_duration,
            voting_details=result['voting_details'],
        )

    async def run_with_streaming(
        self,
        query: str,
        strategies: List[str],
        use_rag: bool = True,
        collection: str = "PDF",
        config: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """
        Run ensemble with streaming execution events for real-time UI updates.

        Yields ExecutionEvent objects as they occur.
        Final event has event_type="result" with full ReasoningResult in data.
        """
        start_time = time.time()
        rag_context = None

        def make_event(event_type, message, data=None):
            return ExecutionEvent(
                timestamp=datetime.now().strftime('%H:%M:%S'),
                event_type=event_type,
                message=message,
                data=data,
            )

        yield make_event('start', f'Starting ensemble with {len(strategies)} strategies')
        augmented_query = query
        if use_rag and self.vector_store:
            yield make_event('rag', f'Retrieving context from {collection} Collection...')
            rag_context = await self._retrieve_context(query, collection)
            if rag_context and rag_context.get('chunks'):
                chunks_count = len(rag_context['chunks'])
                avg_score = rag_context.get('avg_score', 0)
                yield make_event('rag', f'Found {chunks_count} relevant chunks (score: {avg_score:.2f})')
                augmented_query = self._build_augmented_prompt(query, rag_context)
            else:
                yield make_event('rag', 'No relevant context found')
        yield make_event('strategy_start', 'Launching strategies in parallel...')
        for strategy in strategies:
            icon = self.get_strategy_icon(strategy)
            name = self.get_strategy_display_name(strategy)
            yield make_event('strategy_start', f'{icon} {name}: Starting...')
        result = await self.ensemble.run(augmented_query, strategies, config)
        for resp in result['all_responses']:
            icon = self.get_strategy_icon(resp['strategy'])
            name = self.get_strategy_display_name(resp['strategy'])
            duration = resp['duration_ms'] / 1000
            yield make_event('strategy_complete', f'✅ {name}: Complete ({duration:.1f}s)')
        if result['voting_details']:
            yield make_event('voting', f'Clustering {len(result["all_responses"])} responses...')
            winner = result['winner']
            name = self.get_strategy_display_name(winner['strategy'])
            yield make_event('voting', f'🏆 Winner: {name} ({winner["vote_count"]} votes)')
        total_duration = (time.time() - start_time) * 1000
        yield make_event('complete', f'Ensemble complete ({total_duration / 1000:.1f}s)')
        final_result = ReasoningResult(
            winner=result['winner'],
            all_responses=result['all_responses'],
            execution_trace=[],
            rag_context=rag_context,
            total_duration_ms=total_duration,
            voting_details=result['voting_details'],
        )
        yield make_event('result', 'Final result', {
            'result': final_result,
        })

    async def _retrieve_context(self, query, collection):
        """Retrieve relevant context from vector store."""
        if not self.vector_store:
            return None
        # Map UI collection label to the matching OraDBVectorStore/store method.
        # OraDBVectorStore exposes query_pdf_collection, query_web_collection,
        # query_general_collection, query_repo_collection -- not a single .query().
        method_map = {
            'PDF': 'query_pdf_collection',
            'Web': 'query_web_collection',
            'Repository': 'query_repo_collection',
            'General': 'query_general_collection',
        }
        method_name = method_map.get(collection, 'query_pdf_collection')
        query_method = getattr(self.vector_store, method_name, None)
        if query_method is None:
            return None
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, lambda: query_method(query, n_results=5)
        )
        if not results:
            return None
        chunks = []
        scores = []
        sources = set()
        for doc in results:
            chunks.append({
                'content': doc.get('content', doc.get('text', '')),
                'metadata': doc.get('metadata', {}),
                'score': doc.get('score', 0),
            })
            scores.append(doc.get('score', 0))
            if 'source' in doc.get('metadata', {}):
                sources.add(doc['metadata']['source'])
        return {
            'chunks': chunks,
            'sources': list(sources),
            'avg_score': sum(scores) / len(scores) if scores else 0,
        }

    def _build_augmented_prompt(self, query, context):
        """Build prompt with RAG context."""
        context_text = '\n\n'.join(
            [f'[Source: {c["metadata"].get("source", "unknown")}]\n{c["content"]}' for c in context.get('chunks', [])]
        )
        return (
            f"Use the following context to answer the question. "
            f"If the context doesn't contain relevant information, use your general knowledge.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {query}\n\n"
            f"Answer:"
        )

    async def _log_reasoning_event(self, query, strategies, result, rag_context, use_rag, collection, total_duration_ms):
        """Log reasoning event to database."""
        if not self.event_logger:
            return None
        try:
            self.event_logger.log_reasoning_event(
                query_text=query,
                strategies_requested=strategies,
                winner_strategy=result['winner']['strategy'],
                winner_response=result['winner']['response'],
                vote_count=result['winner']['vote_count'],
                all_responses=result['all_responses'],
                rag_enabled=use_rag,
                collection_used=collection if use_rag else None,
                chunks_retrieved=len(rag_context['chunks']) if rag_context else 0,
                total_duration_ms=total_duration_ms,
                config=None,
                status='success',
            )
        except Exception:
            return None
