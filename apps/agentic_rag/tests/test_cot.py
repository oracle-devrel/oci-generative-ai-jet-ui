import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from src.local_rag_agent import LocalRAGAgent

# from rag_agent import RAGAgent  # Removed as we are standardizing on LocalRAGAgent
from src.store import VectorStore

console = Console()

def load_config():
    """Load configuration from config.yaml and .env"""
    try:
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
        load_dotenv()
        return {
            'hf_token': config.get('HUGGING_FACE_HUB_TOKEN'),
            'openai_key': os.getenv('OPENAI_API_KEY')
        }
    except Exception as e:
        console.print(f"[red]Error loading configuration: {str(e)}")
        sys.exit(1)

def compare_responses(agent, query: str, description: str):
    """Compare standard vs CoT responses for the same query"""
    console.print(f"\n[bold cyan]Test Case: {description}")
    console.print(Panel(f"Query: {query}", style="yellow"))

    # Standard response
    agent.use_cot = False
    standard_response = agent.process_query(query)
    console.print(Panel(
        "[bold]Standard Response:[/bold]\n" + standard_response["answer"],
        title="Without Chain of Thought",
        style="blue"
    ))

    # CoT response
    agent.use_cot = True
    cot_response = agent.process_query(query)
    console.print(Panel(
        "[bold]Chain of Thought Response:[/bold]\n" + cot_response["answer"],
        title="With Chain of Thought",
        style="green"
    ))

def main():
    parser = argparse.ArgumentParser(description="Compare standard vs Chain of Thought prompting")
    parser.add_argument("--model", default='local', help="Model to use (default: gemma3:270m)")
    _args = parser.parse_args()

    _config = load_config()

    # Try Oracle first, then Chroma
    try:
        from src.OraDBVectorStore import OraDBVectorStore
        store = OraDBVectorStore()
        console.print("[green]Using Oracle DB Vector Store[/green]")
    except ImportError:
        store = VectorStore(persist_directory="embeddings")
        console.print("[yellow]Using ChromaDB Vector Store[/yellow]")

    # Initialize agent
    agent = LocalRAGAgent(store, model_name="gemma3:270m")
    model_name = "gemma3:270m"

    console.print(f"\n[bold]Testing {model_name} Responses[/bold]")
    console.print("=" * 80)

    # Test cases that highlight CoT benefits
    test_cases = [
        {
            "query": "A train travels at 60 mph for 2.5 hours, then at 45 mph for 1.5 hours. What's the total distance covered?",
            "description": "Multi-step math problem"
        },
        {
            "query": "Compare and contrast REST and GraphQL APIs, considering their strengths and use cases.",
            "description": "Complex comparison requiring structured analysis"
        },
        {
            "query": "If a tree falls in a forest and no one is around to hear it, does it make a sound? Explain your reasoning.",
            "description": "Philosophical question requiring detailed reasoning"
        }
    ]

    for test_case in test_cases:
        try:
            compare_responses(agent, test_case["query"], test_case["description"])
        except Exception as e:
            console.print(f"[red]Error in test case '{test_case['description']}': {str(e)}")

    console.print("\n[bold green]Testing complete!")

if __name__ == "__main__":
    main()
