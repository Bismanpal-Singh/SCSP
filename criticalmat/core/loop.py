"""Main autonomous loop for CriticalMat.

Hour 3+ integration status:
- P1 (`materials/search.py`, `materials/scorer.py`) is wired and enabled by default.
- P2 (`agents/agent.py`) parse, interpretation, and next-hypothesis are wired when available.
- Safe fallbacks keep loop runnable if API keys/dependencies are unavailable.
"""

from __future__ import annotations

from .memory import AgentMemory
from . import mocks
from ..materials.search import apply_hard_filters
from ..demo import (
    print_candidate,
    print_experiment_tree,
    print_final_result,
    print_header,
    print_ineligible_panel,
    print_iteration,
    print_notice,
    print_portfolio_table,
    print_reasoning,
    print_status_line,
    print_test_queue,
    print_uncertainty_map,
)


def _has_converged(best_scores: list[int]) -> bool:
    """Converge if score has not improved in two iterations."""
    if len(best_scores) < 3:
        return False
    return best_scores[-1] <= best_scores[-2] <= best_scores[-3]


def _is_candidate_eligible(candidate: dict) -> bool:
    """Prefer explicit eligibility flags, then practicality fallback."""
    if "eligible" in candidate:
        return bool(candidate.get("eligible"))
    if "is_practical" in candidate:
        return bool(candidate.get("is_practical"))
    return True


def _candidate_rejection_reason(candidate: dict) -> str:
    """Build concise rejection reasons from available candidate annotations."""
    reasons = candidate.get("ineligibility_reasons")
    if isinstance(reasons, list) and reasons:
        return "; ".join(str(r) for r in reasons)

    fallback_reasons: list[str] = []
    if candidate.get("is_radioactive") is True:
        fallback_reasons.append("contains radioactive element(s)")
    if candidate.get("is_solid_likely") is False:
        fallback_reasons.append("not likely solid-state")
    if candidate.get("is_practical") is False:
        fallback_reasons.append("fails practicality constraints")
    if candidate.get("score", 0) < 50:
        fallback_reasons.append("score below viability threshold (50)")
    return "; ".join(fallback_reasons) if fallback_reasons else "did not satisfy selection constraints"


def _candidate_elements(candidate: dict) -> set[str]:
    return {str(el).strip() for el in (candidate.get("elements", []) or []) if str(el).strip()}


def _query_safe_spec(spec: dict) -> dict:
    """Return a query-safe copy of spec for P1 retrieval compatibility.

    Some MP API query paths reject very long `exclude_elements` lists; keep the
    highest-priority exclusions for retrieval and leave full constraints in the
    original `spec` for downstream interpretation/scoring.
    """
    safe_spec = dict(spec)
    banned = list(spec.get("banned_elements", []) or [])
    if len(banned) <= 20:
        return safe_spec

    priority_order = [
        "Nd",
        "Dy",
        "Tb",
        "Pr",
        "Sm",
        "Gd",
        "Fe",
        "Co",
        "Ga",
        "Cr",
        "Pu",
        "U",
        "Th",
        "Am",
        "Np",
        "As",
        "Cd",
        "Hg",
        "Pb",
    ]
    prioritized = [element for element in priority_order if element in banned]
    remainder = [element for element in banned if element not in prioritized]
    safe_spec["banned_elements"] = (prioritized + remainder)[:20]
    return safe_spec


def _as_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def get_material_class(spec: dict) -> str:
    target_props = dict((spec or {}).get("target_props", {}) or {})
    return str(target_props.get("material_class", "unknown") or "unknown").strip().lower()


def _preserve_original_material_context(spec: dict, original_spec: dict | None) -> dict:
    """Prevent later generated hypotheses from drifting into a different material class."""
    if not original_spec:
        return spec
    original_class = get_material_class(original_spec)
    if original_class in {"", "unknown"}:
        return spec

    preserved = dict(spec or {})
    target_props = dict(preserved.get("target_props", {}) or {})
    parsed_class = str(target_props.get("material_class", "unknown") or "unknown").strip().lower()
    if parsed_class != original_class:
        preserved = dict(original_spec)
        preserved["context"] = (spec or {}).get("context", preserved.get("context", ""))
    return preserved


def candidate_tiebreak_value(candidate: dict, material_class: str) -> float:
    """
    Return a class-aware tie-break value.

    Score remains the primary signal. This value is only used when scores are
    tied or very close. Magnetic moment is only a tie-breaker for permanent
    magnets because it is not a universal performance target.
    """
    magnetic_moment = _as_float(candidate.get("magnetic_moment"), 0.0)
    band_gap = _as_float(candidate.get("band_gap"), 0.0)
    stability = 100.0 - min(100.0, _as_float(candidate.get("stability_above_hull"), 1.0) * 500.0)
    supply_safety = 100.0 - min(100.0, _as_float(candidate.get("supply_chain_risk"), 0.0))
    manufacturability = _as_float(candidate.get("manufacturability_score"), 0.0)
    evidence = _as_float(candidate.get("evidence_confidence_score"), 0.0)
    electrochemical_proxy = 100.0 - min(100.0, abs(_as_float(candidate.get("formation_energy"), 0.0)) * 100.0)

    if material_class == "permanent_magnet":
        return magnetic_moment
    if material_class == "semiconductor":
        band_gap_suitability = max(0.0, 100.0 - abs(band_gap - 1.1) * 35.0)
        return 0.75 * band_gap_suitability + 0.25 * stability
    if material_class == "protective_coating":
        return 0.55 * stability + 0.25 * manufacturability + 0.20 * evidence
    if material_class == "battery_material":
        return 0.60 * stability + 0.40 * electrochemical_proxy
    if material_class == "high_temperature_structural_material":
        return 0.75 * stability + 0.25 * manufacturability

    return 0.50 * stability + 0.30 * supply_safety + 0.20 * manufacturability


def sort_eligible_candidates(candidates: list[dict], spec: dict) -> list[dict]:
    if not candidates:
        return []
    material_class = get_material_class(spec)
    top_score = max(int(c.get("score", 0) or 0) for c in candidates)
    close_score_window = 2

    def sort_key(candidate: dict) -> tuple[int, float, float]:
        score = int(candidate.get("score", 0) or 0)
        # Keep score as primary. Use class-specific tie-break only for tied/close.
        tiebreak = (
            candidate_tiebreak_value(candidate, material_class)
            if (top_score - score) <= close_score_window
            else 0.0
        )
        stability = 100.0 - min(100.0, _as_float(candidate.get("stability_above_hull"), 1.0) * 500.0)
        return (score, tiebreak, stability)

    return sorted(candidates, key=sort_key, reverse=True)


def choose_final_winner(memory_or_result: dict, portfolio: list[dict], source_candidates: list[dict] | None = None) -> dict:
    if portfolio:
        top = dict(portfolio[0] or {})
        candidate_name = str(top.get("candidate", top.get("formula", "")) or "").strip()
        if candidate_name and not top.get("formula"):
            top["formula"] = candidate_name
        source_pool = list(source_candidates or [])
        current_best = dict((memory_or_result or {}).get("current_best", {}) or {})
        if current_best:
            source_pool.append(current_best)
        formula = str(top.get("formula", top.get("candidate", "")) or "").strip()
        for source in source_pool:
            if str(source.get("formula", "") or "").strip() == formula:
                merged = dict(source)
                merged.update({key: value for key, value in top.items() if value is not None})
                top = merged
                break
        scores = dict(top.get("scores", {}) or {})
        if "score" not in top and "overall" in scores:
            top["score"] = int(scores.get("overall", 0) or 0)
        if "supply_chain_risk" not in top:
            safety = top.get("supply_chain_score", scores.get("supply_chain_safety"))
            if safety is not None:
                top["supply_chain_risk"] = max(0, min(100, 100 - int(float(safety))))
        return top
    return dict((memory_or_result or {}).get("current_best", {}) or {})


def _load_p1_functions():
    """Load P1 modules lazily so mock mode works without mp-api installed."""
    from ..materials.search import get_candidates as p1_get_candidates
    from ..materials.scorer import score_candidate as p1_score_candidate

    return p1_get_candidates, p1_score_candidate


def _load_p2_functions():
    """Load available P2 functions lazily to avoid hard dependency failures."""
    from ..agents import agent as p2_agent

    parse_fn = getattr(p2_agent, "parse_hypothesis", None)
    interpret_fn = getattr(p2_agent, "interpret_results", None)
    generate_next_fn = getattr(p2_agent, "generate_next_hypothesis", None)
    synthesis_fn = getattr(p2_agent, "generate_synthesis_recommendation", None)
    portfolio_fn = getattr(p2_agent, "generate_lab_ready_portfolio", None)
    return parse_fn, interpret_fn, generate_next_fn, synthesis_fn, portfolio_fn


def _latest_portfolio(memory_dict: dict) -> dict:
    history = memory_dict.get("portfolio_history", []) or []
    if not isinstance(history, list) or not history:
        return {}
    return dict(history[-1] or {})


def run_agent(
    hypothesis: str,
    max_iterations: int = 5,
    use_real_p1: bool = True,
    use_real_p2: bool = True,
    allow_mock_fallback: bool = True,
) -> dict:
    """Run iterative search/scoring/reasoning loop."""
    memory = AgentMemory()
    current_hypothesis = hypothesis
    best_scores: list[int] = []
    scored_candidates: list[dict] = []
    convergence_score_threshold = 95
    min_iterations_before_stop = 2
    p2_synthesis_fn = None
    p2_portfolio_fn = None
    latest_spec: dict = {}
    original_spec: dict | None = None

    print_header(current_hypothesis)
    for iteration in range(1, max_iterations + 1):
        p2_parse_fn = mocks.parse_hypothesis
        p2_interpret_fn = mocks.interpret_results
        p2_next_fn = mocks.generate_next_hypothesis
        p2_portfolio_fn = getattr(mocks, "generate_lab_ready_portfolio", None)
        if use_real_p2:
            try:
                parse_fn, interpret_fn, next_fn, synth_fn, portfolio_fn = _load_p2_functions()
                if callable(parse_fn):
                    p2_parse_fn = parse_fn
                if callable(interpret_fn):
                    p2_interpret_fn = interpret_fn
                if callable(next_fn):
                    p2_next_fn = next_fn
                if callable(synth_fn):
                    p2_synthesis_fn = synth_fn
                if callable(portfolio_fn):
                    p2_portfolio_fn = portfolio_fn
                elif iteration == 1:
                    print_notice("1) P2 next-hypothesis missing; using mock fallback.", style="yellow")
            except Exception as exc:
                if not allow_mock_fallback:
                    raise RuntimeError(f"Real P2 import failed: {exc}") from exc
                if iteration == 1:
                    print_notice(f"1) Real P2 import failed ({exc}); using mock reasoning.", style="yellow")

        spec = p2_parse_fn(current_hypothesis)
        if original_spec is None:
            original_spec = dict(spec)
        else:
            spec = _preserve_original_material_context(spec, original_spec)
        latest_spec = dict(spec)
        retrieval_spec = _query_safe_spec(spec)
        memory.add_composition(current_hypothesis)
        print_status_line("1) Parsed hypothesis into structured spec.")

        p1_score_fn = mocks.score_candidate
        try:
            if use_real_p1:
                p1_get_candidates, p1_score_fn = _load_p1_functions()
                candidates = p1_get_candidates(
                    retrieval_spec.get("allowed_elements", []),
                    retrieval_spec.get("banned_elements", []),
                    retrieval_spec.get("target_props", {}),
                    limit=50,
                )
            else:
                candidates = mocks.get_candidates(
                    spec.get("allowed_elements", []),
                    spec.get("banned_elements", []),
                    spec.get("target_props", {}),
                    limit=50,
                )
        except Exception as exc:
            if not allow_mock_fallback:
                raise RuntimeError(f"Real P1 retrieval failed: {exc}") from exc
            print_notice(f"2) Real P1 retrieval failed ({exc}); falling back to mocks.", style="yellow")
            candidates = mocks.get_candidates(
                spec.get("allowed_elements", []),
                spec.get("banned_elements", []),
                spec.get("target_props", {}),
                limit=50,
            )
        print_iteration(iteration, max_iterations, len(candidates), int(memory.current_best.get("score", 0) or 0))

        scored_candidates: list[dict] = []
        for candidate in candidates:
            scored = dict(candidate)
            scored["score"] = p1_score_fn(scored, spec)
            scored_candidates.append(scored)

            if scored["score"] < 50:
                memory.add_rejection(
                    scored.get("formula", "unknown"),
                    _candidate_rejection_reason(scored),
                )

        eligible_candidates, ineligible_candidates = apply_hard_filters(scored_candidates, spec)
        for candidate in ineligible_candidates:
            memory.add_ineligible(
                candidate.get("formula", "unknown"),
                candidate.get("reason", "Hard filter constraint violation"),
            )
            memory.add_rejection(
                candidate.get("formula", "unknown"),
                candidate.get("reason", "Hard filter constraint violation"),
            )

        eligible_candidates = sort_eligible_candidates(eligible_candidates, spec)
        scored_candidates = list(eligible_candidates) + list(ineligible_candidates)
        memory.record_iteration(iteration, scored_candidates)

        selected_top = eligible_candidates[0] if eligible_candidates else (scored_candidates[0] if scored_candidates else {})
        if selected_top and _is_candidate_eligible(selected_top):
            current_best_score = int(memory.current_best.get("score", -1)) if memory.current_best else -1
            if int(selected_top.get("score", 0)) > current_best_score:
                memory.current_best = dict(selected_top)

        top_score = selected_top.get("score", 0) if selected_top else 0
        best_scores.append(top_score)
        print_status_line(f"3) Scored candidates. Best eligible score this round: {top_score}")
        if selected_top:
            material_class = get_material_class(spec)
            print_candidate(
                formula=str(selected_top.get("formula", "unknown")),
                score=int(selected_top.get("score", 0) or 0),
                magnetic_moment=selected_top.get("magnetic_moment"),
                supply_chain_risk=int(selected_top.get("supply_chain_risk", 0)) if selected_top.get("supply_chain_risk") is not None else None,
                status="ELIGIBLE" if _is_candidate_eligible(selected_top) else "INELIGIBLE",
                material_class=material_class,
                band_gap=selected_top.get("band_gap"),
                stability_above_hull=selected_top.get("stability_above_hull"),
                material_family=selected_top.get("material_family"),
            )

        try:
            interpretation = p2_interpret_fn(
                eligible_candidates[:5],
                spec,
                iteration,
                ineligible_candidates=ineligible_candidates,
            )
        except TypeError:
            interpretation = p2_interpret_fn(eligible_candidates[:5], spec, iteration)
        print_reasoning(interpretation, iteration)

        eligible_top = eligible_candidates[:5]
        iteration_portfolio = {}
        if callable(p2_portfolio_fn):
            iteration_portfolio = p2_portfolio_fn(eligible_top, spec, memory.to_dict()) or {}
            memory.portfolio_history.append(iteration_portfolio)
            memory.experiment_queue = list(iteration_portfolio.get("test_queue", []) or [])

        if iteration >= min_iterations_before_stop and top_score > convergence_score_threshold:
            print_notice(f"Converged: best score exceeded {convergence_score_threshold}.", style="green")
            break
        portfolio_entries = list(iteration_portfolio.get("portfolio", []) or [])
        has_test_first = any(str(entry.get("status", "")).upper() == "TEST_FIRST" for entry in portfolio_entries)
        backup_count = sum(
            1
            for entry in portfolio_entries
            if str(entry.get("status", "")).upper() in {"BACKUP_TEST", "SAFE_FALLBACK"}
        )
        if has_test_first and backup_count >= 2:
            print_notice("Converged: portfolio has TEST_FIRST plus two viable backups.", style="green")
            break
        if iteration >= min_iterations_before_stop and _has_converged(best_scores):
            print_notice("Converged: score did not improve for two iterations.", style="green")
            break

        next_memory = memory.to_dict()
        next_memory["original_spec"] = dict(original_spec or latest_spec)
        next_memory["original_material_class"] = get_material_class(original_spec or latest_spec)
        next_memory["original_hypothesis"] = hypothesis
        current_hypothesis = p2_next_fn(next_memory)
        print_status_line(f"5) Next hypothesis: {current_hypothesis}")

    final_memory = memory.to_dict()
    latest_portfolio = _latest_portfolio(final_memory)
    portfolio_entries = list(latest_portfolio.get("portfolio", []))
    best_candidate = choose_final_winner(final_memory, portfolio_entries, scored_candidates)

    if best_candidate and not _is_candidate_eligible(best_candidate):
        eligible_sorted = [candidate for candidate in scored_candidates if _is_candidate_eligible(candidate)]
        if eligible_sorted:
            best_candidate = dict(eligible_sorted[0])

    if best_candidate:
        synthesis = None
        if callable(p2_synthesis_fn):
            synthesis = p2_synthesis_fn(best_candidate)
        if not synthesis:
            synthesis = (
                "Synthesize via solid-state or melt processing followed by controlled annealing "
                "to stabilize the target phase; validate experimentally."
            )
        best_candidate["synthesis_recommendation"] = synthesis
        print_final_result(best_candidate, latest_spec)

    ineligible_entries = list(final_memory.get("ineligible_candidates", []))
    test_queue = list(final_memory.get("experiment_queue", []))
    target_props = dict((latest_spec or {}).get("target_props", {}) or {})
    constraints_payload = {
        "banned_elements": list((latest_spec or {}).get("banned_elements", [])),
        "material_class": str(target_props.get("material_class", "unknown")),
        "exclude_radioactive": bool(target_props.get("exclude_radioactive", True)),
        "require_solid_state": bool(target_props.get("require_solid_state", True)),
    }

    final_result = {
        "mission": hypothesis,
        "constraints": dict(latest_spec),
        "portfolio": portfolio_entries,
        "ineligible": ineligible_entries,
        "test_queue": test_queue,
        "provenance_tree": {
            "mission": hypothesis,
            "constraints": constraints_payload,
            "candidate_search": {
                "iterations_run": len(best_scores),
                "ineligible": [
                    {"formula": row.get("formula", "unknown"), "reason": row.get("reason", "")}
                    for row in ineligible_entries
                ],
                "portfolio": [
                    {
                        "rank": row.get("rank", idx + 1),
                        "candidate": row.get("candidate", row.get("formula", "unknown")),
                        "status": row.get("status", ""),
                    }
                    for idx, row in enumerate(portfolio_entries)
                ],
            },
            "test_queue": test_queue,
        },
        "best_candidate": best_candidate,
    }

    print_ineligible_panel(final_result.get("ineligible", []))
    print_portfolio_table(final_result.get("portfolio", []))
    print_uncertainty_map(final_result.get("portfolio", []))
    print_experiment_tree(final_result)
    print_test_queue(final_result.get("test_queue", []))
    return final_result
