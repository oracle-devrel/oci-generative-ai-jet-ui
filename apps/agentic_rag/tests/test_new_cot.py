import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

# from rag_agent import RAGAgent # Removed
from src.local_rag_agent import LocalRAGAgent
from src.store import VectorStore

# Configure rich console
console = Console()

def run_multi_agent_cot(agent, query: str, description: str):
    """Run a multi-agent Chain of Thought test case"""
    console.print(f"\n[bold cyan]Test Case: {description}")
    console.print(Panel(f"Query: {query}", style="yellow"))

    # Process query with multi-agent CoT
    response = agent.process_query(query)

    # Print each step's result
    if response.get("reasoning_steps"):
        for i, step in enumerate(response["reasoning_steps"]):
            console.print(Panel(
                f"[bold]Step {i+1}:[/bold]\n{step}",
                title=f"Reasoning Step {i+1}",
                style="blue"
            ))

    # Print final answer
    console.print(Panel(
        f"[bold]Final Answer:[/bold]\n{response['answer']}",
        title="Synthesized Response",
        style="green"
    ))

    # Print sources if available
    if response.get("context"):
        console.print("\n[bold]Sources Used:[/bold]")
        for ctx in response["context"]:
            source = ctx["metadata"].get("source", "Unknown")
            if "page_numbers" in ctx["metadata"]:
                pages = ctx["metadata"].get("page_numbers", [])
                console.print(f"- {source} (pages: {pages})")
            else:
                file_path = ctx["metadata"].get("file_path", "Unknown")
                console.print(f"- {source} (file: {file_path})")

def main():
    parser = argparse.ArgumentParser(description="Test multi-agent Chain of Thought reasoning")
    parser.add_argument("--model", default='local', help="Model to use (default: local gemma3:270m)")
    parser.add_argument("--store-path", default="embeddings", help="Path to the vector store")
    args = parser.parse_args()

    # Load environment variables and config
    load_dotenv()

    console.print("\n[bold]Testing Multi-Agent Chain of Thought System[/bold]")
    console.print("=" * 80)

    try:
        # Initialize vector store
        # Try Oracle first, then Chroma
        try:
            from src.OraDBVectorStore import OraDBVectorStore
            store = OraDBVectorStore()
            console.print("[green]Using Oracle DB Vector Store[/green]")
        except ImportError:
            store = VectorStore(persist_directory=args.store_path)
            console.print("[yellow]Using ChromaDB Vector Store[/yellow]")

        # Initialize appropriate agent
        # Always use LocalRAGAgent with gemma3:270m
        agent = LocalRAGAgent(store, model_name="gemma3:270m", use_cot=True)
        model_name = "gemma3:270m"

        console.print(f"\n[bold]Using {model_name} with Multi-Agent CoT[/bold]")
        console.print("=" * 80)

        # Test cases that demonstrate multi-agent CoT benefits
        test_cases = [
            {
                "query": "What are the key differences between traditional RAG systems and the agentic RAG approach implemented in this project?",
                "description": "Complex comparison requiring analysis of implementation details"
            },
            {
                "query": "How does the system handle PDF document processing and what are the main steps involved?",
                "description": "Technical process analysis requiring step-by-step breakdown"
            },
            {
                "query": "What are the advantages and limitations of using local LLMs versus cloud-based models in this implementation?",
                "description": "Trade-off analysis requiring multiple perspectives"
            }
        ]

        # Run test cases
        for test_case in test_cases:
            run_multi_agent_cot(agent, test_case["query"], test_case["description"])
            console.print("\n" + "=" * 80)

    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
