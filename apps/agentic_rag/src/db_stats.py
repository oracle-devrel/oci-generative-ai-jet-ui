#!/usr/bin/env python3
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from src.OraDBVectorStore import OraDBVectorStore

console = Console()

def show_stats():
    """Fetch and display vector store statistics"""
    console.print(Panel("[bold cyan]Oracle AI Vector Store Statistics[/bold cyan]", expand=False))
    
    try:
        with console.status("[bold green]Connecting to Oracle Database...[/bold green]"):
            store = OraDBVectorStore()
            
        table = Table(title="Collection Statistics")
        table.add_column("Collection Name", style="cyan", no_wrap=True)
        table.add_column("Table Name", style="magenta")
        table.add_column("Vectors", justify="right", style="green")
        table.add_column("Dimension", justify="right", style="yellow")
        table.add_column("Sample Snippet", style="dim")

        for display_name, table_name in store.collections.items():
            # Get stats
            count = store.get_collection_count(display_name)
            dimension = store.get_embedding_dimension(display_name)
            # Use get_latest_chunk directly to get snippet, ignore timestamp
            latest_chunk = store.get_latest_chunk(display_name)
            
            snippet = latest_chunk.get("content", "")
            if snippet:
                snippet = snippet[:50] + "..."
            else:
                snippet = "N/A"
            
            table.add_row(
                display_name,
                table_name,
                str(count),
                str(dimension),
                snippet
            )
            
        console.print(table)
        
        # Additional DB Info
        console.print("\n[bold]Database Info:[/bold]")
        console.print(f"• Connection: {store.connection.dsn}")
        console.print(f"• User: {store.connection.username}")
        console.print(f"• Driver: {store.connection.version}")
        
    except Exception as e:
        console.print(f"[bold red]Error fetching statistics:[/bold red] {e}")

if __name__ == "__main__":
    show_stats()
