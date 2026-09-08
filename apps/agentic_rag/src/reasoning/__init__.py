"""
Reasoning module for agentic_rag.

Wraps agent_reasoning library with RAG context, A2A protocol, and database logging.
"""

from .rag_ensemble import RAGReasoningEnsemble

__all__ = ["RAGReasoningEnsemble"]
