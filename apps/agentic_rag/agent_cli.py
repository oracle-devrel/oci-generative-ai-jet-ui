#!/usr/bin/env python3
import os
import sys
import subprocess
import time
from src.load_model import ensure_model_loaded, get_db_connection
from typing import Optional, List
from threading import Thread
import textwrap

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import print as rprint
    import questionary
except ImportError:
    print(
        "Error: 'rich' and 'questionary' libraries are required. Please install them with: pip install rich questionary"
    )
    sys.exit(1)

console = Console()


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def run_command(cmd, desc="Running..."):
    with console.status(f"[bold green]{desc}...[/bold green]"):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                console.print(f"[green]Done![/green]")
                if result.stdout:
                    console.print(result.stdout)
            else:
                console.print(f"[red]Error (code {result.returncode}):[/red]")
                console.print(result.stderr)
        except Exception as e:
            console.print(f"[red]Failed to execute command: {e}[/red]")


def print_header():
    clear_screen()
    console.print(
        Panel.fit(
            "[bold cyan]AGENTIC RAG SYSTEM CLI[/bold cyan]\n[dim]Oracle AI Vector Search + Ollama (Qwen3.5:9b)[/dim]",
            border_style="cyan",
        )
    )
    console.print(f"[dim]Working Directory: {os.getcwd()}[/dim]\n")


def menu_process_pdfs():
    print_header()

    choices = [
        questionary.Choice("Process a single PDF file", value="1"),
        questionary.Choice("Process all PDFs in a directory", value="2"),
        questionary.Choice("Process a PDF from URL", value="3"),
        questionary.Separator(),
        questionary.Choice("Back to Main Menu", value="0"),
    ]

    choice = questionary.select("PDF Processor", choices=choices, use_arrow_keys=True).ask()

    if not choice or choice == "0":
        return

    output_file = Prompt.ask("Output JSON file path", default="chunks.json")

    if choice == "1":
        input_path = Prompt.ask("Enter path to PDF file")
        if not os.path.exists(input_path):
            console.print(f"[red]File not found: {input_path}[/red]")
            input("Press Enter to continue...")
            return
        run_command(
            ["python", "-m", "src.pdf_processor", "--input", input_path, "--output", output_file],
            "Processing PDF...",
        )

    elif choice == "2":
        input_path = Prompt.ask("Enter directory path")
        if not os.path.isdir(input_path):
            console.print(f"[red]Directory not found: {input_path}[/red]")
            input("Press Enter to continue...")
            return
        run_command(
            ["python", "-m", "src.pdf_processor", "--input", input_path, "--output", output_file],
            "Processing Directory...",
        )

    elif choice == "3":
        input_url = Prompt.ask("Enter PDF URL")
        run_command(
            ["python", "-m", "src.pdf_processor", "--input", input_url, "--output", output_file],
            "Downloading and Processing PDF...",
        )

    input("\nPress Enter to continue...")


def menu_process_websites():
    print_header()

    choices = [
        questionary.Choice("Process a single website URL", value="1"),
        questionary.Choice("Process multiple URLs from a file", value="2"),
        questionary.Separator(),
        questionary.Choice("Back to Main Menu", value="0"),
    ]

    choice = questionary.select("Website Processor", choices=choices, use_arrow_keys=True).ask()

    if not choice or choice == "0":
        return

    output_file = Prompt.ask("Output JSON file path", default="docs/web_content.json")

    if choice == "1":
        url = Prompt.ask("Enter website URL")
        run_command(
            ["python", "-m", "src.web_processor", "--input", url, "--output", output_file],
            "Processing Website...",
        )

    elif choice == "2":
        input_file = Prompt.ask("Enter URLs file path", default="urls.txt")
        if not os.path.exists(input_file):
            console.print(f"[red]File not found: {input_file}[/red]")
            input("Press Enter to continue...")
            return
        run_command(
            ["python", "-m", "src.web_processor", "--input", input_file, "--output", output_file],
            "Processing URLs from file...",
        )

    input("\nPress Enter to continue...")


def menu_manage_vector_store():
    print_header()

    choices = [
        questionary.Choice("Add PDF chunks to vector store", value="1"),
        questionary.Choice("Add Web chunks to vector store", value="2"),
        questionary.Choice("Query vector store directly", value="3"),
        questionary.Choice("Check Vector Store Statistics", value="4"),
        questionary.Separator(),
        questionary.Choice("Back to Main Menu", value="0"),
    ]

    choice = questionary.select("Manage Vector Store", choices=choices, use_arrow_keys=True).ask()

    if not choice or choice == "0":
        return

    if choice == "1":
        input_file = Prompt.ask("Enter chunks JSON file", default="chunks.json")
        if not os.path.exists(input_file):
            console.print(f"[red]File not found: {input_file}[/red]")
            input("Press Enter to continue...")
            return
        run_command(["python", "-m", "src.store", "--add", input_file], "Adding PDF chunks...")

    elif choice == "2":
        input_file = Prompt.ask("Enter web content JSON file", default="docs/web_content.json")
        if not os.path.exists(input_file):
            console.print(f"[red]File not found: {input_file}[/red]")
            input("Press Enter to continue...")
            return
        run_command(["python", "-m", "src.store", "--add-web", input_file], "Adding Web chunks...")

    elif choice == "3":
        query = Prompt.ask("Enter search query")
        run_command(["python", "-m", "src.store", "--query", query], "Querying Vector Store...")

    elif choice == "4":
        run_command(["python", "-m", "src.db_stats"], "Fetching Statistics...")

    input("\nPress Enter to continue...")


def menu_test_oradb():
    print_header()

    choices = [
        questionary.Choice("Run basic connection tests", value="1"),
        questionary.Choice("Show collection statistics only", value="2"),
        questionary.Choice("Run text similarity search", value="3"),
        questionary.Choice("Verify ONNX Model", value="4"),
        questionary.Separator(),
        questionary.Choice("Back to Main Menu", value="0"),
    ]

    choice = questionary.select(
        "Test Oracle DB Connection", choices=choices, use_arrow_keys=True
    ).ask()

    if not choice or choice == "0":
        return

    if choice == "1":
        run_command(["python", "tests/test_oradb.py"], "Testing Oracle DB...")

    elif choice == "2":
        run_command(["python", "tests/test_oradb.py", "--stats-only"], "Fetching Stats...")

    elif choice == "3":
        query = Prompt.ask("Enter test query", default="artificial intelligence")
        run_command(["python", "tests/test_oradb.py", "--query", query], "Running Vector Search...")

    elif choice == "4":
        run_command(["python", "tests/test_oradb.py", "--model-check"], "Verifying ONNX Model...")

    input("\nPress Enter to continue...")


def menu_rag_agent():
    while True:
        print_header()
        console.print("[bold yellow]RAG Agent Chat (Qwen3.5:9b)[/bold yellow]")
        console.print("Enter your query to chat with the agent.")
        console.print("Type 'exit' or '0' to return to main menu.")

        query = Prompt.ask("\n[bold green]Query[/bold green]")

        if query.lower() in ["exit", "quit", "0"]:
            break

        use_cot = Confirm.ask("Use Chain of Thought reasoning?", default=False)

        cmd = ["python", "-m", "src.local_rag_agent", "--query", query]
        if use_cot:
            cmd.append("--use-cot")

        run_command(cmd, "Generating Answer...")
        input("\nPress Enter to continue...")


def main_menu():
    while True:
        print_header()

        choices = [
            questionary.Choice("Process PDFs", value="1"),
            questionary.Choice("Process Websites", value="2"),
            questionary.Choice("Manage Vector Store", value="3"),
            questionary.Choice("Test Oracle DB", value="4"),
            questionary.Choice("Chat with Agent (RAG)", value="5"),
            questionary.Separator(),
            questionary.Choice("Exit", value="0"),
        ]

        choice = questionary.select("Select a Task:", choices=choices, use_arrow_keys=True).ask()

        if not choice or choice == "0":
            console.print("[bold]Goodbye![/bold]")
            sys.exit(0)
        elif choice == "1":
            menu_process_pdfs()
        elif choice == "2":
            menu_process_websites()
        elif choice == "3":
            menu_manage_vector_store()
        elif choice == "4":
            menu_test_oradb()
        elif choice == "5":
            menu_rag_agent()


if __name__ == "__main__":
    try:
        console.print("[bold cyan]Checking AI Model availability...[/bold cyan]")
        if not ensure_model_loaded(get_db_connection()):
            console.print(
                "[bold red]Failed to ensure AI model is loaded. Some features may not work.[/bold red]"
            )
            input("Press Enter to continue anyway...")

        main_menu()
    except KeyboardInterrupt:
        console.print("\n[bold red]Interrupted by user. Exiting...[/bold red]")
        sys.exit(0)
