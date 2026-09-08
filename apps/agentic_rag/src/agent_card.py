"""
Agent Card for A2A Protocol

This module defines the agent card that describes the capabilities
and configuration of the agentic_rag system for A2A protocol.
"""

from src.a2a_models import AgentCard, AgentCapability, AgentEndpoint


def get_agent_card() -> dict:
    """Get the agent card for the agentic_rag system"""
    
    # Define capabilities
    capabilities = [
        AgentCapability(
            name="document.query",
            description="Query documents using RAG with context retrieval and intelligent routing",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query string to search for"
                    },
                    "collection": {
                        "type": "string",
                        "enum": ["PDF", "Repository", "Web", "General"],
                        "description": "Specific collection to search (optional)"
                    },
                    "use_cot": {
                        "type": "boolean",
                        "default": False,
                        "description": "Use Chain of Thought reasoning"
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 3,
                        "description": "Maximum number of results to return"
                    }
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "context": {"type": "array"},
                    "sources": {"type": "object"},
                    "reasoning_steps": {"type": "array"},
                    "collection_used": {"type": "string"}
                }
            }
        ),
        AgentCapability(
            name="document.upload",
            description="Process and store documents in vector database",
            input_schema={
                "type": "object",
                "properties": {
                    "document_type": {
                        "type": "string",
                        "enum": ["pdf", "web", "repository"],
                        "description": "Type of document to process"
                    },
                    "content": {
                        "type": "string",
                        "description": "Document content or URL"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional document metadata"
                    }
                },
                "required": ["document_type", "content"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "message": {"type": "string"},
                    "document_id": {"type": "string"},
                    "chunks_processed": {"type": "integer"}
                }
            }
        ),
        AgentCapability(
            name="task.create",
            description="Create long-running tasks for document processing or complex queries",
            input_schema={
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "enum": ["document_processing", "complex_query", "batch_upload"],
                        "description": "Type of task to create"
                    },
                    "params": {
                        "type": "object",
                        "description": "Task-specific parameters"
                    },
                    "priority": {
                        "type": "integer",
                        "default": 0,
                        "description": "Task priority"
                    }
                },
                "required": ["task_type", "params"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {"type": "string"},
                    "message": {"type": "string"}
                }
            }
        ),
        AgentCapability(
            name="task.status",
            description="Check status of long-running tasks",
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID to check"
                    }
                },
                "required": ["task_id"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {"type": "string"},
                    "result": {"type": "object"},
                    "error": {"type": "string"},
                    "progress": {"type": "number"}
                }
            }
        ),
        AgentCapability(
            name="agent.discover",
            description="Discover other agents and their capabilities",
            input_schema={
                "type": "object",
                "properties": {
                    "capability": {
                        "type": "string",
                        "description": "Capability to search for"
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Specific agent ID to find"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "agents": {
                        "type": "array",
                        "items": {"type": "object"}
                    }
                }
            }
        ),
        AgentCapability(
            name="agent.query",
            description="Query specialized Chain of Thought agents (Planner, Researcher, Reasoner, Synthesizer) for distributed multi-agent reasoning",
            input_schema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "enum": ["planner_agent_v1", "researcher_agent_v1", "reasoner_agent_v1", "synthesizer_agent_v1"],
                        "description": "ID of the specialized agent to query"
                    },
                    "query": {
                        "type": "string",
                        "description": "The query or problem to process"
                    },
                    "step": {
                        "type": "string",
                        "description": "Specific step to process (for Researcher/Reasoner)"
                    },
                    "context": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Context from previous agents"
                    },
                    "reasoning_steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "All reasoning steps (for Synthesizer)"
                    }
                },
                "required": ["agent_id", "query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "plan": {"type": "string"},
                    "steps": {"type": "array"},
                    "findings": {"type": "array"},
                    "summary": {"type": "string"},
                    "conclusion": {"type": "string"},
                    "reasoning": {"type": "string"},
                    "answer": {"type": "string"},
                    "agent_id": {"type": "string"}
                }
            }
        ),
        AgentCapability(
            name="health.check",
            description="Check agent health and status",
            input_schema={
                "type": "object",
                "properties": {}
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "timestamp": {"type": "number"},
                    "version": {"type": "string"},
                    "capabilities": {"type": "array"}
                }
            }
        )
    ]
    
    # Define endpoint configuration
    endpoint = AgentEndpoint(
        base_url="http://localhost:8000",
        authentication={
            "type": "bearer_token",
            "required": False,
            "description": "Optional bearer token authentication"
        }
    )
    
    # Create agent card
    agent_card = AgentCard(
        agent_id="agentic_rag_v1",
        name="Agentic RAG System",
        version="1.0.0",
        description="Intelligent RAG system with multi-agent reasoning, supporting document querying, processing, and task management with Chain of Thought capabilities",
        capabilities=capabilities,
        endpoints=endpoint,
        metadata={
            "model_support": ["openai", "mistral", "ollama"],
            "vector_stores": ["oracle_db", "chromadb"],
            "document_types": ["pdf", "web", "repository"],
            "reasoning_modes": ["standard", "chain_of_thought"],
            "max_context_length": 4096,
            "supported_languages": ["en"],
            "deployment_type": "container",
            "resource_requirements": {
                "min_memory": "4GB",
                "recommended_memory": "16GB",
                "gpu_optional": True
            }
        }
    )
    
    return agent_card.model_dump()


def get_agent_card_json() -> str:
    """Get the agent card as a JSON string"""
    import json
    return json.dumps(get_agent_card(), indent=2)
