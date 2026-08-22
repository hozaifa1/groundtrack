"""
Main application entry point for IBM Bob Challenge.
"""
import sys
from rich.console import Console

console = Console()

def main():
    console.print("[bold green]====================================================[/bold green]")
    console.print("[bold cyan]  IBM Bob Challenge — AI Builders Prototype Initialized[/bold cyan]")
    console.print("[bold green]====================================================[/bold green]")
    console.print("[yellow]Core System:[/] Ready")
    console.print("[yellow]Agent Engine:[/] Initialized via IBM Bob directives")
    console.print("[dim]Use IBM Bob (Plan/Agent/Ask modes) to expand this project.[/dim]\n")

if __name__ == "__main__":
    main()
