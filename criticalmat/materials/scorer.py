"""Candidate scoring logic for P1 scope."""

from __future__ import annotations


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def score_candidate(candidate: dict, spec: dict) -> int:
    """Return a 0-100 score using material performance + supply risk."""
    target = spec.get("target_props", {})

    magnetic = float(candidate.get("magnetic_moment", 0.0) or 0.0)
    formation = float(candidate.get("formation_energy", 0.0) or 0.0)
    hull = float(candidate.get("stability_above_hull", 1.0) or 1.0)
    supply_risk = float(candidate.get("supply_chain_risk", 0.0) or 0.0)

    min_magnetic = float(target.get("min_magnetic_moment", 2.0) or 2.0)
    max_formation = float(target.get("max_formation_energy", 0.1) or 0.1)
    max_hull = float(target.get("max_stability_above_hull", 0.05) or 0.05)

    # 1) Magnetic contribution (0..40): reward values at/above target.
    magnetic_ratio = magnetic / max(min_magnetic, 1e-6)
    magnetic_points = 40.0 * _clamp(magnetic_ratio, 0.0, 1.25) / 1.25

    # 2) Formation energy contribution (0..25): lower is better.
    if formation <= max_formation:
        formation_points = 25.0
    else:
        formation_points = 25.0 * _clamp(max_formation / max(formation, 1e-6), 0.0, 1.0)

    # 3) Stability contribution (0..20): lower energy above hull is better.
    if hull <= max_hull:
        stability_points = 20.0
    else:
        stability_points = 20.0 * _clamp(max_hull / max(hull, 1e-6), 0.0, 1.0)

    # 4) Baseline viability points (0..15): favors non-pathological candidates.
    baseline_points = 15.0 if magnetic > 0 and hull < 1.0 else 5.0

    raw_score = magnetic_points + formation_points + stability_points + baseline_points

    # Supply chain penalty: subtract up to 30 points.
    penalty = 0.30 * _clamp(supply_risk, 0.0, 100.0)
    final_score = int(round(_clamp(raw_score - penalty, 0.0, 100.0)))
    return final_score
