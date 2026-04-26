"""Candidate scoring logic for P1 scope."""

from __future__ import annotations


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _compute_score_components(candidate: dict, spec: dict) -> dict:
    """Compute score and breakdown components for downstream explainability."""
    target = spec.get("target_props", {})

    magnetic = float(candidate.get("magnetic_moment", 0.0) or 0.0)
    formation = float(candidate.get("formation_energy", 0.0) or 0.0)
    hull = float(candidate.get("stability_above_hull", 1.0) or 1.0)
    supply_risk = float(candidate.get("supply_chain_risk", 0.0) or 0.0)

    min_magnetic = float(target.get("min_magnetic_moment", 2.0) or 2.0)
    max_formation = float(target.get("max_formation_energy", 0.1) or 0.1)
    max_hull = float(target.get("max_stability_above_hull", 0.05) or 0.05)
    material_class = str(target.get("material_class", "")).lower()
    is_magnet_task = ("magnet" in material_class) or bool(target.get("needs_magnetism", False))

    magnetic_ratio = magnetic / max(min_magnetic, 1e-6)
    magnetic_points = 40.0 * _clamp(magnetic_ratio, 0.0, 1.25) / 1.25

    if formation <= max_formation:
        formation_points = 25.0
    else:
        formation_points = 25.0 * _clamp(max_formation / max(formation, 1e-6), 0.0, 1.0)

    if hull <= max_hull:
        stability_points = 20.0
    else:
        stability_points = 20.0 * _clamp(max_hull / max(hull, 1e-6), 0.0, 1.0)

    baseline_points = 15.0 if magnetic > 0 and hull < 1.0 else 5.0
    raw_score = magnetic_points + formation_points + stability_points + baseline_points

    family_tag = str(candidate.get("family_tag", ""))
    elements = set(candidate.get("elements", []) or [])
    single_element_penalty = 0.0
    family_bonus = 0.0
    if is_magnet_task:
        if len(elements) < 2:
            single_element_penalty = 30.0
        if family_tag in {"fe_n", "mn_al", "ferrite", "fe_co"}:
            family_bonus = 10.0
        raw_score = raw_score + family_bonus - single_element_penalty

    penalty = 0.30 * _clamp(supply_risk, 0.0, 100.0)
    final_score = int(round(_clamp(raw_score - penalty, 0.0, 100.0)))

    scientific_fit = int(round(_clamp(magnetic_points + formation_points + stability_points, 0.0, 85.0)))
    manufacturability_score = int(round(_clamp(100.0 - (hull * 500.0) - supply_risk, 0.0, 100.0)))
    evidence_confidence_score = int(round(_clamp(70.0 + (10.0 if candidate.get("mp_id") else 0.0) - (hull * 100.0), 0.0, 100.0)))

    return {
        "final_score": final_score,
        "score_breakdown": {
            "magnetic_points": round(magnetic_points, 2),
            "formation_points": round(formation_points, 2),
            "stability_points": round(stability_points, 2),
            "baseline_points": round(baseline_points, 2),
            "family_bonus": round(family_bonus, 2),
            "single_element_penalty": round(single_element_penalty, 2),
            "supply_chain_penalty": round(penalty, 2),
        },
        "scientific_fit_logic": scientific_fit,
        "manufacturability_score": manufacturability_score,
        "evidence_confidence_score": evidence_confidence_score,
    }


def score_candidate(candidate: dict, spec: dict) -> int:
    """Return a 0-100 score using material performance + supply risk."""
    components = _compute_score_components(candidate, spec)
    candidate["score_breakdown"] = components["score_breakdown"]
    candidate["scientific_fit_logic"] = components["scientific_fit_logic"]
    candidate["manufacturability_score"] = components["manufacturability_score"]
    candidate["evidence_confidence_score"] = components["evidence_confidence_score"]
    final_score = int(components["final_score"])
    return final_score
