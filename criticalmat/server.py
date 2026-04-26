"""FastAPI SSE server for the CriticalMat agent."""

from __future__ import annotations

import json
import queue
import threading
import time
import io
import contextlib
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


def clean_terminal_output(text: str) -> str:
    """Strip terminal formatting noise for web rendering."""
    if not text:
        return ""

    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    text = re.sub(r"[═║╔╗╚╝│┃─━┌┐└┘┤├┬┴┼╠╣╦╩╬]", "", text)
    text = re.sub(r"^[=\-_]{3,}.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()


def _clean_text_fields(value: Any) -> Any:
    if isinstance(value, str):
        return clean_terminal_output(value)
    if isinstance(value, list):
        return [_clean_text_fields(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_text_fields(item) for key, item in value.items()}
    return value


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
    try:
        transcript_buffer = io.StringIO()
        with contextlib.redirect_stdout(transcript_buffer):
            result = run_agent(
                hypothesis,
                max_iterations=5,
                use_real_p1=True,
                use_real_p2=True,
                allow_mock_fallback=True,
            )
        terminal_transcript = transcript_buffer.getvalue()
        final_candidate = dict(result.get("best_candidate", {}) or {})
        provenance_tree = dict(result.get("provenance_tree", {}) or {})
        candidate_search = dict(provenance_tree.get("candidate_search", {}) or {})
        portfolio = list(result.get("portfolio", []) or [])
        ineligible = list(result.get("ineligible", []) or [])
        test_queue = list(result.get("test_queue", []) or [])
        constraints = dict(result.get("constraints", {}) or {})

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
                    "interpretation": clean_terminal_output("Structured 2.0 portfolio generated from full agent loop."),
                    "reasoning": clean_terminal_output("Portfolio and constraint analysis complete."),
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
                    "decisionLog": _clean_text_fields({
                        "mission": result.get("mission", hypothesis),
                        "constraints": constraints,
                        "portfolio": portfolio,
                        "ineligible": ineligible,
                        "test_queue": test_queue,
                        "provenance_tree": provenance_tree,
                    }),
                    "terminalTranscript": clean_terminal_output(terminal_transcript),
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
