"""Candidate scoring logic for P1 scope."""

from __future__ import annotations

from criticalmat.core.policy import get_policy


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _compute_score_components(candidate: dict, spec: dict) -> dict:
    """Compute 2.0 weighted score and breakdown components."""
    target = dict(spec.get("target_props", {}) or {})
    material_class = str(target.get("material_class", "unknown")).lower()
    policy = get_policy({"target_props": target})

    magnetic_moment = float(candidate.get("magnetic_moment", 0.0) or 0.0)
    band_gap = candidate.get("band_gap")
    band_gap_value = float(band_gap or 0.0)
    hull = float(candidate.get("stability_above_hull", 1.0) or 1.0)
    supply_chain_risk = float(candidate.get("supply_chain_risk", 0.0) or 0.0)
    material_family = str(candidate.get("material_family", "") or "")

    known_families = [
        "Fe-N",
        "Mn-Al",
        "Fe-Co",
        "Fe-Si",
        "Mn-Al-C",
        "Fe-Ni",
        "Co-Fe",
        "Si-Ge",
        "GaAs",
        "InP",
    ]

    stability_score = _clamp(100 - (hull * 500), 0.0, 100.0)
    supply_chain_safety = _clamp(100 - supply_chain_risk, 0.0, 100.0)
    scientific_fit_from_band_gap = _clamp(100 - abs(band_gap_value - 1.1) * 30, 0.0, 100.0)

    if material_class == "permanent_magnet":
        scientific_fit = _clamp((magnetic_moment / 80.0) * 100, 0.0, 100.0)
    elif material_class == "semiconductor":
        scientific_fit = scientific_fit_from_band_gap
    elif material_class == "battery_material":
        scientific_fit = stability_score
    elif material_class in {"protective_coating", "high_temperature_structural_material"}:
        scientific_fit = (stability_score + supply_chain_safety) / 2.0
    elif material_class == "sensor_material":
        scientific_fit = (scientific_fit_from_band_gap + stability_score) / 2.0
    else:
        scientific_fit = (stability_score + supply_chain_safety) / 2.0

    manufacturability_score = 70.0
    if int(candidate.get("element_count", 5) or 5) > 4:
        manufacturability_score -= 20.0
    if bool(candidate.get("is_solid_state", False)):
        manufacturability_score += 20.0
    if material_family in known_families:
        manufacturability_score += 10.0
    manufacturability_score = _clamp(manufacturability_score, 0.0, 100.0)

    evidence_confidence_score = 50.0
    if candidate.get("magnetic_moment") is not None:
        evidence_confidence_score += 15.0
    if candidate.get("band_gap") is not None:
        evidence_confidence_score += 10.0
    if candidate.get("stability_above_hull") is not None:
        evidence_confidence_score += 15.0
    if material_family in known_families:
        evidence_confidence_score += 10.0
    evidence_confidence_score = _clamp(evidence_confidence_score, 0.0, 100.0)

    overall = (
        float(policy.w_scientific_fit) * scientific_fit
        + float(policy.w_stability) * stability_score
        + float(policy.w_supply_chain) * supply_chain_safety
        + float(policy.w_manufacturability) * manufacturability_score
        + float(policy.w_evidence) * evidence_confidence_score
    )
    final_score = int(min(100, max(0, overall)))

    return {
        "final_score": final_score,
        "score_breakdown": {
            "scientific_fit": round(scientific_fit, 2),
            "stability": round(stability_score, 2),
            "supply_chain_safety": round(supply_chain_safety, 2),
            "manufacturability": round(manufacturability_score, 2),
            "evidence_confidence": round(evidence_confidence_score, 2),
            "overall": final_score,
        },
        "scientific_fit_logic": int(round(scientific_fit)),
        "stability_score": int(round(stability_score)),
        "supply_chain_safety_score": int(round(supply_chain_safety)),
        "manufacturability_score": int(round(manufacturability_score)),
        "evidence_confidence_score": int(round(evidence_confidence_score)),
    }


def score_candidate(candidate: dict, spec: dict) -> int:
    """Return a 0-100 score using material performance + supply risk."""
    components = _compute_score_components(candidate, spec)
    candidate["score_breakdown"] = components["score_breakdown"]
    candidate["scientific_fit_logic"] = components["scientific_fit_logic"]
    candidate["stability_score"] = components["stability_score"]
    candidate["supply_chain_safety_score"] = components["supply_chain_safety_score"]
    candidate["manufacturability_score"] = components["manufacturability_score"]
    candidate["evidence_confidence_score"] = components["evidence_confidence_score"]
    final_score = int(components["final_score"])
    return final_score
