"""In-memory state tracking for CriticalMat agent runs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentMemory:
    """Tracks what the agent has tried and learned so far."""

    tried_compositions: list[str] = field(default_factory=list)
    scores_by_iteration: dict[int, list[int]] = field(default_factory=dict)
    current_best: dict = field(default_factory=dict)
    rejection_reasons: list[dict] = field(default_factory=list)

    def record_iteration(self, iteration: int, scored_candidates: list[dict]) -> None:
        """Store score list and keep best candidate updated."""
        scores = [int(c.get("score", 0)) for c in scored_candidates]
        self.scores_by_iteration[iteration] = scores

        if not scored_candidates:
            return

        top = max(scored_candidates, key=lambda c: c.get("score", 0))
        if not self.current_best or top.get("score", 0) > self.current_best.get("score", 0):
            self.current_best = dict(top)

    def add_composition(self, hypothesis: str) -> None:
        """Track tried hypothesis text for next-step reasoning."""
        if hypothesis and hypothesis not in self.tried_compositions:
            self.tried_compositions.append(hypothesis)

    def add_rejection(self, formula: str, reason: str) -> None:
        """Track rejected candidates and why they were rejected."""
        self.rejection_reasons.append({"formula": formula, "reason": reason})

    def to_dict(self) -> dict:
        """Return a serializable memory shape for teammate functions."""
        return {
            "tried_compositions": list(self.tried_compositions),
            "scores_by_iteration": dict(self.scores_by_iteration),
            "current_best": dict(self.current_best),
            "rejection_reasons": list(self.rejection_reasons),
        }
