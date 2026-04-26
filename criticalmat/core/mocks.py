"""Mock implementations so the loop runs before teammate code lands."""

from __future__ import annotations


def parse_hypothesis(text: str) -> dict:
    lower_text = text.lower()
    banned_elements = []
    if "without neodymium" in lower_text or "no neodymium" in lower_text:
        banned_elements.append("Nd")
    if "without dysprosium" in lower_text or "no dysprosium" in lower_text:
        banned_elements.append("Dy")

    return {
        "allowed_elements": ["Fe", "N", "Co", "Mn"],
        "banned_elements": banned_elements,
        "target_props": {
            "min_magnetic_moment": 2.0,
            "max_formation_energy": 0.1,
            "max_stability_above_hull": 0.05,
        },
        "context": text,
        "defense_application": "missile guidance",
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

    top = max(candidates, key=lambda c: c.get("score", 0))
    return (
        f"Iteration {iteration}: {top.get('formula')} leads with score "
        f"{top.get('score', 0)} due to strong magnetic moment and low instability."
    )


def generate_next_hypothesis(memory: dict) -> str:
    tried = memory.get("tried_compositions", [])
    if not tried:
        return "Try iron nitride families with nitrogen-stabilized phases."
    if len(tried) == 1:
        return "Try cobalt-manganese alloys with reduced rare-earth dependency."
    return "Try manganese-aluminum with light-element doping for higher magnetic moment."


def generate_lab_ready_portfolio(candidates: list[dict], spec: dict, memory: dict) -> dict:
    del spec, memory
    eligible = [dict(c) for c in candidates if bool(c.get("eligible", True))]
    eligible.sort(key=lambda c: int(c.get("score", 0)), reverse=True)
    top = eligible[:3]
    portfolio = []
    queue = []
    for idx, candidate in enumerate(top, start=1):
        status = "TEST_FIRST" if idx == 1 else ("BACKUP_TEST" if idx == 2 else "SAFE_FALLBACK")
        formula = str(candidate.get("formula", f"candidate_{idx}"))
        portfolio.append({"formula": formula, "status": status, "reason": "Mock-ranked by score."})
        queue.append(
            {
                "rank": idx,
                "formula": formula,
                "status": status,
                "experiment": f"Run baseline synthesis and magnetic characterization for {formula}.",
            }
        )
    return {
        "mission": "Generate a practical magnet test set.",
        "constraints": {},
        "portfolio": portfolio,
        "test_queue": queue,
        "provenance_tree": {"source": "mock_portfolio"},
    }
