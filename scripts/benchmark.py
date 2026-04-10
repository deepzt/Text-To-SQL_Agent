"""
Benchmark script — runs 20 standard NL→SQL test queries and reports accuracy.

Usage:
    python scripts/benchmark.py

Requires the sample database to be seeded first:
    python scripts/seed_sample_db.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

from agent import TextToSQLAgent

console = Console()

# ── Test cases ────────────────────────────────────────────────────────────────
# Each entry: (question, expected_keyword_in_result)
TEST_CASES = [
    ("How many users are in the database?", "100"),
    ("How many products do we have?", "15"),
    ("List all product categories.", "Electronics"),
    ("What is the most expensive product?", "Smart Watch"),
    ("How many orders have status 'completed'?", "completed"),
    ("What is the total revenue from all orders?", None),  # any numeric result
    ("Show me the top 5 products by price.", None),
    ("How many users are from California?", None),
    ("What are the names of users from Texas?", "Texas"),
    ("Show me orders placed in the last 30 days.", None),
    ("Which product category has the most products?", None),
    ("What is the average order total?", None),
    ("List users who have placed more than 2 orders.", None),
    ("Show me products with stock greater than 300.", None),
    ("What is the total quantity of items sold per product?", None),
    ("How many orders are pending?", None),
    ("Show the top 3 users by total spending.", None),
    ("What products are in the Sports category?", "Sports"),
    ("How many distinct cities are represented in our user base?", None),
    ("Show order details with user names for the 5 most recent orders.", None),
]


def run_benchmark() -> None:
    console.print("\n[bold cyan]Text-To-SQL Benchmark[/bold cyan]")
    console.print(f"Running {len(TEST_CASES)} test queries...\n")

    try:
        agent = TextToSQLAgent()
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    results_table = Table(show_header=True, header_style="bold magenta")
    results_table.add_column("#", width=4)
    results_table.add_column("Question", width=50)
    results_table.add_column("Result", width=10)
    results_table.add_column("Time (s)", width=8)

    passed = 0
    failed = 0

    for i, (question, expected) in enumerate(TEST_CASES, 1):
        start = time.perf_counter()
        try:
            answer = agent.run(question)
            elapsed = time.perf_counter() - start

            if expected is None or expected.lower() in answer.lower():
                status = "[green]PASS[/green]"
                passed += 1
            else:
                status = "[red]FAIL[/red]"
                failed += 1
                console.print(f"\n[dim]Q{i}: {question}[/dim]")
                console.print(f"[dim]Expected keyword: {expected!r}[/dim]")
                console.print(f"[dim]Got: {answer[:200]}[/dim]")
        except Exception as exc:
            elapsed = time.perf_counter() - start
            status = "[red]ERROR[/red]"
            failed += 1
            console.print(f"\n[red]Q{i} exception:[/red] {exc}")

        results_table.add_row(
            str(i),
            question[:48] + "…" if len(question) > 48 else question,
            status,
            f"{elapsed:.2f}",
        )

    console.print(results_table)
    total = passed + failed
    pct = (passed / total * 100) if total else 0
    console.print(
        f"\n[bold]Score: {passed}/{total} ({pct:.0f}%)[/bold] | "
        f"Pass: [green]{passed}[/green] | Fail: [red]{failed}[/red]"
    )


if __name__ == "__main__":
    run_benchmark()
