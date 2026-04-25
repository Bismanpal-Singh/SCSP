"""Main autonomous loop for CriticalMat.

During Hours 0-3 this module intentionally imports mock implementations.
Swap these imports to `search.py` and `agent.py` teammate functions later.
"""

from __future__ import annotations

from .memory import AgentMemory
from .mocks import (
    generate_next_hypothesis,
    get_candidates,
    interpret_results,
    parse_hypothesis,
    score_candidate,
)


def _has_converged(best_scores: list[int]) -> bool:
    """Converge if score has not improved in two iterations."""
    if len(best_scores) < 3:
        return False
    return best_scores[-1] <= best_scores[-2] <= best_scores[-3]


def run_agent(hypothesis: str, max_iterations: int = 5) -> dict:
    """Run iterative search/scoring/reasoning loop."""
    memory = AgentMemory()
    current_hypothesis = hypothesis
    best_scores: list[int] = []

    print(f"Input hypothesis: {current_hypothesis}")
    for iteration in range(1, max_iterations + 1):
        print(f"\n=== Iteration {iteration}/{max_iterations} ===")

        spec = parse_hypothesis(current_hypothesis)
        memory.add_composition(current_hypothesis)
        print("1) Parsed hypothesis into structured spec.")

        candidates = get_candidates(
            spec.get("allowed_elements", []),
            spec.get("banned_elements", []),
            spec.get("target_props", {}),
            limit=50,
        )
        print(f"2) Retrieved {len(candidates)} candidates.")

        scored_candidates: list[dict] = []
        for candidate in candidates:
            scored = dict(candidate)
            scored["score"] = score_candidate(scored, spec)
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

        interpretation = interpret_results(scored_candidates[:5], spec, iteration)
        print(f"4) Interpretation: {interpretation}")

        if top_score > 80:
            print("Converged: best score exceeded 80.")
            break
        if _has_converged(best_scores):
            print("Converged: score did not improve for two iterations.")
            break

        current_hypothesis = generate_next_hypothesis(memory.to_dict())
        print(f"5) Next hypothesis: {current_hypothesis}")

    final_memory = memory.to_dict()
    return {
        "final_hypothesis": current_hypothesis,
        "best_candidate": final_memory.get("current_best", {}),
        "memory": final_memory,
    }
