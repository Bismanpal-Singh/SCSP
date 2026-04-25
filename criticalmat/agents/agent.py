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
)


load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


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

    # Add safe defaults for downstream scoring.
    target_props.setdefault("material_class", "unknown")
    target_props.setdefault("needs_magnetism", False)
    target_props.setdefault("prefer_high_magnetic_moment", False)
    target_props.setdefault("max_stability_above_hull", 0.1)
    target_props.setdefault("prefer_low_formation_energy", True)
    target_props.setdefault("avoid_rare_earths", bool(banned_elements))
    target_props.setdefault("mp_screen_fetch_limit", 100)

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

    banned_elements = list(dict.fromkeys(banned_elements))

    is_magnet = "magnet" in lower

    target_props = {
        "material_class": "permanent_magnet" if is_magnet else "unknown",
        "needs_magnetism": is_magnet,
        "prefer_high_magnetic_moment": is_magnet,
        "max_stability_above_hull": 0.1,
        "prefer_low_formation_energy": True,
        "avoid_rare_earths": bool(banned_elements),
        "mp_screen_fetch_limit": 100,
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

    return {
        "allowed_elements": [],
        "banned_elements": banned_elements,
        "target_props": target_props,
        "context": text,
        "defense_application": defense_application,
    }


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
        return _fallback_parse_hypothesis(text)


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

    candidates_sorted = sorted(
        candidates,
        key=lambda candidate: candidate.get("score", candidate.get("final_score", 0)),
        reverse=True,
    )

    prompt = interpret_results_prompt(candidates_sorted, spec, iteration)

    try:
        return _call_gemini(prompt, temperature=0.3)
    except Exception as exc:
        print(f"[agent.py warning] Gemini interpretation failed. Using fallback. Reason: {exc}")

        best = candidates_sorted[0]
        formula = best.get("formula", "unknown material")
        score = best.get("score", best.get("final_score", "N/A"))
        magnetic_moment = best.get("magnetic_moment", "N/A")
        stability = best.get("stability_above_hull", "N/A")
        risk = best.get("supply_chain_risk", "N/A")

        return (
            f"Iteration {iteration}: The strongest candidate is {formula} with a score of {score}. "
            f"It has magnetic moment proxy {magnetic_moment}, stability above hull {stability}, "
            f"and supply-chain risk {risk}. Lower-ranked candidates were likely rejected because "
            "they had weaker magnetic proxies, poorer stability, or higher strategic dependency risk. "
            "The agent should next explore a nearby rare-earth-free composition family."
        )

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
        response = _call_gemini(prompt, temperature=0.5)
        cleaned = response.replace("\n", " ").strip().strip('"').strip("'")

        # Keep only the first sentence if Gemini returns extra text.
        if "." in cleaned:
            cleaned = cleaned.split(".")[0].strip() + "."

        if not cleaned:
            raise ValueError("Gemini returned an empty next hypothesis.")

        return cleaned

    except Exception as exc:
        print(f"[agent.py warning] Gemini next-hypothesis failed. Using fallback. Reason: {exc}")

        memory_text = str(memory).lower()

        if "fe16n2" not in memory_text and "iron nitride" not in memory_text and "fe-n" not in memory_text:
            return (
                "Try Fe-N based compounds such as iron nitride because they may preserve "
                "strong magnetism while avoiding rare-earth dependence."
            )

        if "mn-al" not in memory_text and "mnal" not in memory_text:
            return (
                "Explore Mn-Al-C family candidates because they are rare-earth-free and have "
                "known permanent-magnet potential."
            )

        if "ferrite" not in memory_text and "fe-o" not in memory_text:
            return (
                "Explore ferrite-based Fe-O candidates because they avoid rare earths and have "
                "low strategic supply risk."
            )

        return (
            "Test Fe-Co-Ni compositions with reduced cobalt content to balance magnetic "
            "performance against supply-chain risk."
        )

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