"""Rich terminal UI helpers for CriticalMat demo runs."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

console = Console()


def print_header(hypothesis: str) -> None:
    title = Text("CRITICALMAT", style="bold white")
    body = Text.assemble(
        ("AI-Accelerated Critical Minerals Discovery\n\n", "bold cyan"),
        ("Hypothesis:\n", "bold white"),
        (hypothesis, "white"),
    )
    console.print(
        Panel(
            body,
            title=title,
            border_style="bright_blue",
            box=box.DOUBLE,
            padding=(1, 2),
        )
    )


def print_status_line(text: str) -> None:
    """Render existing loop status lines in consistent UI styling."""
    console.print(f"[bold white]{text}[/bold white]")


def print_notice(text: str, style: str = "yellow") -> None:
    """Render non-step notices (fast mode, convergence, fallbacks)."""
    console.print(f"[bold {style}]{text}[/bold {style}]")


def print_iteration(n: int, total: int, candidates_tested: int, best_score: int) -> None:
    console.print(f"\n[bold cyan]Iteration {n} / {total}[/bold cyan]")
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=36),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    )
    task_id = progress.add_task("Loop progress", total=total, completed=n)
    progress.refresh()
    progress.stop()
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_row("Candidates tested", str(candidates_tested))
    table.add_row("Best score so far", str(best_score))
    console.print(table)


def print_reasoning(text: str, iteration: int) -> None:
    console.print(
        Panel(
            text,
            title=f"[bold magenta]AI REASONING - Iteration {iteration}[/bold magenta]",
            border_style="magenta",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )


def print_candidate(
    formula: str,
    score: int,
    magnetic_moment: float,
    supply_chain_risk: int,
    status: str,
) -> None:
    score_style = "green" if score >= 80 else "yellow" if score >= 50 else "red"
    risk_text = (
        f"[green]\u2713 {supply_chain_risk}%[/green]"
        if supply_chain_risk == 0
        else f"[red]\u26A0 {supply_chain_risk}%[/red]"
    )
    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("Formula", style="bold white")
    table.add_column("Score")
    table.add_column("Magnetic Moment")
    table.add_column("Supply Risk")
    table.add_column("Status")
    table.add_row(
        formula,
        f"[{score_style}]{score}[/{score_style}]",
        f"{magnetic_moment:.2f}",
        risk_text,
        status,
    )
    console.print(table)


def print_final_result(candidate: dict) -> None:
    formula = candidate.get("formula", "N/A")
    score = int(candidate.get("score", 0) or 0)
    magnetic_moment = float(candidate.get("magnetic_moment", 0.0) or 0.0)
    supply_risk = int(candidate.get("supply_chain_risk", 0) or 0)
    synthesis = candidate.get("synthesis_recommendation", "No synthesis recommendation available.")

    score_color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
    risk_line = (
        "[green]0% China dependency[/green]"
        if supply_risk == 0
        else f"[red]{supply_risk}% China dependency[/red]"
    )

    body = (
        f"[bold white]WINNER:[/bold white] [{score_color}]{formula}[/{score_color}]\n"
        f"[bold white]Score:[/bold white] [{score_color}]{score} / 100[/{score_color}]\n"
        f"[bold white]Magnetic moment:[/bold white] {magnetic_moment:.2f} μB\n"
        f"[bold white]Supply chain risk:[/bold white] {risk_line}\n"
        f"[bold white]Synthesis route:[/bold white] {synthesis}"
    )
    console.print(
        Panel(
            body,
            title="[bold green]FINAL RESULT[/bold green]",
            border_style="green",
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
        )
    )
