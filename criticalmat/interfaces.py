"""Shared function contracts for CriticalMat teammates.

Do not change signatures without notifying the full team.
"""

from __future__ import annotations


def get_candidates(
    allowed_elements: list[str],
    banned_elements: list[str],
    target_props: dict,
    limit: int = 50,
) -> list[dict]:
    """Return candidate materials from the materials database."""
    raise NotImplementedError


def score_candidate(candidate: dict, spec: dict) -> int:
    """Return candidate score from 0 to 100."""
    raise NotImplementedError


def parse_hypothesis(text: str) -> dict:
    """Parse a user hypothesis into a structured specification dict."""
    raise NotImplementedError


def interpret_results(
    candidates: list[dict],
    spec: dict,
    iteration: int,
    ineligible_candidates: list[dict] | None = None,
) -> str:
    """Return a readable summary of current iteration results."""
    raise NotImplementedError


def generate_next_hypothesis(memory: dict) -> str:
    """Generate a plain-English next hypothesis from loop memory."""
    raise NotImplementedError


def generate_lab_ready_potential(candidate: dict) -> dict:
    """Return lab-readiness potential assessment with status and rationale."""
    raise NotImplementedError


def generate_lab_ready_portfolio(candidates: list[dict], spec: dict, memory: dict) -> dict:
    """Return ranked test-first portfolio with backups and provenance."""
    raise NotImplementedError
