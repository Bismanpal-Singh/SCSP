"""In-memory state tracking for CriticalMat agent runs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentMemory:
    """Tracks what the agent has tried and learned so far."""

    tried_compositions: list[str] = field(default_factory=list)
    tried_families: list[str] = field(default_factory=list)
    scores_by_iteration: dict[int, list[int]] = field(default_factory=dict)
    current_best: dict = field(default_factory=dict)
    rejection_reasons: list[dict] = field(default_factory=list)
    ineligible_candidates: list[dict] = field(default_factory=list)
    portfolio_history: list[dict] = field(default_factory=list)
    uncertainty_gaps: list[str] = field(default_factory=list)
    experiment_queue: list[str] = field(default_factory=list)

    def record_iteration(self, iteration: int, scored_candidates: list[dict]) -> None:
        """Store score list and keep best candidate updated."""
        scores = [int(c.get("score", 0)) for c in scored_candidates]
        self.scores_by_iteration[iteration] = scores
        if len(scores) >= 2:
            sorted_scores = sorted(scores, reverse=True)
            self.uncertainty_gaps.append(
                f"Iteration {iteration}: top-vs-runner-up score gap is {sorted_scores[0] - sorted_scores[1]}"
            )

        if not scored_candidates:
            return

        top = max(scored_candidates, key=lambda c: c.get("score", 0))
        if not self.current_best or top.get("score", 0) > self.current_best.get("score", 0):
            self.current_best = dict(top)

        for candidate in scored_candidates:
            family = str(candidate.get("material_family") or "").strip()
            if family and family not in self.tried_families:
                self.tried_families.append(family)

    def add_composition(self, hypothesis: str) -> None:
        """Track tried hypothesis text for next-step reasoning."""
        if hypothesis and hypothesis not in self.tried_compositions:
            self.tried_compositions.append(hypothesis)

    def add_rejection(self, formula: str, reason: str) -> None:
        """Track rejected candidates and why they were rejected."""
        self.rejection_reasons.append({"formula": formula, "reason": reason})

    def add_ineligible(self, formula: str, reason: str) -> None:
        """Track hard-filter ineligible candidates with rationale."""
        self.ineligible_candidates.append({"formula": formula, "reason": reason})

    def record_portfolio(self, iteration: int, portfolio: dict) -> None:
        """Store generated lab-ready portfolio and update appointment queue."""
        self.portfolio_history.append(dict(portfolio or {}))
        queue = list((portfolio or {}).get("test_queue", []) or [])
        if queue:
            self.experiment_queue = [str(item) for item in queue]

    def to_dict(self) -> dict:
        """Return a serializable memory shape for teammate functions."""
        return {
            "tried_compositions": list(self.tried_compositions),
            "tried_families": list(self.tried_families),
            "scores_by_iteration": dict(self.scores_by_iteration),
            "current_best": dict(self.current_best),
            "rejection_reasons": list(self.rejection_reasons),
            "ineligible_candidates": list(self.ineligible_candidates),
            "portfolio_history": list(self.portfolio_history),
            "uncertainty_gaps": list(self.uncertainty_gaps),
            "experiment_queue": list(self.experiment_queue),
        }
