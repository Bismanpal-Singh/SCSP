"""Rich terminal UI helpers for Mantle AI demo runs."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

console = Console()


def _normalize_material_class(value: object) -> str:
    return str(value or "unknown").strip().lower() or "unknown"


def get_material_class_from_candidate_or_spec(candidate: dict, spec: dict | None = None) -> str:
    target_props = dict((spec or {}).get("target_props", {}) or {})
    return _normalize_material_class(
        candidate.get("material_class")
        or target_props.get("material_class")
        or "unknown"
    )


def get_candidate_property(candidate: dict, keys: list[str]) -> object:
    for key in keys:
        value = candidate.get(key)
        if value is not None and value != "":
            return value
    return None


def _supply_chain_risk(candidate: dict) -> int | None:
    risk = get_candidate_property(candidate, ["supply_chain_risk", "china_dependency"])
    if risk is not None:
        return int(float(risk))
    score = get_candidate_property(candidate, ["supply_chain_score", "supply_chain_safety_score"])
    scores = dict(candidate.get("scores", {}) or {})
    if score is None:
        score = scores.get("supply_chain_safety")
    if score is not None:
        return max(0, min(100, 100 - int(float(score))))
    return None


def _supply_risk_line(supply_risk: int | None) -> str:
    if supply_risk is None:
        return "N/A"
    return (
        "[green]0% China dependency[/green]"
        if supply_risk == 0
        else f"[red]{supply_risk}% China dependency[/red]"
    )


def format_final_result_fields(candidate: dict, spec: dict | None = None) -> list[tuple[str, str]]:
    material_class = get_material_class_from_candidate_or_spec(candidate, spec)
    score = int(candidate.get("score", 0) or 0)
    stability = float(candidate.get("stability_above_hull", 1.0) or 1.0)
    band_gap = candidate.get("band_gap")
    band_gap_text = f"{float(band_gap):.3f} eV" if band_gap is not None else "N/A"
    supply_risk = _supply_chain_risk(candidate)
    synthesis = str(candidate.get("synthesis_recommendation", "") or "").strip()
    uncertainty = str(candidate.get("main_uncertainty", "N/A"))
    recommended_experiment = str(
        candidate.get("recommended_experiment", "N/A")
    )

    if not synthesis:
        synthesis = recommended_experiment

    fields: list[tuple[str, str]] = [
        ("Score", f"{score} / 100"),
        ("Supply chain risk", _supply_risk_line(supply_risk)),
    ]

    if material_class == "permanent_magnet":
        magnetic = get_candidate_property(
            candidate,
            ["magnetic_moment", "total_magnetization", "magnetization", "magnetic_moment_total"],
        )
        magnetic_text = f"{float(magnetic):.2f} \u03bcB" if magnetic is not None else "N/A"
        fields.insert(1, ("Magnetic moment", magnetic_text))
        fields.append(("Synthesis route", synthesis or "N/A"))
        return fields

    if material_class == "semiconductor":
        fields.insert(1, ("Band gap", band_gap_text))
        fields.insert(2, ("Stability (E_hull)", f"{stability:.3f} eV/atom"))
        fields.append(("Main uncertainty", uncertainty))
        fields.append(
            (
                "Recommended radiation/electrical test",
                recommended_experiment if recommended_experiment != "N/A" else "TID + electrical characterization (I-V/C-V).",
            )
        )
        return fields

    if material_class == "protective_coating":
        fields.insert(1, ("Chemical/stability proxy", f"E_hull {stability:.3f} eV/atom"))
        fields.append(("Main uncertainty", uncertainty))
        fields.append(
            (
                "Recommended corrosion test",
                recommended_experiment if recommended_experiment != "N/A" else "Salt-spray + electrochemical impedance testing.",
            )
        )
        return fields

    if material_class == "battery_material":
        fields.insert(1, ("Stability (E_hull)", f"{stability:.3f} eV/atom"))
        fields.append(("Cycling/electrochemical uncertainty", uncertainty))
        fields.append(
            (
                "Recommended battery test",
                recommended_experiment if recommended_experiment != "N/A" else "Galvanostatic cycling + rate capability testing.",
            )
        )
        return fields

    if material_class == "high_temperature_structural_material":
        fields.insert(1, ("Stability/thermal proxy", f"E_hull {stability:.3f} eV/atom"))
        fields.append(("Oxidation/manufacturing uncertainty", uncertainty))
        fields.append(
            (
                "Recommended thermal/mechanical test",
                recommended_experiment if recommended_experiment != "N/A" else "High-temperature oxidation + creep testing.",
            )
        )
        return fields

    fields.insert(1, ("Stability (E_hull)", f"{stability:.3f} eV/atom"))
    fields.append(("Main uncertainty", uncertainty))
    fields.append(("Recommended experiment", recommended_experiment))
    return fields


def get_candidate_table_columns(spec: dict | None = None) -> list[tuple[str, str]]:
    material_class = get_material_class_from_candidate_or_spec({}, spec)
    if material_class == "permanent_magnet":
        return [
            ("Formula", "formula"),
            ("Score", "score"),
            ("Magnetic Moment", "magnetic_moment"),
            ("Supply Risk", "supply_risk"),
            ("Status", "status"),
        ]
    if material_class == "semiconductor":
        return [
            ("Formula", "formula"),
            ("Score", "score"),
            ("Band Gap (eV)", "band_gap"),
            ("E_hull", "stability"),
            ("Supply Risk", "supply_risk"),
            ("Status", "status"),
        ]
    return [
        ("Formula", "formula"),
        ("Score", "score"),
        ("E_hull", "stability"),
        ("Family", "family"),
        ("Supply Risk", "supply_risk"),
        ("Status", "status"),
    ]


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
    magnetic_moment: float | None,
    supply_chain_risk: int | None,
    status: str,
    material_class: str = "unknown",
    band_gap: float | None = None,
    stability_above_hull: float | None = None,
    material_family: str | None = None,
) -> None:
    score_style = "green" if score >= 80 else "yellow" if score >= 50 else "red"
    risk_text = (
        f"[green]\u2713 {supply_chain_risk}%[/green]"
        if supply_chain_risk == 0
        else f"[red]\u26A0 {supply_chain_risk}%[/red]" if supply_chain_risk is not None else "N/A"
    )
    spec = {"target_props": {"material_class": _normalize_material_class(material_class)}}
    columns = get_candidate_table_columns(spec)
    table = Table(box=box.SIMPLE_HEAVY)
    for idx, (label, _) in enumerate(columns):
        table.add_column(label, style="bold white" if idx == 0 else None)
    values = {
        "formula": formula,
        "score": f"[{score_style}]{score}[/{score_style}]",
        "magnetic_moment": f"{float(magnetic_moment):.2f}" if magnetic_moment is not None else "N/A",
        "band_gap": f"{float(band_gap):.3f}" if band_gap is not None else "N/A",
        "stability": f"{float(stability_above_hull):.3f}" if stability_above_hull is not None else "N/A",
        "family": str(material_family or "N/A"),
        "supply_risk": risk_text,
        "status": status,
    }
    table.add_row(*[str(values[key]) for _, key in columns])
    console.print(table)


def print_final_result(candidate: dict, spec: dict | None = None) -> None:
    formula = candidate.get("formula", "N/A")
    score = int(candidate.get("score", 0) or 0)

    score_color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
    fields = format_final_result_fields(candidate, spec)
    lines = [f"[bold white]PROMISING COMPUTATIONAL CANDIDATE:[/bold white] [{score_color}]{formula}[/{score_color}]"]
    for label, value in fields:
        lines.append(f"[bold white]{label}:[/bold white] {value}")
    body = "\n".join(lines)
    console.print(
        Panel(
            body,
            title="[bold green]FINAL RESULT[/bold green]",
            border_style="green",
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
        )
    )


def _material_source_label(entry: dict) -> str:
    verification_source = str(entry.get("verification_source", "") or "")
    existence_status = str(entry.get("existence_status", "") or "")
    source = str(entry.get("source", "") or "").lower()
    source_type = str(entry.get("source_type", "") or "")
    source_type_lower = source_type.lower()

    if verification_source == "Materials Project" or existence_status == "VERIFIED_IN_DATABASE":
        return "Materials Project"
    if source_type == "curated_evidence_fallback":
        return "Curated"
    if existence_status == "FAMILY_OR_TEMPLATE":
        return "Template"
    if "llm" in source or "llm" in source_type_lower:
        return "LLM"
    if existence_status == "NOT_FOUND_IN_DATABASE":
        return "LLM / Unverified"
    return "Unknown"


def print_portfolio_table(portfolio: list) -> None:
    table = Table(title="RANKED MATERIAL PORTFOLIO", show_header=True, header_style="bold white")
    table.add_column("Rank", style="bold", width=6)
    table.add_column("Candidate", width=12)
    table.add_column("Status", width=14)
    table.add_column("Source", width=16)
    table.add_column("Overall", width=9)
    table.add_column("Sci Fit", width=9)
    table.add_column("Stability", width=10)
    table.add_column("Supply Risk", width=12)
    table.add_column("Confidence", width=11)

    status_colors = {
        "TEST_FIRST": "green",
        "BACKUP_TEST": "yellow",
        "SAFE_FALLBACK": "cyan",
        "EXPLORE_LATER": "white",
        "INELIGIBLE": "red",
    }

    for i, entry in enumerate((portfolio or [])[:5]):
        scores = dict(entry.get("scores", {}) or {})
        risk = _supply_chain_risk(entry)
        status = str(entry.get("status", "EXPLORE_LATER"))
        color = status_colors.get(status, "white")
        row_style = "bold" if i == 0 else ""
        table.add_row(
            str(entry.get("rank", i + 1)),
            str(entry.get("candidate", "")),
            f"[{color}]{status}[/{color}]",
            _material_source_label(entry),
            str(scores.get("overall", "")),
            str(scores.get("scientific_fit", "")),
            str(scores.get("stability", "")),
            "" if risk is None else str(risk),
            str(scores.get("evidence_confidence", "")),
            style=row_style,
        )
    console.print(table)


def print_ineligible_panel(ineligible: list) -> None:
    if not ineligible:
        console.print(
            Panel(
                "[dim]No candidates failed hard filters in this run.[/dim]",
                title="REJECTED — INELIGIBLE CANDIDATES",
                border_style="red",
            )
        )
        return

    lines = []
    for candidate in ineligible:
        formula = candidate.get("formula", "Unknown")
        reason = candidate.get("reason", "Constraint violation")
        lines.append(f"[red]X[/red] [bold]{formula}[/bold] — {reason}")

    console.print(
        Panel(
            "\n".join(lines),
            title="[red]REJECTED — INELIGIBLE CANDIDATES[/red]",
            border_style="red",
        )
    )


def print_uncertainty_map(portfolio: list) -> None:
    table = Table(title="WHAT WE STILL DON'T KNOW", show_header=True, header_style="bold yellow")
    table.add_column("Material Family", width=16)
    table.add_column("Main Uncertainty", width=40)
    table.add_column("Likely Failure Mode", width=35)

    for entry in (portfolio or [])[:5]:
        if entry.get("status") == "INELIGIBLE":
            continue
        table.add_row(
            str(entry.get("family", "")),
            str(entry.get("main_uncertainty", "")),
            str(entry.get("likely_failure_mode", "")),
        )
    console.print(table)


def print_experiment_tree(final_result: dict) -> None:
    tree = Tree("[bold]MISSION[/bold]: " + str(final_result.get("mission", ""))[:60])

    prov = dict(final_result.get("provenance_tree", {}) or {})
    constraints = dict(prov.get("constraints", {}) or {})

    constraints_branch = tree.add("[bold]Constraints[/bold]")
    constraints_branch.add(f"Material class: {constraints.get('material_class', '')}")
    constraints_branch.add(f"Banned elements: {', '.join(constraints.get('banned_elements', []))}")
    constraints_branch.add(f"Exclude radioactive: {constraints.get('exclude_radioactive', True)}")
    constraints_branch.add(f"Require solid-state: {constraints.get('require_solid_state', True)}")

    search = dict(prov.get("candidate_search", {}) or {})
    search_branch = tree.add("[bold]Candidate Search[/bold]")

    ineligible = list(search.get("ineligible", []) or [])
    if ineligible:
        rejected_branch = search_branch.add("[red]INELIGIBLE[/red]")
        for candidate in ineligible:
            rejected_branch.add(f"[red]X[/red] {candidate.get('formula', 'Unknown')} — {candidate.get('reason', '')}")
    else:
        search_branch.add("[dim]No candidates rejected[/dim]")

    portfolio = list(search.get("portfolio", []) or [])
    portfolio_branch = search_branch.add("[green]PORTFOLIO[/green]")
    for candidate in portfolio:
        portfolio_branch.add(
            f"Rank {candidate.get('rank', '')}: {candidate.get('candidate', '')} [{candidate.get('status', '')}]"
        )

    queue = list(final_result.get("test_queue", []) or [])
    queue_branch = tree.add("[bold cyan]Lab-Ready Test Queue[/bold cyan]")
    for item in queue:
        queue_branch.add(str(item))

    console.print(tree)


def print_test_queue(test_queue: list) -> None:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Num", style="bold cyan", width=4)
    table.add_column("Experiment", width=80)

    for i, item in enumerate(test_queue or [], 1):
        table.add_row(str(i), str(item))

    console.print(
        Panel(
            table,
            title="[bold cyan]LAB-READY TEST QUEUE — HAND OFF TO RESEARCHERS[/bold cyan]",
            border_style="cyan",
        )
    )
