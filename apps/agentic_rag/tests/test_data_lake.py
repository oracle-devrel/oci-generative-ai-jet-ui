"""
Test script for the Oracle DB Data Lake Event Logging system

This script demonstrates the data lake functionality by:
1. Initializing the event logger
2. Logging sample events of each type
3. Querying and displaying statistics
4. Showing recent events
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.OraDBEventLogger import OraDBEventLogger
except ImportError:
    print("❌ Error: Could not import OraDBEventLogger")
    print("Make sure Oracle DB credentials are configured in config.yaml")
    sys.exit(1)


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70 + "\n")


def test_event_logging():
    """Test the event logging system"""

    print_section("Oracle DB Data Lake Event Logger Test")

    # Initialize logger
    print("1️⃣ Initializing Event Logger...")
    try:
        logger = OraDBEventLogger()
        print("✅ Event logger initialized successfully\n")
    except Exception as e:
        print(f"❌ Failed to initialize event logger: {str(e)}")
        return

    # Test A2A Event Logging
    print_section("Testing A2A Event Logging")

    print("Logging Planner Agent event...")
    logger.log_a2a_event(
        agent_id="planner_agent_v1",
        agent_name="Strategic Planner",
        method="agent.query",
        system_prompt="You are a strategic planning agent with expertise in problem decomposition.",
        user_prompt="How can I build a distributed RAG system?",
        response="Step 1: Design the architecture\nStep 2: Implement A2A protocol\nStep 3: Deploy specialized agents\nStep 4: Set up monitoring",
        metadata={"query_type": "planning", "steps_generated": 4},
        duration_ms=1234.5,
        status="success"
    )
    print("✅ Planner event logged\n")

    print("Logging Researcher Agent event...")
    logger.log_a2a_event(
        agent_id="researcher_agent_v1",
        agent_name="Deep Researcher",
        method="agent.query",
        system_prompt="You are a research agent with expertise in information gathering.",
        user_prompt="Research distributed systems architecture",
        response="Key findings: Microservices, event-driven architecture, message queues...",
        metadata={"findings_count": 5, "sources_consulted": 3},
        duration_ms=2345.6,
        status="success"
    )
    print("✅ Researcher event logged\n")

    print("Logging Synthesizer Agent event...")
    logger.log_a2a_event(
        agent_id="synthesizer_agent_v1",
        agent_name="Knowledge Synthesizer",
        method="agent.query",
        system_prompt="You are a synthesis agent that combines multiple perspectives.",
        user_prompt="Synthesize findings about distributed RAG",
        response="Based on the research, a distributed RAG system requires careful consideration of...",
        metadata={"reasoning_steps_count": 4},
        duration_ms=1567.8,
        status="success"
    )
    print("✅ Synthesizer event logged\n")

    # Test API Event Logging
    print_section("Testing API Event Logging")

    print("Logging /query endpoint event...")
    logger.log_api_event(
        endpoint="/query",
        method="POST",
        request_data={
            "query": "What is machine learning?",
            "use_cot": True,
            "model": "qwen2"
        },
        response_data={
            "answer_length": 450,
            "context_chunks": 3
        },
        status_code=200,
        duration_ms=3456.7,
        user_agent="Mozilla/5.0",
        client_ip="127.0.0.1"
    )
    print("✅ API event logged\n")

    print("Logging /a2a endpoint event...")
    logger.log_api_event(
        endpoint="/a2a",
        method="POST",
        request_data={
            "method": "document.query",
            "params": {"query": "Explain neural networks", "collection": "PDF"}
        },
        response_data={
            "result": "Neural networks are...",
            "sources": ["paper1.pdf", "paper2.pdf"]
        },
        status_code=200,
        duration_ms=2567.8
    )
    print("✅ A2A API event logged\n")

    # Test Model Event Logging
    print_section("Testing Model Event Logging")

    print("Logging gemma3:270m model inference...")
    logger.log_model_event(
        model_name="gemma3:270m",
        model_type="ollama",
        system_prompt="You are a helpful AI assistant.",
        user_prompt="Explain quantum computing in simple terms",
        response="Quantum computing uses quantum mechanics principles...",
        collection_used="general_knowledge",
        use_cot=False,
        tokens_used=256,
        duration_ms=1890.2,
        context_chunks=0
    )
    print("✅ Model event logged\n")

    print("Logging deepseek-r1 model inference with CoT...")
    logger.log_model_event(
        model_name="deepseek-r1",
        model_type="ollama",
        system_prompt="You are an analytical reasoning agent.",
        user_prompt="How does A2A protocol improve distributed systems?",
        response="Through standardized communication, agent discovery, and task management...",
        collection_used="repository_documents",
        use_cot=True,
        tokens_used=512,
        duration_ms=3456.1,
        context_chunks=5
    )
    print("✅ Model event logged\n")

    # Test Document Event Logging
    print_section("Testing Document Event Logging")

    print("Logging PDF document processing...")
    logger.log_document_event(
        document_type="pdf",
        document_id="doc_12345",
        source="machine_learning_research.pdf",
        chunks_processed=45,
        processing_time_ms=5678.9,
        status="success"
    )
    print("✅ Document event logged\n")

    print("Logging repository processing...")
    logger.log_document_event(
        document_type="repository",
        document_id="repo_67890",
        source="https://github.com/example/agentic-rag",
        chunks_processed=123,
        processing_time_ms=8901.2,
        status="success"
    )
    print("✅ Repository event logged\n")

    # Test Query Event Logging
    print_section("Testing Query Event Logging")

    print("Logging vector store query...")
    logger.log_query_event(
        query_text="machine learning algorithms",
        collection_name="pdf_documents",
        results_count=10,
        query_time_ms=123.4,
        metadata={"similarity_threshold": 0.7}
    )
    print("✅ Query event logged\n")

    # Get Statistics
    print_section("Event Statistics")

    stats = logger.get_statistics()
    print(f"Total Events:          {stats['total_events']}")
    print(f"A2A Events:            {stats['a2a_events']}")
    print(f"API Events:            {stats['api_events']}")
    print(f"Model Events:          {stats['model_events']}")
    print(f"Document Events:       {stats['document_events']}")
    print(f"Query Events:          {stats['query_events']}")
    print(f"\nAvg A2A Duration:      {stats['avg_a2a_duration_ms']:.2f} ms")
    print(f"Avg Model Duration:    {stats['avg_model_duration_ms']:.2f} ms")

    if stats['top_models']:
        print("\nTop Models:")
        for i, model_stat in enumerate(stats['top_models'], 1):
            print(f"  {i}. {model_stat['model']}: {model_stat['count']} calls")

    # Show Recent Events
    print_section("Recent A2A Events (Last 5)")

    recent_events = logger.get_events(event_type="a2a", limit=5)
    for i, event in enumerate(recent_events, 1):
        print(f"{i}. Agent: {event.get('AGENT_NAME', 'Unknown')}")
        print(f"   Method: {event.get('METHOD', 'N/A')}")
        print(f"   Duration: {event.get('DURATION_MS', 0):.2f} ms")
        print(f"   Status: {event.get('STATUS', 'N/A')}")
        print(f"   Time: {event.get('TIMESTAMP', 'N/A')}")
        print()

    # Show Recent Model Events
    print_section("Recent Model Events (Last 3)")

    model_events = logger.get_events(event_type="model", limit=3)
    for i, event in enumerate(model_events, 1):
        print(f"{i}. Model: {event.get('MODEL_NAME', 'Unknown')} ({event.get('MODEL_TYPE', 'N/A')})")
        print(f"   CoT: {'Yes' if event.get('USE_COT') == 1 else 'No'}")
        print(f"   Duration: {event.get('DURATION_MS', 0):.2f} ms")
        print(f"   Context Chunks: {event.get('CONTEXT_CHUNKS', 0)}")
        print(f"   Time: {event.get('TIMESTAMP', 'N/A')}")
        print()

    # Show Event Counts
    print_section("Event Counts by Type")

    for event_type in ["a2a", "api", "model", "document", "query"]:
        count = logger.get_event_count(event_type)
        print(f"{event_type.upper():12s}: {count:6d} events")

    # Close connection
    print_section("Cleanup")
    logger.close()
    print("✅ Database connection closed")

    print_section("Test Complete")
    print("✅ All event types tested successfully!")
    print("\nThe data lake is now storing all events in Oracle AI Database 26ai.")
    print("You can query these events using:")
    print("  - SQL queries directly on the database")
    print("  - REST API endpoints (/events/statistics, /events/{type})")
    print("  - OraDBEventLogger Python API")
    print()


if __name__ == "__main__":
    try:
        test_event_logging()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        import traceback
        print("\nTraceback:")
        print(traceback.format_exc())

