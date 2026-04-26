"""FastAPI SSE server for the CriticalMat agent."""

from __future__ import annotations

import json
import queue
import threading
import io
import contextlib
import os
import re
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .core import mocks
from .core.loop import _has_converged, _load_p1_functions
from .core.memory import AgentMemory
from .core.loop import run_agent

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
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


class RunRequest(BaseModel):
    hypothesis: str


def _sse_event(name: str, payload: dict[str, Any]) -> str:
    return f"event: {name}\ndata: {json.dumps(payload)}\n\n"


def _max_transcript_chars() -> int:
    try:
        return max(0, int(os.getenv("CRITICALMAT_SSE_MAX_TRANSCRIPT_CHARS", "12000")))
    except (TypeError, ValueError):
        return 12000


def _compact_transcript(text: str) -> str:
    clean = ANSI_ESCAPE_RE.sub("", text or "")
    max_chars = _max_transcript_chars()
    if max_chars <= 0 or len(clean) <= max_chars:
        return clean
    head = int(max_chars * 0.7)
    tail = max_chars - head
    return (
        clean[:head].rstrip()
        + "\n\n... [transcript truncated for UI performance] ...\n\n"
        + clean[-tail:].lstrip()
    )


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
        formula_text = str(formula).strip().lower()
        if formula_text in {"no candidate selected", "none", "n/a"}:
            fallback_name = (
                normalized.get("rationale")
                or normalized.get("mainUncertainty")
                or "No class-relevant high-confidence candidate met current constraints."
            )
            normalized["fullName"] = str(fallback_name)
        else:
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
    try:
        def _emit_progress(payload: dict[str, Any]) -> None:
            event_type = str(payload.get("type", "iteration"))
            outbound = dict(payload)
            outbound.pop("type", None)
            event_queue.put((event_type, outbound))

        transcript_buffer = io.StringIO()
        with contextlib.redirect_stdout(transcript_buffer):
            result = run_agent(
                hypothesis,
                max_iterations=5,
                use_real_p1=True,
                use_real_p2=True,
                allow_mock_fallback=True,
                event_callback=_emit_progress,
            )
        terminal_transcript = _compact_transcript(transcript_buffer.getvalue())
        final_candidate = dict(result.get("best_candidate", {}) or {})
        provenance_tree = dict(result.get("provenance_tree", {}) or {})
        candidate_search = dict(provenance_tree.get("candidate_search", {}) or {})
        portfolio = list(result.get("portfolio", []) or [])
        ineligible = list(result.get("ineligible", []) or [])
        test_queue = list(result.get("test_queue", []) or [])
        constraints = dict(result.get("constraints", {}) or {})
        agent_trace = list(result.get("agent_trace", []) or [])

        event_queue.put(
            (
                "iteration",
                {
                    "num": int(candidate_search.get("iterations_run", 1) or 1),
                    "candidatesTested": max(1, len(portfolio) + len(ineligible)),
                    "bestFormula": final_candidate.get("formula"),
                    "bestFormulaPlain": _formula_plain(final_candidate.get("formula")),
                    "score": int(final_candidate.get("score", 0) or 0),
                    "bestCandidate": _candidate_to_frontend(final_candidate),
                    "interpretation": "Structured 2.0 portfolio generated from full agent loop.",
                    "nextHypothesis": None,
                    "status": "converged",
                },
            )
        )

        event_queue.put(
            (
                "complete",
                {
                    "finalCandidate": _candidate_to_frontend(final_candidate),
                    "decisionLog": {
                        "mission": result.get("mission", hypothesis),
                        "constraints": constraints,
                        "portfolio": portfolio,
                        "ineligible": ineligible,
                        "test_queue": test_queue,
                        "agent_trace": agent_trace,
                        "provenance_tree": provenance_tree,
                    },
                    "terminalTranscript": terminal_transcript,
                },
            )
        )
    except Exception as exc:
        event_queue.put(("error", {"message": str(exc)}))
    finally:
        event_queue.put(SENTINEL)


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
def run(request: RunRequest) -> StreamingResponse:
    stream = _stream_agent(request.hypothesis)
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )
