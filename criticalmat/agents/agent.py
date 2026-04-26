"""
agent.py

Person 2: Gemini Agent Engineer for CriticalMat.

Owns:
1. parse_hypothesis(text: str) -> dict
2. interpret_results(candidates: list, spec: dict, iteration: int) -> str

This file uses Gemini instead of Claude, while keeping the exact same interface
expected by the rest of the team.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from google import genai

from criticalmat.agents.prompts import (
    parse_hypothesis_prompt,
    interpret_results_prompt,
    generate_next_hypothesis_prompt,
    synthesis_recommendation_prompt,
    lab_ready_potential_prompt,
    lab_ready_portfolio_prompt,
)


load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-lite-preview")

RADIOACTIVE_ELEMENTS = {
    "Tc", "Pm", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th", "Pa", "U",
    "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr"
}

COMMON_RARE_EARTHS = {
    "Sc", "Y", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd",
    "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu"
}

HIGH_TOXICITY_OR_PROBLEMATIC_ELEMENTS = {
    "Hg", "Cd", "Pb", "As", "Be", "Tl"
}

PRECIOUS_OR_LOW_SCALABILITY_ELEMENTS = {
    "Pt", "Pd", "Rh", "Ir", "Ru", "Os", "Au", "Ag"
}

def _get_client() -> genai.Client:
    """
    Create a Gemini client using GEMINI_API_KEY from .env.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Missing GEMINI_API_KEY. Add this to your .env file:\n"
            "GEMINI_API_KEY=your_key_here"
        )

    return genai.Client(api_key=api_key)


def _call_gemini(prompt: str, temperature: float = 0.2) -> str:
    """
    Call Gemini and return only visible text.

    This manually extracts text parts so the SDK does not print warnings
    about non-text parts such as thought_signature.
    """
    client = _get_client()

    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=prompt,
        config={
            "temperature": temperature,
        },
    )

    text_parts = []

    if getattr(response, "candidates", None):
        for candidate in response.candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None)

            if parts:
                for part in parts:
                    part_text = getattr(part, "text", None)
                    if part_text:
                        text_parts.append(part_text)

    text = "\n".join(text_parts).strip()

    if not text:
        # fallback to response.text if manual extraction fails
        text = getattr(response, "text", "") or ""

    text = text.strip()

    if not text:
        raise RuntimeError("Gemini returned an empty text response.")

    return text

def _extract_json(text: str) -> dict[str, Any]:
    """
    Extract JSON from model output.

    Handles:
    - pure JSON
    - ```json fenced JSON
    - extra accidental text around JSON
    """
    cleaned = text.strip()

    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model response:\n{text}")

    parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object from Gemini.")

    return parsed


def _normalize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """
    Make sure parse_hypothesis always returns the same stable structure.

    This also strengthens constraints such as:
    - non-radioactive
    - solid-state
    - manufacturable
    - practical/scalable materials
    """
    allowed_elements = spec.get("allowed_elements", [])
    banned_elements = spec.get("banned_elements", [])
    target_props = spec.get("target_props", {})
    context = spec.get("context", "")
    defense_application = spec.get("defense_application", "")

    if not isinstance(allowed_elements, list):
        allowed_elements = []

    if not isinstance(banned_elements, list):
        banned_elements = []

    if not isinstance(target_props, dict):
        target_props = {}

    preferred_families = target_props.get("preferred_families", [])
    if not isinstance(preferred_families, list):
        preferred_families = []
    preferred_families = [str(f).strip().lower() for f in preferred_families if str(f).strip()]

    allowed_elements = [
        str(element).strip()
        for element in allowed_elements
        if str(element).strip()
    ]

    banned_elements = [
        str(element).strip()
        for element in banned_elements
        if str(element).strip()
    ]

    # Remove duplicates while preserving order.
    allowed_elements = list(dict.fromkeys(allowed_elements))
    banned_elements = list(dict.fromkeys(banned_elements))

    # Safe defaults for downstream scoring and interpretation.
    target_props.setdefault("material_class", "unknown")
    target_props.setdefault("needs_magnetism", False)
    target_props.setdefault("prefer_high_magnetic_moment", False)
    target_props.setdefault("max_stability_above_hull", 0.1)
    target_props.setdefault("prefer_low_formation_energy", True)

    # New explicit constraint defaults.
    target_props.setdefault("avoid_rare_earths", bool(set(banned_elements) & COMMON_RARE_EARTHS))
    target_props.setdefault("exclude_radioactive", True)
    target_props.setdefault("require_solid_state", True)
    target_props.setdefault("require_practical_materials", True)
    target_props.setdefault("require_manufacturable", True)
    target_props.setdefault("require_non_toxic", True)
    target_props.setdefault("require_compound", "magnet" in str(target_props.get("material_class", "")).lower())
    target_props.setdefault("avoid_toxic_elements", True)
    target_props.setdefault("avoid_precious_metals", False)
    target_props.setdefault("mp_screen_fetch_limit", 100)
    target_props["preferred_families"] = list(dict.fromkeys(preferred_families))

    # If user wants rare-earth avoidance, banned list should include common rare earths.
    if target_props.get("avoid_rare_earths"):
        for element in ["Nd", "Dy", "Tb", "Pr", "Sm", "Gd"]:
            if element not in banned_elements:
                banned_elements.append(element)

    # If exclude_radioactive is true, add radioactive elements to banned list.
    if target_props.get("exclude_radioactive"):
        for element in sorted(RADIOACTIVE_ELEMENTS):
            if element not in banned_elements:
                banned_elements.append(element)

    # If avoid toxic elements is true, add problematic elements to banned list.
    if target_props.get("avoid_toxic_elements"):
        for element in sorted(HIGH_TOXICITY_OR_PROBLEMATIC_ELEMENTS):
            if element not in banned_elements:
                banned_elements.append(element)

    # Keep duplicates removed after adding constraints.
    banned_elements = list(dict.fromkeys(banned_elements))

    return {
        "allowed_elements": allowed_elements,
        "banned_elements": banned_elements,
        "target_props": target_props,
        "context": str(context),
        "defense_application": str(defense_application),
    }

def _fallback_parse_hypothesis(text: str) -> dict[str, Any]:
    """
    Simple rule-based backup parser.

    This keeps the demo from crashing if Gemini is unavailable.
    """
    lower = text.lower()

    banned_elements = []
    allowed_elements: list[str] = []
    preferred_families: list[str] = []

    if "neodymium" in lower or " nd" in lower or "nd-" in lower:
        banned_elements.append("Nd")

    if "dysprosium" in lower or " dy" in lower:
        banned_elements.append("Dy")

    if "terbium" in lower or " tb" in lower:
        banned_elements.append("Tb")

    if "cobalt" in lower and any(word in lower for word in ["without", "avoid", "free", "no "]):
        banned_elements.append("Co")

    if "rare earth" in lower or "rare-earth" in lower or "chinese rare" in lower:
        banned_elements.extend(["Nd", "Dy", "Tb", "Pr", "Sm", "Gd"])

    if "all rare earth" in lower or "avoid rare earth" in lower:
        banned_elements.extend(sorted(COMMON_RARE_EARTHS))

    exclude_radioactive = any(
        phrase in lower
        for phrase in [
            "non-radioactive",
            "non radioactive",
            "radioactive-free",
            "no radioactive",
            "avoid radioactive",
            "field-safe",
            "safe",
            "deployable",
        ]
    )

    require_solid_state = any(
        phrase in lower
        for phrase in [
            "solid-state",
            "solid state",
            "bulk material",
            "crystal",
            "ceramic",
            "alloy",
            "manufacturable",
            "deployable",
        ]
    )

    require_practical_materials = any(
        phrase in lower
        for phrase in [
            "manufacturable",
            "scalable",
            "practical",
            "production-ready",
            "production ready",
            "deployable",
            "field-ready",
            "field ready",
        ]
    )

    avoid_toxic_elements = any(
        phrase in lower
        for phrase in [
            "non-toxic",
            "nontoxic",
            "low-toxicity",
            "low toxicity",
            "environmentally safe",
            "safe",
            "deployable",
        ]
    )

    banned_elements = list(dict.fromkeys(banned_elements))

    is_magnet = "magnet" in lower

    if any(token in lower for token in ["actuator", "precision actuator", "servo"]):
        preferred_families = ["mn_al", "fe_n"]
        allowed_elements = ["Mn", "Al", "C", "Fe", "N"]
    elif any(token in lower for token in ["missile", "guidance", "aerospace"]):
        preferred_families = ["fe_n", "ferrite"]
        allowed_elements = ["Fe", "N", "O", "B", "Si"]
    elif any(token in lower for token in ["manufacturable", "scalable", "production"]):
        preferred_families = ["ferrite", "mn_al"]
        allowed_elements = ["Fe", "O", "Mn", "Al", "C"]
    elif is_magnet:
        preferred_families = ["fe_n", "mn_al", "ferrite"]
        allowed_elements = ["Fe", "Mn", "Al", "N", "O", "C"]

    if "battery" in lower or "cathode" in lower:
        material_class = "battery_material"
    elif "semiconductor" in lower or "chip" in lower:
        material_class = "semiconductor"
    elif "coating" in lower or "corrosion" in lower:
        material_class = "protective_coating"
    elif is_magnet:
        material_class = "permanent_magnet"
    else:
        material_class = "unknown"

    target_props = {
        "material_class": material_class,
        "needs_magnetism": is_magnet,
        "prefer_high_magnetic_moment": is_magnet,
        "max_stability_above_hull": 0.1,
        "prefer_low_formation_energy": True,
        "avoid_rare_earths": bool(set(banned_elements) & COMMON_RARE_EARTHS),

        # New explicit constraints.
        "exclude_radioactive": exclude_radioactive or True,
        "require_solid_state": require_solid_state or True,
        "require_practical_materials": require_practical_materials or True,
        "require_manufacturable": require_practical_materials or True,
        "avoid_toxic_elements": avoid_toxic_elements or True,
        "avoid_precious_metals": False,
        "mp_screen_fetch_limit": 100,
        "preferred_families": preferred_families,
    }

    if "missile" in lower:
        defense_application = "missile guidance systems"
    elif "drone" in lower:
        defense_application = "military drones"
    elif "sonar" in lower or "submarine" in lower:
        defense_application = "submarine sonar or naval systems"
    elif "aircraft" in lower or "f-35" in lower:
        defense_application = "military aircraft systems"
    else:
        defense_application = "critical defense hardware"

    return _normalize_spec(
        {
            "allowed_elements": allowed_elements,
            "banned_elements": banned_elements,
            "target_props": target_props,
            "context": text,
            "defense_application": defense_application,
        }
    )

def parse_hypothesis(text: str) -> dict:
    """
    Convert plain-English user input into structured material-search constraints.

    Required team interface:
        parse_hypothesis(text: str) -> dict

    Returns:
        {
            "allowed_elements": list,
            "banned_elements": list,
            "target_props": dict,
            "context": str,
            "defense_application": str
        }
    """
    if not text or not text.strip():
        raise ValueError("Hypothesis text cannot be empty.")

    prompt = parse_hypothesis_prompt(text)

    try:
        raw_response = _call_gemini(prompt, temperature=0.1)
        parsed = _extract_json(raw_response)
        return _normalize_spec(parsed)
    except Exception as exc:
        print(f"[agent.py warning] Gemini parse failed. Using fallback parser. Reason: {exc}")
        return {
            "allowed_elements": ["Fe", "Mn", "Al", "Ni", "Si", "C", "N", "B"],
            "banned_elements": ["Nd", "Dy", "Tb", "Ho", "Pr", "Eu", "Gd", "Co", "Sm", "Ce", "La", "Y"],
            "target_props": {
                "magnetic_moment": {"min": 2.0},
                "formation_energy": {"max": 0.0},
                "stability_above_hull": {"max": 0.1},
                "material_class": "permanent_magnet",
                "exclude_radioactive": True,
                "require_solid_state": True,
                "require_manufacturable": True,
                "require_non_toxic": True,
            },
            "context": "Rare-earth-free permanent magnet for defense applications",
        }
        
def _candidate_elements(candidate: dict) -> set[str]:
    """
    Extract element symbols from a candidate dict.
    """
    elements = candidate.get("elements", [])

    if isinstance(elements, list):
        return {str(element).strip() for element in elements if str(element).strip()}

    formula = str(candidate.get("formula", ""))
    found = set(re.findall(r"[A-Z][a-z]?", formula))
    return found


def _annotate_candidate_eligibility(candidate: dict, spec: dict) -> dict:
    """
    Adds eligibility metadata to a candidate.

    This prevents interpretation from calling unsafe or constraint-violating
    candidates the 'best' or 'top' result.
    """
    annotated = dict(candidate)

    target_props = spec.get("target_props", {})
    banned_elements = set(spec.get("banned_elements", []))
    elements = _candidate_elements(candidate)

    reasons = []

    banned_overlap = sorted(elements & banned_elements)
    if banned_overlap:
        reasons.append(f"contains banned element(s): {', '.join(banned_overlap)}")

    if target_props.get("exclude_radioactive", True):
        radioactive_overlap = sorted(elements & RADIOACTIVE_ELEMENTS)
        if radioactive_overlap:
            reasons.append(f"contains radioactive element(s): {', '.join(radioactive_overlap)}")

    if target_props.get("avoid_toxic_elements", True):
        toxic_overlap = sorted(elements & HIGH_TOXICITY_OR_PROBLEMATIC_ELEMENTS)
        if toxic_overlap:
            reasons.append(f"contains high-toxicity/problematic element(s): {', '.join(toxic_overlap)}")

    if target_props.get("avoid_precious_metals", False):
        precious_overlap = sorted(elements & PRECIOUS_OR_LOW_SCALABILITY_ELEMENTS)
        if precious_overlap:
            reasons.append(f"uses precious/low-scalability element(s): {', '.join(precious_overlap)}")

    stability = candidate.get("stability_above_hull", None)
    max_stability = target_props.get("max_stability_above_hull", 0.1)

    try:
        if stability is not None and float(stability) > float(max_stability):
            reasons.append(
                f"stability_above_hull {stability} exceeds limit {max_stability}"
            )
    except (TypeError, ValueError):
        pass

    # Optional practical-material heuristic.
    if target_props.get("require_practical_materials", True):
        formula = str(candidate.get("formula", ""))
        if len(elements) > 5:
            reasons.append("too many distinct elements for a practical first-pass material candidate")
        if "Fr" in elements or "Ra" in elements or "Ac" in elements:
            reasons.append("contains impractical radioactive/heavy element for deployable material")

    annotated["eligible"] = len(reasons) == 0
    annotated["eligibility_status"] = "ELIGIBLE" if len(reasons) == 0 else "INELIGIBLE"
    annotated["ineligibility_reasons"] = reasons

    return annotated


def _annotate_candidates(candidates: list, spec: dict) -> list[dict]:
    """
    Annotate all candidates with eligibility metadata.
    """
    return [_annotate_candidate_eligibility(candidate, spec) for candidate in candidates]

def interpret_results(candidates: list, spec: dict, iteration: int) -> str:
    """
    Produce a human-readable interpretation of scored candidate materials.

    Required team interface:
        interpret_results(candidates: list, spec: dict, iteration: int) -> str
    """
    if not candidates:
        return (
            f"Iteration {iteration}: No candidates were returned. "
            "The agent should broaden the search, relax constraints, or try a different material family."
        )

    annotated_candidates = _annotate_candidates(candidates, spec)

    # Sort eligible candidates first, then by score.
    candidates_sorted = sorted(
        annotated_candidates,
        key=lambda candidate: (
            1 if candidate.get("eligible", False) else 0,
            candidate.get("score", candidate.get("final_score", 0)),
        ),
        reverse=True,
    )

    prompt = interpret_results_prompt(candidates_sorted, spec, iteration)

    try:
        return _call_gemini(prompt, temperature=0.3)
    except Exception as exc:
        print(f"[agent.py warning] Gemini interpretation failed. Using fallback. Reason: {exc}")
        eligible = [c for c in candidates_sorted if c.get("eligible", False)]
        ineligible = [c for c in candidates_sorted if not c.get("eligible", False)]

        lines = [
            "This iteration screened candidates under hard safety, practicality, and supply-chain constraints.",
            "INELIGIBLE CANDIDATES:",
        ]
        if ineligible:
            for candidate in ineligible[:4]:
                formula = candidate.get("formula", "unknown")
                reasons = "; ".join(candidate.get("ineligibility_reasons", [])) or "hard constraints failed"
                lines.append(f"- {formula}: {reasons}")
        else:
            lines.append("- None")

        if eligible:
            top = eligible[0]
            lines.append(
                f"Top eligible candidate is {top.get('formula', 'unknown')} "
                f"with score {top.get('score', top.get('final_score', 'N/A'))}."
            )
        else:
            lines.append("No eligible candidate passed all hard constraints this round.")

        return " ".join(lines)
    
def generate_next_hypothesis(memory: dict) -> str:
    """
    Generate the next material hypothesis for the autonomous loop.

    Required team interface:
        generate_next_hypothesis(memory: dict) -> str

    Returns:
        A single plain-English sentence describing the next material family
        or composition direction to test.
    """
    if memory is None:
        memory = {}

    prompt = generate_next_hypothesis_prompt(memory)

    try:
        response = _call_gemini(prompt, temperature=0.65)
        cleaned = response.replace("\n", " ").strip().strip('"').strip("'")

        # Keep only the first sentence if Gemini returns extra text.
        if "." in cleaned:
            cleaned = cleaned.split(".")[0].strip() + "."

        if not cleaned:
            raise ValueError("Gemini returned an empty next hypothesis.")

        return cleaned

    except Exception as exc:
        print(f"[agent.py warning] Gemini next-hypothesis failed. Using fallback. Reason: {exc}")
        return (
            "Explore Mn-Al binary and ternary compounds, particularly Mn4Al9 and "
            "MnAl families, which are known rare-earth-free permanent magnet "
            "candidates with high coercivity potential and full domestic sourcing."
        )


def generate_synthesis_recommendation(candidate: dict) -> str:
    """Return a short, realistic synthesis route for the winning candidate."""
    prompt = synthesis_recommendation_prompt(candidate or {})
    try:
        response = _call_gemini(prompt, temperature=0.25).replace("\n", " ").strip()
        if not response:
            raise ValueError("Empty synthesis recommendation from Gemini.")
        return response
    except Exception as exc:
        print(f"[agent.py warning] Gemini synthesis recommendation failed. Using fallback. Reason: {exc}")
        formula = str((candidate or {}).get("formula", "the candidate material"))
        return (
            f"Synthesize {formula} via arc melting of elemental precursors "
            f"followed by annealing at 800°C for 24 hours under argon atmosphere "
            f"to achieve the desired ordered phase with optimal magnetic properties."
        )


def generate_lab_ready_potential(candidate: dict) -> dict:
    """
    Return lab-readiness potential classification.

    Returns:
    {
      "status": "high" | "medium" | "low",
      "summary": str,
      "reasons": list[str]
    }
    """
    prompt = lab_ready_potential_prompt(candidate or {})
    try:
        raw = _call_gemini(prompt, temperature=0.2)
        parsed = _extract_json(raw)
        status = str(parsed.get("status", "medium")).strip().lower()
        if status not in {"high", "medium", "low"}:
            status = "medium"
        summary = str(parsed.get("summary", "")).strip() or "Candidate shows moderate lab-readiness potential."
        reasons_raw = parsed.get("reasons", [])
        reasons = [str(reason).strip() for reason in reasons_raw if str(reason).strip()] if isinstance(reasons_raw, list) else []
        if not reasons:
            reasons = [
                "Based on predicted stability and composition practicality.",
                "Requires experimental verification before scale-up.",
            ]
        return {"status": status, "summary": summary, "reasons": reasons[:5]}
    except Exception as exc:
        print(f"[agent.py warning] Gemini lab-readiness evaluation failed. Using fallback. Reason: {exc}")
        stability = float((candidate or {}).get("stability_above_hull", 1.0) or 1.0)
        risk = int((candidate or {}).get("supply_chain_risk", 100) or 100)
        if stability <= 0.05 and risk <= 10:
            status = "high"
        elif stability <= 0.12 and risk <= 40:
            status = "medium"
        else:
            status = "low"
        formula = str((candidate or {}).get("formula", "candidate"))
        return {
            "status": status,
            "summary": f"{formula} is assessed as {status} lab-ready potential based on current computational evidence.",
            "reasons": [
                f"Stability-above-hull observed at {stability:.3f} eV/atom.",
                f"Supply-chain risk estimated at {risk}%.",
                "Experimental synthesis and validation are still required.",
            ],
        }


def generate_lab_ready_portfolio(candidates: list[dict], spec: dict, memory: dict) -> dict:
    """Build a ranked actionable portfolio for immediate testing."""
    eligible = [dict(c) for c in (candidates or []) if bool(c.get("eligible", True))]
    eligible.sort(key=lambda c: int(c.get("score", 0)), reverse=True)
    top = eligible[:5]
    prompt = lab_ready_portfolio_prompt(top, spec or {}, memory or {})

    try:
        raw = _call_gemini(prompt, temperature=0.25)
        parsed = _extract_json(raw)
        portfolio = parsed if isinstance(parsed, dict) else {}
    except Exception as exc:
        print(f"[agent.py warning] Gemini portfolio generation failed. Using fallback. Reason: {exc}")
        entries = []
        queue = []
        for idx, candidate in enumerate(top[:3], start=1):
            status = "TEST_FIRST" if idx == 1 else ("BACKUP_TEST" if idx == 2 else "SAFE_FALLBACK")
            formula = str(candidate.get("formula", f"candidate_{idx}"))
            entries.append(
                {
                    "formula": formula,
                    "status": status,
                    "reason": "Ranked by score, stability, and supply-chain practicality.",
                }
            )
            queue.append(
                {
                    "rank": idx,
                    "formula": formula,
                    "status": status,
                    "experiment": f"Prepare {formula} by arc melting and anneal to verify phase and magnetization.",
                }
            )

        target_props = (spec or {}).get("target_props", {}) or {}
        portfolio = {
            "mission": str((spec or {}).get("context", "Identify practical defense-ready candidate.")),
            "constraints": {
                "material_class": str(target_props.get("material_class", "unknown")),
                "exclude_radioactive": bool(target_props.get("exclude_radioactive", True)),
                "require_solid_state": bool(target_props.get("require_solid_state", True)),
                "require_manufacturable": bool(target_props.get("require_manufacturable", True)),
                "require_non_toxic": bool(target_props.get("require_non_toxic", True)),
            },
            "portfolio": entries,
            "test_queue": queue,
            "provenance_tree": {
                "source": "criticalmat_agent",
                "based_on_iteration_count": len((memory or {}).get("scores_by_iteration", {})),
                "notes": "Fallback portfolio from deterministic ranking.",
            },
        }

    # Normalize and guard statuses/shape.
    valid_status = {"TEST_FIRST", "BACKUP_TEST", "SAFE_FALLBACK"}
    normalized_entries = []
    for entry in list((portfolio or {}).get("portfolio", []) or []):
        formula = str(entry.get("formula", "unknown"))
        status = str(entry.get("status", "SAFE_FALLBACK")).upper()
        if status not in valid_status:
            status = "SAFE_FALLBACK"
        normalized_entries.append(
            {
                "formula": formula,
                "status": status,
                "reason": str(entry.get("reason", "Portfolio-ranked candidate.")),
            }
        )
    if not normalized_entries and top:
        normalized_entries = [
            {"formula": str(top[0].get("formula", "unknown")), "status": "TEST_FIRST", "reason": "Highest ranked eligible candidate."}
        ]

    normalized_queue = []
    for idx, item in enumerate(list((portfolio or {}).get("test_queue", []) or []), start=1):
        status = str(item.get("status", "SAFE_FALLBACK")).upper()
        if status not in valid_status:
            status = "SAFE_FALLBACK"
        normalized_queue.append(
            {
                "rank": int(item.get("rank", idx) or idx),
                "formula": str(item.get("formula", normalized_entries[min(idx - 1, len(normalized_entries) - 1)]["formula"] if normalized_entries else "unknown")),
                "status": status,
                "experiment": str(item.get("experiment", "Run baseline synthesis and characterization.")),
            }
        )
    if not normalized_queue and normalized_entries:
        normalized_queue = [
            {
                "rank": i + 1,
                "formula": entry["formula"],
                "status": entry["status"],
                "experiment": f"Run synthesis and magnetic characterization for {entry['formula']}.",
            }
            for i, entry in enumerate(normalized_entries)
        ]

    target_props = (spec or {}).get("target_props", {}) or {}
    return {
        "mission": str((portfolio or {}).get("mission", (spec or {}).get("context", "Defense-ready material discovery"))),
        "constraints": {
            "material_class": str((portfolio or {}).get("constraints", {}).get("material_class", target_props.get("material_class", "unknown"))),
            "exclude_radioactive": bool((portfolio or {}).get("constraints", {}).get("exclude_radioactive", target_props.get("exclude_radioactive", True))),
            "require_solid_state": bool((portfolio or {}).get("constraints", {}).get("require_solid_state", target_props.get("require_solid_state", True))),
            "require_manufacturable": bool((portfolio or {}).get("constraints", {}).get("require_manufacturable", target_props.get("require_manufacturable", True))),
            "require_non_toxic": bool((portfolio or {}).get("constraints", {}).get("require_non_toxic", target_props.get("require_non_toxic", True))),
        },
        "portfolio": normalized_entries,
        "test_queue": normalized_queue,
        "provenance_tree": dict((portfolio or {}).get("provenance_tree", {"source": "criticalmat_agent", "notes": "Generated portfolio."})),
    }
if __name__ == "__main__":
    """
    Local test for Person 2 only.

    Run from SCSP root:
        python -m criticalmat.agents.agent
    """

    user_input = (
        "Find a permanent magnet for missile guidance systems that does not depend on Chinese rare earths."
    )

    print("\n--- Testing parse_hypothesis() ---")
    spec = parse_hypothesis(user_input)
    print(json.dumps(spec, indent=2))

    print("\n--- Testing interpret_results() ---")
    fake_candidates = [
        {
            "formula": "Fe16N2",
            "score": 87,
            "magnetic_moment": 2.4,
            "formation_energy": -0.35,
            "stability_above_hull": 0.04,
            "supply_chain_risk": 8,
            "elements": ["Fe", "N"],
            "mp_id": "mp-demo-001",
        },
        {
            "formula": "MnAl",
            "score": 74,
            "magnetic_moment": 1.6,
            "formation_energy": -0.21,
            "stability_above_hull": 0.08,
            "supply_chain_risk": 15,
            "elements": ["Mn", "Al"],
            "mp_id": "mp-demo-002",
        },
        {
            "formula": "CoFe2O4",
            "score": 62,
            "magnetic_moment": 1.9,
            "formation_energy": -0.28,
            "stability_above_hull": 0.03,
            "supply_chain_risk": 55,
            "elements": ["Co", "Fe", "O"],
            "mp_id": "mp-demo-003",
        },
        {
            "formula": "Nd2Fe14B",
            "score": 95,
            "magnetic_moment": 3.1,
            "formation_energy": -0.42,
            "stability_above_hull": 0.02,
            "supply_chain_risk": 95,
            "elements": ["Nd", "Fe", "B"],
            "mp_id": "mp-demo-004",
        },
        {
            "formula": "UFe2",
            "score": 90,
            "magnetic_moment": 2.8,
            "formation_energy": -0.30,
            "stability_above_hull": 0.05,
            "supply_chain_risk": 90,
            "elements": ["U", "Fe"],
            "mp_id": "mp-demo-005",
        },
    ]

    explanation = interpret_results(fake_candidates, spec, iteration=1)
    print(explanation)

    print("\n--- Testing generate_next_hypothesis() ---")
    fake_memory = {
        "tried_compositions": ["Fe16N2", "MnAl", "CoFe2O4"],
        "scores_by_iteration": {
            "1": 87
        },
        "current_best": {
            "formula": "Fe16N2",
            "score": 87,
            "supply_chain_risk": 8,
            "magnetic_moment": 2.4,
            "stability_above_hull": 0.04
        },
        "rejection_reasons": [
            "MnAl had lower magnetic moment.",
            "CoFe2O4 was penalized for cobalt supply-chain risk."
        ]
    }

    next_hypothesis = generate_next_hypothesis(fake_memory)
    print(next_hypothesis)