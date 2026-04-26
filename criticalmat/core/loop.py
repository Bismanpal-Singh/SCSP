"""LangGraph-based autonomous loop for CriticalMat.

This module keeps the same `run_agent(...)` API while switching orchestration
to a graph state machine for clearer agentic control flow and observability.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .memory import AgentMemory
from . import mocks

SCORE_CONVERGENCE_THRESHOLD = 92
REPEAT_FAMILY_PENALTY = 8
MIN_ITERATIONS_BEFORE_STOP = 2


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


class AgentState(TypedDict, total=False):
    hypothesis: str
    current_hypothesis: str
    iteration: int
    max_iterations: int
    use_real_p1: bool
    use_real_p2: bool
    allow_mock_fallback: bool
    memory: AgentMemory
    best_scores: list[int]
    spec: dict
    candidates: list[dict]
    scored_candidates: list[dict]
    top_score: int
    top_raw_score: int
    top_family: str
    family_win_counts: dict[str, int]
    interpretation: str
    next_hypothesis: str
    stop: bool
    stop_reason: str


def _node_parse(state: AgentState) -> AgentState:
    p2_parse_fn = mocks.parse_hypothesis
    if state.get("use_real_p2", True):
        try:
            parse_fn, _, _ = _load_p2_functions()
            if callable(parse_fn):
                p2_parse_fn = parse_fn
        except Exception as exc:
            if not state.get("allow_mock_fallback", True):
                raise RuntimeError(f"Real P2 parse import failed: {exc}") from exc
            if state.get("iteration", 1) == 1:
                print(f"1) Real P2 parse import failed ({exc}); using mock parser.")

    current_hypothesis = state.get("current_hypothesis", state.get("hypothesis", ""))
    spec = p2_parse_fn(current_hypothesis)
    memory = state["memory"]
    memory.add_composition(current_hypothesis)
    print("1) Parsed hypothesis into structured spec.")
    return {"spec": spec}


def _node_search(state: AgentState) -> AgentState:
    spec = state.get("spec", {})
    p1_score_fn = mocks.score_candidate
    try:
        if state.get("use_real_p1", True):
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
        if not state.get("allow_mock_fallback", True):
            raise RuntimeError(f"Real P1 retrieval failed: {exc}") from exc
        print(f"2) Real P1 retrieval failed ({exc}); falling back to mocks.")
        candidates = mocks.get_candidates(
            spec.get("allowed_elements", []),
            spec.get("banned_elements", []),
            spec.get("target_props", {}),
            limit=50,
        )
    print(f"2) Retrieved {len(candidates)} candidates.")
    return {"candidates": candidates, "_p1_score_fn": p1_score_fn}  # type: ignore[typeddict-item]


def _node_score(state: AgentState) -> AgentState:
    spec = state.get("spec", {})
    candidates = state.get("candidates", [])
    memory = state["memory"]
    p1_score_fn = state.get("_p1_score_fn", mocks.score_candidate)  # type: ignore[assignment]

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
    iteration = state.get("iteration", 1)
    practical_candidates = [c for c in scored_candidates if c.get("is_practical", True)]
    practical_candidates.sort(key=lambda c: c.get("score", 0), reverse=True)

    # Record all scored rows for history, but only practical candidates may become "best".
    memory.record_iteration(iteration, scored_candidates)
    if practical_candidates:
        memory.current_best = dict(practical_candidates[0])

    family_win_counts = dict(state.get("family_win_counts", {}))
    top_raw_score = practical_candidates[0]["score"] if practical_candidates else 0
    top_family = str(practical_candidates[0].get("family_tag", "unknown")) if practical_candidates else "none"
    repeat_count = family_win_counts.get(top_family, 0) if practical_candidates else 0
    top_score = max(0, top_raw_score - (REPEAT_FAMILY_PENALTY * repeat_count))
    if practical_candidates:
        family_win_counts[top_family] = repeat_count + 1

    best_scores = list(state.get("best_scores", []))
    best_scores.append(top_score)
    print(
        "3) Scored candidates. "
        f"Best practical score this round: {top_score} "
        f"(raw={top_raw_score}, family={top_family}, repeat_penalty={REPEAT_FAMILY_PENALTY * repeat_count}) "
        f"(practical_count={len(practical_candidates)}/{len(scored_candidates)})"
    )
    return {
        "scored_candidates": scored_candidates,
        "top_score": top_score,
        "top_raw_score": top_raw_score,
        "top_family": top_family,
        "family_win_counts": family_win_counts,
        "best_scores": best_scores,
    }


def _node_interpret(state: AgentState) -> AgentState:
    p2_interpret_fn = mocks.interpret_results
    if state.get("use_real_p2", True):
        try:
            _, interpret_fn, _ = _load_p2_functions()
            if callable(interpret_fn):
                p2_interpret_fn = interpret_fn
        except Exception as exc:
            if not state.get("allow_mock_fallback", True):
                raise RuntimeError(f"Real P2 interpret import failed: {exc}") from exc
            if state.get("iteration", 1) == 1:
                print(f"4) Real P2 interpret import failed ({exc}); using mock interpreter.")

    interpretation = p2_interpret_fn(
        state.get("scored_candidates", [])[:5],
        state.get("spec", {}),
        state.get("iteration", 1),
    )
    print(f"4) Interpretation: {interpretation}")
    return {"interpretation": interpretation}


def _node_decide(state: AgentState) -> AgentState:
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 5)
    top_score = state.get("top_score", 0)
    best_scores = state.get("best_scores", [])

    if iteration >= MIN_ITERATIONS_BEFORE_STOP:
        if top_score > SCORE_CONVERGENCE_THRESHOLD:
            print(f"Converged: best score exceeded {SCORE_CONVERGENCE_THRESHOLD}.")
            return {"stop": True, "stop_reason": "score_threshold"}
        if _has_converged(best_scores):
            print("Converged: score did not improve for two iterations.")
            return {"stop": True, "stop_reason": "no_improvement"}
    if iteration >= max_iterations:
        return {"stop": True, "stop_reason": "max_iterations"}
    return {"stop": False}


def _node_next_hypothesis(state: AgentState) -> AgentState:
    p2_next_fn = mocks.generate_next_hypothesis
    if state.get("use_real_p2", True):
        try:
            _, _, next_fn = _load_p2_functions()
            if callable(next_fn):
                p2_next_fn = next_fn
            elif state.get("iteration", 1) == 1:
                print("5) P2 next-hypothesis missing; using mock fallback.")
        except Exception as exc:
            if not state.get("allow_mock_fallback", True):
                raise RuntimeError(f"Real P2 next-hypothesis import failed: {exc}") from exc
            if state.get("iteration", 1) == 1:
                print(f"5) Real P2 next-hypothesis import failed ({exc}); using mock fallback.")

    next_hypothesis = p2_next_fn(state["memory"].to_dict())
    print(f"5) Next hypothesis: {next_hypothesis}")
    return {
        "next_hypothesis": next_hypothesis,
        "current_hypothesis": next_hypothesis,
        "iteration": state.get("iteration", 1) + 1,
    }


def _route_after_decide(state: AgentState) -> str:
    if state.get("stop", False):
        return "end"
    return "next"


def _build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("parse", _node_parse)
    graph.add_node("search", _node_search)
    graph.add_node("score", _node_score)
    graph.add_node("interpret", _node_interpret)
    graph.add_node("decide", _node_decide)
    graph.add_node("next", _node_next_hypothesis)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "search")
    graph.add_edge("search", "score")
    graph.add_edge("score", "interpret")
    graph.add_edge("interpret", "decide")
    graph.add_conditional_edges("decide", _route_after_decide, {"next": "next", "end": END})
    graph.add_edge("next", "parse")
    return graph.compile()


def run_agent(
    hypothesis: str,
    max_iterations: int = 5,
    use_real_p1: bool = True,
    use_real_p2: bool = True,
    allow_mock_fallback: bool = True,
) -> dict:
    """Run agentic workflow via LangGraph state transitions."""
    memory = AgentMemory()
    initial_state: AgentState = {
        "hypothesis": hypothesis,
        "current_hypothesis": hypothesis,
        "iteration": 1,
        "max_iterations": max_iterations,
        "use_real_p1": use_real_p1,
        "use_real_p2": use_real_p2,
        "allow_mock_fallback": allow_mock_fallback,
        "memory": memory,
        "best_scores": [],
        "family_win_counts": {},
        "stop": False,
    }

    print(f"Input hypothesis: {hypothesis}")
    graph = _build_graph()
    final_state: AgentState = graph.invoke(initial_state)

    final_memory = final_state["memory"].to_dict()
    return {
        "final_hypothesis": final_state.get("current_hypothesis", hypothesis),
        "best_candidate": final_memory.get("current_best", {}),
        "memory": final_memory,
        "stop_reason": final_state.get("stop_reason", "max_iterations"),
    }
