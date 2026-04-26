"""FastAPI SSE server for the CriticalMat agent."""

from __future__ import annotations

import json
import queue
import threading
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .core import mocks
from .core.loop import _has_converged, _load_p1_functions
from .core.memory import AgentMemory

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SENTINEL = object()
STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


class RunRequest(BaseModel):
    hypothesis: str


def _sse_event(name: str, payload: dict[str, Any]) -> str:
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n"


def _to_camel(value: Any) -> Any:
    if isinstance(value, list):
        return [_to_camel(item) for item in value]
    if isinstance(value, dict):
        return {_camel_key(str(key)): _to_camel(item) for key, item in value.items()}
    return value


def _camel_key(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def _formula_plain(formula: str | None) -> str | None:
    if formula is None:
        return None
    subscript_digits = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
    return formula.translate(subscript_digits)


def _candidate_to_frontend(candidate: dict[str, Any]) -> dict[str, Any]:
    normalized = _to_camel(candidate)
    formula = normalized.get("formula")
    if formula:
        normalized.setdefault("formulaPlain", _formula_plain(formula))
        normalized.setdefault("fullName", formula)
    if "supplyChainRisk" in normalized:
        risk = normalized["supplyChainRisk"]
        normalized.setdefault("supplyChainScore", max(0, 100 - int(risk or 0)))
    return normalized


def _decision_entry(
    iteration: int,
    candidate: dict[str, Any],
    selected_formula: str | None = None,
) -> dict[str, Any]:
    formula = str(candidate.get("formula", "unknown"))
    score = int(candidate.get("score", 0))
    selected = selected_formula is not None and formula == selected_formula
    return {
        "iteration": iteration,
        "formula": formula,
        "score": score,
        "decision": "selected" if selected else "rejected",
        "reason": (
            "Highest-scoring candidate selected after agent convergence."
            if selected
            else "Score below current best or viability threshold."
        ),
    }


def _parse_iteration_from_interpretation(text: str) -> tuple[str | None, str | None]:
    interpretation = text
    next_hypothesis = None
    marker = "Next hypothesis:"
    if marker in text:
        interpretation, next_hypothesis = text.split(marker, 1)
        interpretation = interpretation.strip()
        next_hypothesis = next_hypothesis.strip() or None
    return interpretation, next_hypothesis


def _get_p2_functions():
    try:
        from .agents import agent as p2_agent

        parse_fn = getattr(p2_agent, "parse_hypothesis", None) or mocks.parse_hypothesis
        interpret_fn = getattr(p2_agent, "interpret_results", None) or mocks.interpret_results
        next_fn = (
            getattr(p2_agent, "generate_next_hypothesis", None)
            or mocks.generate_next_hypothesis
        )
    except Exception:
        parse_fn = mocks.parse_hypothesis
        interpret_fn = mocks.interpret_results
        next_fn = mocks.generate_next_hypothesis
    return parse_fn, interpret_fn, next_fn


def _run_agent_streaming(hypothesis: str, event_queue: queue.Queue) -> None:
    memory = AgentMemory()
    current_hypothesis = hypothesis
    best_scores: list[int] = []
    decision_log: list[dict[str, Any]] = []
    final_candidate: dict[str, Any] = {}

    try:
        parse_fn, interpret_fn, next_fn = _get_p2_functions()

        for iteration in range(1, 6):
            spec = parse_fn(current_hypothesis)
            memory.add_composition(current_hypothesis)

            try:
                p1_get_candidates, p1_score_fn = _load_p1_functions()
                candidates = p1_get_candidates(
                    spec.get("allowed_elements", []),
                    spec.get("banned_elements", []),
                    spec.get("target_props", {}),
                    limit=50,
                )
            except Exception:
                p1_score_fn = mocks.score_candidate
                candidates = mocks.get_candidates(
                    spec.get("allowed_elements", []),
                    spec.get("banned_elements", []),
                    spec.get("target_props", {}),
                    limit=50,
                )

            scored_candidates: list[dict[str, Any]] = []
            for candidate in candidates:
                scored = dict(candidate)
                scored["score"] = p1_score_fn(scored, spec)
                scored_candidates.append(scored)
                if scored["score"] < 50:
                    memory.add_rejection(
                        scored.get("formula", "unknown"),
                        "Score below viability threshold (50).",
                    )

            scored_candidates.sort(key=lambda item: item.get("score", 0), reverse=True)
            memory.record_iteration(iteration, scored_candidates)

            best = scored_candidates[0] if scored_candidates else {}
            top_score = int(best.get("score", 0))
            best_scores.append(top_score)
            final_candidate = dict(memory.current_best or best)

            interpretation_text = interpret_fn(scored_candidates[:5], spec, iteration)
            interpretation, parsed_next = _parse_iteration_from_interpretation(
                str(interpretation_text)
            )

            converged = top_score > 80 or _has_converged(best_scores)
            next_hypothesis = None
            if not converged:
                next_hypothesis = parsed_next or next_fn(memory.to_dict())
                current_hypothesis = next_hypothesis

            for candidate in scored_candidates:
                decision_log.append(_decision_entry(iteration, candidate))

            event_queue.put(
                (
                    "iteration",
                    {
                        "num": iteration,
                        "candidatesTested": len(scored_candidates),
                        "bestFormula": best.get("formula"),
                        "bestFormulaPlain": _formula_plain(best.get("formula")),
                        "score": top_score,
                        "interpretation": interpretation,
                        "nextHypothesis": next_hypothesis,
                        "status": "converged" if converged else "continue",
                    },
                )
            )

            if converged:
                break

        selected_formula = final_candidate.get("formula")
        decision_log = [
            _decision_entry(entry["iteration"], entry, selected_formula)
            for entry in decision_log
        ]
        event_queue.put(
            (
                "complete",
                {
                    "finalCandidate": _candidate_to_frontend(final_candidate),
                    "decisionLog": decision_log,
                },
            )
        )
    except Exception as exc:
        event_queue.put(("error", {"message": str(exc)}))
    finally:
        event_queue.put(SENTINEL)


def _load_demo_cache() -> dict[str, Any]:
    demo_path = Path(__file__).resolve().parent / "materials" / "demo_cache.json"
    return json.loads(demo_path.read_text(encoding="utf-8"))


def _demo_iterations(cache: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(cache.get("iterations"), list):
        return [_to_camel(iteration) for iteration in cache["iterations"]]

    top_candidates = cache.get("top_candidates", [])
    best = top_candidates[0] if top_candidates else {}
    return [
        {
            "num": 1,
            "candidatesTested": int(cache.get("candidate_count", len(top_candidates))),
            "bestFormula": best.get("formula"),
            "bestFormulaPlain": _formula_plain(best.get("formula")),
            "score": int(best.get("score", 0)),
            "interpretation": "Demo cache replayed successfully.",
            "nextHypothesis": None,
            "status": "converged",
        }
    ]


def _demo_decision_log(cache: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = cache.get("top_candidates", [])
    selected_formula = candidates[0].get("formula") if candidates else None
    return [
        _decision_entry(1, candidate, selected_formula)
        for candidate in candidates
    ]


def _demo_final_candidate(cache: dict[str, Any]) -> dict[str, Any]:
    candidates = cache.get("top_candidates", [])
    return _candidate_to_frontend(candidates[0] if candidates else {})


def _stream_demo() -> Any:
    try:
        cache = _load_demo_cache()
        iterations = _demo_iterations(cache)
        for iteration in iterations:
            yield _sse_event("iteration", iteration)
            time.sleep(1)
        yield _sse_event(
            "complete",
            {
                "finalCandidate": _demo_final_candidate(cache),
                "decisionLog": _demo_decision_log(cache),
            },
        )
    except Exception as exc:
        yield _sse_event("error", {"message": str(exc)})


def _stream_agent(hypothesis: str) -> Any:
    event_queue: queue.Queue = queue.Queue()
    thread = threading.Thread(
        target=_run_agent_streaming,
        args=(hypothesis, event_queue),
        daemon=True,
    )
    thread.start()

    try:
        while True:
            item = event_queue.get()
            if item is SENTINEL:
                break
            name, payload = item
            yield _sse_event(name, payload)
    except Exception as exc:
        yield _sse_event("error", {"message": str(exc)})


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "agent": "ready"}


@app.post("/run")
@app.post("/api/run")
def run(request: RunRequest, fast: bool = Query(default=False)) -> StreamingResponse:
    stream = _stream_demo() if fast else _stream_agent(request.hypothesis)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )
