"""Main autonomous loop for CriticalMat.

Hour 3+ integration status:
- P1 (`materials/search.py`, `materials/scorer.py`) is wired and enabled by default.
- P2 (`agents/agent.py`) parse, interpretation, and next-hypothesis are wired when available.
- Safe fallbacks keep loop runnable if API keys/dependencies are unavailable.
"""

from __future__ import annotations

from .memory import AgentMemory
from . import mocks


def _has_converged(best_scores: list[int]) -> bool:
    """Converge if score has not improved in two iterations."""
    if len(best_scores) < 3:
        return False
    return best_scores[-1] <= best_scores[-2] <= best_scores[-3]


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
    return parse_fn, interpret_fn, generate_next_fn


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

    print(f"Input hypothesis: {current_hypothesis}")
    for iteration in range(1, max_iterations + 1):
        print(f"\n=== Iteration {iteration}/{max_iterations} ===")

        p2_parse_fn = mocks.parse_hypothesis
        p2_interpret_fn = mocks.interpret_results
        p2_next_fn = mocks.generate_next_hypothesis
        if use_real_p2:
            try:
                parse_fn, interpret_fn, next_fn = _load_p2_functions()
                if callable(parse_fn):
                    p2_parse_fn = parse_fn
                if callable(interpret_fn):
                    p2_interpret_fn = interpret_fn
                if callable(next_fn):
                    p2_next_fn = next_fn
                elif iteration == 1:
                    print("1) P2 next-hypothesis missing; using mock fallback.")
            except Exception as exc:
                if not allow_mock_fallback:
                    raise RuntimeError(f"Real P2 import failed: {exc}") from exc
                if iteration == 1:
                    print(f"1) Real P2 import failed ({exc}); using mock reasoning.")

        spec = p2_parse_fn(current_hypothesis)
        memory.add_composition(current_hypothesis)
        print("1) Parsed hypothesis into structured spec.")

        p1_score_fn = mocks.score_candidate
        try:
            if use_real_p1:
                p1_get_candidates, p1_score_fn = _load_p1_functions()
                candidates = p1_get_candidates(
                    spec.get("allowed_elements", []),
                    spec.get("banned_elements", []),
                    spec.get("target_props", {}),
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
            print(f"2) Real P1 retrieval failed ({exc}); falling back to mocks.")
            candidates = mocks.get_candidates(
                spec.get("allowed_elements", []),
                spec.get("banned_elements", []),
                spec.get("target_props", {}),
                limit=50,
            )
        print(f"2) Retrieved {len(candidates)} candidates.")

        scored_candidates: list[dict] = []
        for candidate in candidates:
            scored = dict(candidate)
            scored["score"] = p1_score_fn(scored, spec)
            scored_candidates.append(scored)
            if scored["score"] < 50:
                memory.add_rejection(
                    scored.get("formula", "unknown"),
                    "Score below viability threshold (50).",
                )

        scored_candidates.sort(key=lambda c: c.get("score", 0), reverse=True)
        memory.record_iteration(iteration, scored_candidates)

        top_score = scored_candidates[0]["score"] if scored_candidates else 0
        best_scores.append(top_score)
        print(f"3) Scored candidates. Best score this round: {top_score}")

        interpretation = p2_interpret_fn(scored_candidates[:5], spec, iteration)
        print(f"4) Interpretation: {interpretation}")

        if top_score > 80:
            print("Converged: best score exceeded 80.")
            break
        if _has_converged(best_scores):
            print("Converged: score did not improve for two iterations.")
            break

        current_hypothesis = p2_next_fn(memory.to_dict())
        print(f"5) Next hypothesis: {current_hypothesis}")

    final_memory = memory.to_dict()
    return {
        "final_hypothesis": current_hypothesis,
        "best_candidate": final_memory.get("current_best", {}),
        "memory": final_memory,
    }
