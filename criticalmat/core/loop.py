"""Main autonomous loop for CriticalMat.

Hour 3+ integration status:
- P1 (`materials/search.py`, `materials/scorer.py`) is wired and enabled by default.
- P2 (`agents/agent.py`) parse, interpretation, and next-hypothesis are wired when available.
- Safe fallbacks keep loop runnable if API keys/dependencies are unavailable.
"""

from __future__ import annotations

import json

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
        "Co",
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


def _load_fast_candidates(cache_path: str, cache_key: str = "magnet-defense") -> list[dict]:
    with open(cache_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, dict):
        bucket = payload.get(cache_key, {})
        if isinstance(bucket, dict):
            candidates = bucket.get("candidates", [])
            if isinstance(candidates, list):
                return [item for item in candidates if isinstance(item, dict)]
        candidates = payload.get("candidates")
        if isinstance(candidates, list):
            return [item for item in candidates if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


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
    fast_mode: bool = False,
    demo_cache_path: str = "criticalmat/materials/demo_cache.json",
    cache_key: str = "magnet-defense",
) -> dict:
    """Run iterative search/scoring/reasoning loop."""
    memory = AgentMemory()
    current_hypothesis = hypothesis
    best_scores: list[int] = []
    scored_candidates: list[dict] = []
    convergence_score_threshold = 95
    min_iterations_before_stop = 2
    fast_candidates = _load_fast_candidates(demo_cache_path, cache_key=cache_key) if fast_mode else []
    p2_synthesis_fn = None
    p2_portfolio_fn = None
    latest_spec: dict = {}

    print_header(current_hypothesis)
    if fast_mode:
        print_notice("[FAST MODE] Using demo_cache.json candidates (no live MP API call).", style="yellow")
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
        latest_spec = dict(spec)
        retrieval_spec = _query_safe_spec(spec)
        memory.add_composition(current_hypothesis)
        print_status_line("1) Parsed hypothesis into structured spec.")

        p1_score_fn = mocks.score_candidate
        try:
            if fast_mode:
                candidates = list(fast_candidates)
            elif use_real_p1:
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

        eligible_candidates.sort(
            key=lambda c: (
                c.get("score", 0),
                c.get("magnetic_moment", 0.0),
                -float(c.get("stability_above_hull", 1.0) or 1.0),
            ),
            reverse=True,
        )
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
            print_candidate(
                formula=str(selected_top.get("formula", "unknown")),
                score=int(selected_top.get("score", 0) or 0),
                magnetic_moment=float(selected_top.get("magnetic_moment", 0.0) or 0.0),
                supply_chain_risk=int(selected_top.get("supply_chain_risk", 0) or 0),
                status="ELIGIBLE" if _is_candidate_eligible(selected_top) else "INELIGIBLE",
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

        current_hypothesis = p2_next_fn(memory.to_dict())
        print_status_line(f"5) Next hypothesis: {current_hypothesis}")

    final_memory = memory.to_dict()
    best_candidate = final_memory.get("current_best", {})
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
        print_final_result(best_candidate)

    latest_portfolio = _latest_portfolio(final_memory)
    portfolio_entries = list(latest_portfolio.get("portfolio", []))
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
