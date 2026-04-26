"""Mock implementations so the loop runs before teammate code lands."""

from __future__ import annotations


def parse_hypothesis(text: str) -> dict:
    lower_text = text.lower()
    banned_elements: list[str] = []
    allowed_elements: list[str] = []

    # Explicit banned cues
    if "without neodymium" in lower_text or "no neodymium" in lower_text:
        banned_elements.append("Nd")
    if "without dysprosium" in lower_text or "no dysprosium" in lower_text:
        banned_elements.append("Dy")
    if "cobalt-free" in lower_text or "without cobalt" in lower_text or "no cobalt" in lower_text:
        banned_elements.append("Co")

    # Strategic policy cues
    if "rare-earth-free" in lower_text or "rare earth free" in lower_text or "avoid rare earth" in lower_text:
        banned_elements.extend(["Nd", "Dy", "Tb", "Pr", "Sm", "Gd"])
    if "radioactive" in lower_text or "safe" in lower_text:
        banned_elements.extend(["Ac", "Am", "Pu", "U", "Th", "Np", "Ra", "Po"])
    if "toxic" in lower_text:
        banned_elements.extend(["As", "Be", "Cd", "Hg", "Pb", "Tl"])

    # Optional allowed-element hints only when explicitly requested.
    if "iron-based" in lower_text or "fe-based" in lower_text:
        allowed_elements.append("Fe")
    if "manganese" in lower_text:
        allowed_elements.append("Mn")
    if "nitride" in lower_text:
        allowed_elements.append("N")
    if "ferrite" in lower_text:
        allowed_elements.extend(["Fe", "O"])

    # Remove duplicates while preserving order.
    banned_elements = list(dict.fromkeys(banned_elements))
    allowed_elements = list(dict.fromkeys(allowed_elements))

    if "missile" in lower_text:
        defense_application = "missile guidance systems"
    elif "drone" in lower_text:
        defense_application = "military drone actuators"
    elif "actuator" in lower_text:
        defense_application = "precision military actuators"
    elif "sonar" in lower_text or "submarine" in lower_text:
        defense_application = "submarine sonar systems"
    else:
        defense_application = "critical defense hardware"

    return {
        "allowed_elements": allowed_elements,
        "banned_elements": banned_elements,
        "target_props": {
            "material_class": "permanent_magnet" if "magnet" in lower_text else "unknown",
            "needs_magnetism": "magnet" in lower_text or "actuator" in lower_text,
            "prefer_high_magnetic_moment": "magnet" in lower_text or "actuator" in lower_text,
            "min_magnetic_moment": 2.0,
            "max_formation_energy": 0.1,
            "max_stability_above_hull": 0.1,
            "prefer_low_formation_energy": True,
            "avoid_rare_earths": "rare-earth-free" in lower_text or "rare earth free" in lower_text,
            "exclude_radioactive": True,
            "require_solid_state": True,
            "require_practical_materials": True,
            "require_manufacturable": True,
            "avoid_toxic_elements": "toxic" in lower_text or "safe" in lower_text,
            "avoid_precious_metals": False,
            "mp_screen_fetch_limit": 100,
        },
        "context": text,
        "defense_application": defense_application,
    }


def get_candidates(
    allowed_elements: list[str],
    banned_elements: list[str],
    target_props: dict,
    limit: int = 50,
) -> list[dict]:
    del target_props  # Mock keeps fixed candidates.
    pool = [
        {
            "formula": "Fe16N2",
            "magnetic_moment": 2.6,
            "formation_energy": -0.12,
            "stability_above_hull": 0.01,
            "elements": ["Fe", "N"],
            "mp_id": "mp-mock-001",
            "supply_chain_risk": 10,
        },
        {
            "formula": "MnAl",
            "magnetic_moment": 1.7,
            "formation_energy": -0.04,
            "stability_above_hull": 0.03,
            "elements": ["Mn", "Al"],
            "mp_id": "mp-mock-002",
            "supply_chain_risk": 18,
        },
        {
            "formula": "Nd2Fe14B",
            "magnetic_moment": 2.9,
            "formation_energy": -0.2,
            "stability_above_hull": 0.00,
            "elements": ["Nd", "Fe", "B"],
            "mp_id": "mp-mock-003",
            "supply_chain_risk": 95,
        },
        {
            "formula": "Co2MnSi",
            "magnetic_moment": 2.1,
            "formation_energy": -0.08,
            "stability_above_hull": 0.02,
            "elements": ["Co", "Mn", "Si"],
            "mp_id": "mp-mock-004",
            "supply_chain_risk": 45,
        },
    ]

    filtered = []
    for candidate in pool:
        # Keep mock results loosely aligned with requested chemistry.
        if allowed_elements and not any(elem in allowed_elements for elem in candidate["elements"]):
            continue
        if any(elem in banned_elements for elem in candidate["elements"]):
            continue
        filtered.append(candidate)
        if len(filtered) >= limit:
            break
    return filtered


def score_candidate(candidate: dict, spec: dict) -> int:
    target_props = spec.get("target_props", {})
    score = 50

    if candidate.get("magnetic_moment", 0) >= target_props.get("min_magnetic_moment", 2.0):
        score += 25
    else:
        score -= 10

    if candidate.get("formation_energy", 1) <= target_props.get("max_formation_energy", 0.1):
        score += 15
    else:
        score -= 10

    if candidate.get("stability_above_hull", 1) <= target_props.get("max_stability_above_hull", 0.05):
        score += 10
    else:
        score -= 10

    score -= int(candidate.get("supply_chain_risk", 0) * 0.25)
    return max(0, min(100, score))


def interpret_results(candidates: list[dict], spec: dict, iteration: int) -> str:
    del spec
    if not candidates:
        return f"Iteration {iteration}: No candidates met the current constraints."

    practical = [c for c in candidates if c.get("is_practical", True)]
    top_pool = practical if practical else candidates
    top = max(top_pool, key=lambda c: c.get("score", 0))
    practical_note = "practical" if practical else "highest-scoring"
    return (
        f"Iteration {iteration}: {top.get('formula')} is the top {practical_note} candidate with score "
        f"{top.get('score', 0)} due to strong magnetic moment and low instability."
    )


def generate_next_hypothesis(memory: dict) -> str:
    tried = memory.get("tried_compositions", [])
    if not tried:
        return "Try iron nitride families with nitrogen-stabilized phases."
    if len(tried) == 1:
        return "Try cobalt-manganese alloys with reduced rare-earth dependency."
    return "Try manganese-aluminum with light-element doping for higher magnetic moment."
