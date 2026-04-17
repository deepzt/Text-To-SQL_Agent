"""
Text-To-SQL Agent — CLI entry point.

Single-query mode:
    python main.py "show me the top 5 products by revenue"

Interactive REPL mode (no arguments):
    python main.py
"""

from __future__ import annotations

import logging
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from config import Config

console = Console()

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


class _Display:
    """Manages interleaved status lines and streamed tokens cleanly."""

    def __init__(self) -> None:
        self._mid_stream = False

    def status(self, msg: str) -> None:
        if self._mid_stream:
            print()
            self._mid_stream = False
        console.print(f"[dim cyan]  › {msg}[/dim cyan]")

    def token(self, t: str) -> None:
        self._mid_stream = True
        print(t, end="", flush=True)

    def finish(self) -> None:
        if self._mid_stream:
            print()
            self._mid_stream = False


def run_query(agent, query: str, history: list[dict]) -> str:
    display = _Display()
    answer = agent.run(
        query,
        conversation_history=history,
        on_status=display.status,
        on_token=display.token,
    )
    display.finish()
    return answer


def main() -> None:
    # Lazy import to avoid loading heavy deps before we need them
    from agent import TextToSQLAgent

    try:
        agent = TextToSQLAgent()
    except RuntimeError as exc:
        console.print(f"[bold red]Startup error:[/bold red] {exc}")
        console.print(
            "[yellow]Tip:[/yellow] Run [bold]python scripts/seed_sample_db.py[/bold] "
            "to create the sample database."
        )
        sys.exit(1)

    provider_label = Config.LLM_PROVIDER.upper()
    model = Config.OLLAMA_MODEL if Config.LLM_PROVIDER == "ollama" else Config.CLAUDE_MODEL

    console.print(
        Panel(
            f"[bold green]Text-To-SQL Agent[/bold green]\n"
            f"Provider: [cyan]{provider_label}[/cyan] | Model: [cyan]{model}[/cyan]\n"
            f"Database: [cyan]{Config.DATABASE_URL}[/cyan]",
            title="Ready",
        )
    )

    # ── Single-query mode ─────────────────────────────────────────────────────
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        console.print(f"\n[bold]Query:[/bold] {query}\n")
        answer = run_query(agent, query, [])
        console.print(Markdown(answer))
        return

    # ── Interactive REPL mode ─────────────────────────────────────────────────
    console.print("\nType your question in plain English. Type [bold]exit[/bold] to quit.\n")
    history: list[dict] = []

    while True:
        try:
            query = Prompt.ask("[bold blue]You[/bold blue]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if query.strip().lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        if not query.strip():
            continue

        answer = run_query(agent, query, history)
        console.print(f"\n[bold green]Agent:[/bold green]")
        console.print(Markdown(answer))
        console.print()

        # Keep last 10 turns in history for multi-turn context
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})
        if len(history) > 20:
            history = history[-20:]


if __name__ == "__main__":
    main()
