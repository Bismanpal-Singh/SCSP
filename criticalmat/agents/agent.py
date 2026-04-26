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
import requests

from criticalmat.agents.prompts import (
    parse_hypothesis_prompt,
    interpret_results_prompt,
    generate_next_hypothesis_prompt,
    synthesis_recommendation_prompt,
    lab_ready_potential_prompt,
    lab_ready_portfolio_prompt,
    decide_next_action_prompt,
    followup_constraints_prompt,
)


load_dotenv()

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-lite-preview")
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
_PROVIDER_LOGGED = False
_FORMULA_VERIFICATION_CACHE: dict[str, dict] = {}
_PROTOCOLS_IO_SEARCH_CACHE: dict[str, list[dict]] = {}
VALID_MATERIAL_CLASSES = {
    "permanent_magnet",
    "semiconductor",
    "battery_material",
    "protective_coating",
    "high_temperature_structural_material",
    "sensor_material",
    "unknown",
}

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

ELEMENT_NAME_TO_SYMBOL = {
    "aluminum": "Al",
    "aluminium": "Al",
    "arsenic": "As",
    "boron": "B",
    "carbon": "C",
    "cerium": "Ce",
    "chromium": "Cr",
    "cobalt": "Co",
    "dysprosium": "Dy",
    "gallium": "Ga",
    "iron": "Fe",
    "neodymium": "Nd",
    "praseodymium": "Pr",
    "samarium": "Sm",
    "terbium": "Tb",
}

_FOLLOWUP_LINE_RE = re.compile(r"^\s*(follow-up|followup|what-?if)\s*[:\-]\s*(.+?)\s*$", flags=re.IGNORECASE)
_ELEMENT_SYMBOL_RE = re.compile(r"^[A-Z][a-z]?$")
_FORMULA_TOKEN_RE = re.compile(r"\b(?:[A-Z][a-z]?\d*){2,}\b")


def _normalize_followup_payload(payload: dict[str, Any]) -> dict[str, Any]:
    family_alias = {
        "oxides": "oxide",
        "sulfides": "sulfide",
        "phosphates": "phosphate",
        "mn al": "mn-al",
        "mnal": "mn-al",
        "mn al c": "mn-al-c",
        "fe n": "fe-n",
        "iron nitride": "fe-n",
        "ferrites": "ferrite",
    }

    def _norm_family(values: Any) -> list[str]:
        out: list[str] = []
        if not isinstance(values, list):
            return out
        for item in values:
            token = str(item or "").strip().lower().replace("_", "-")
            token = family_alias.get(token, token)
            if token and token not in out:
                out.append(token)
        return out

    name_to_symbol = {k.lower(): v for k, v in ELEMENT_NAME_TO_SYMBOL.items()}
    valid_symbols = {
        "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
        "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
        "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
        "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
        "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
        "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
        "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
        "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
        "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
        "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
        "Md", "No", "Lr",
    }

    def _norm_elements(values: Any) -> list[str]:
        out: list[str] = []
        if not isinstance(values, list):
            return out
        for item in values:
            raw = str(item or "").strip()
            if not raw:
                continue
            symbol = raw
            if not _ELEMENT_SYMBOL_RE.match(raw):
                symbol = name_to_symbol.get(raw.lower(), "")
            if symbol in valid_symbols and symbol not in out:
                out.append(symbol)
        return out

    return {
        "include_families": _norm_family(payload.get("include_families", [])),
        "exclude_families": _norm_family(payload.get("exclude_families", [])),
        "exclude_formulas": _norm_family(payload.get("exclude_formulas", [])),
        "add_elements": _norm_elements(payload.get("add_elements", [])),
        "ban_elements": _norm_elements(payload.get("ban_elements", [])),
        "notes": str(payload.get("notes", "") or "").strip(),
    }


def _extract_followup_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in str(text or "").splitlines():
        match = _FOLLOWUP_LINE_RE.match(raw_line)
        if not match:
            continue
        payload = str(match.group(2) or "").strip()
        if payload:
            lines.append(payload)
    return lines


def _parse_structured_followups_regex(text: str) -> dict[str, Any]:
    include_families: list[str] = []
    exclude_families: list[str] = []
    exclude_formulas: list[str] = []
    add_elements: list[str] = []
    ban_elements: list[str] = []

    if not text:
        return {
            "include_families": include_families,
            "exclude_families": exclude_families,
            "exclude_formulas": exclude_formulas,
            "add_elements": add_elements,
            "ban_elements": ban_elements,
        }

    for raw_line in str(text).splitlines():
        match = _FOLLOWUP_LINE_RE.match(raw_line)
        if not match:
            continue
        payload = str(match.group(2) or "").strip().lower()
        if not payload:
            continue

        family_tokens = {
            "oxide": "oxide",
            "oxides": "oxide",
            "sulfide": "sulfide",
            "sulfides": "sulfide",
            "phosphate": "phosphate",
            "phosphates": "phosphate",
            "spinel": "spinel",
            "layered": "layered",
            "olivine": "olivine",
            "nitride": "nitride",
            "carbide": "carbide",
            "boride": "boride",
            "silicide": "silicide",
            "refractory": "refractory",
            "ceramic": "ceramic",
            "ferrite": "ferrite",
            "mn-al": "mn-al",
            "mn al": "mn-al",
            "mnal": "mn-al",
            "mn-al-c": "mn-al-c",
            "mn al c": "mn-al-c",
            "fe-n": "fe-n",
            "fe n": "fe-n",
            "iron nitride": "fe-n",
            "intermetallic": "intermetallic",
        }

        has_negation = any(word in payload for word in ["avoid ", "exclude ", "ban ", "do not ", "don't ", "dont ", "without ", "not need ", "no need "])
        if any(word in payload for word in ["allow ", "include ", "permit ", "ok ", "okay ", "need ", "want ", "prefer "]) and not has_negation:
            for k, v in family_tokens.items():
                if re.search(rf"\b{re.escape(k)}\b", payload):
                    include_families.append(v)
        if has_negation:
            for k, v in family_tokens.items():
                if re.search(rf"\b{re.escape(k)}\b", payload):
                    exclude_families.append(v)
            for formula in _FORMULA_TOKEN_RE.findall(raw_line):
                exclude_formulas.append(formula)

        if any(word in payload for word in ["add ", "include ", "allow "]):
            for name, symbol in ELEMENT_NAME_TO_SYMBOL.items():
                if re.search(rf"\b{name}\b", payload):
                    add_elements.append(symbol)
            for symbol in re.findall(r"\b[A-Z][a-z]?\b", raw_line):
                add_elements.append(symbol)
        if any(word in payload for word in ["avoid ", "exclude ", "ban ", "without ", "cobalt-free", "cobalt free", "don't ", "dont ", "not need ", "no need "]):
            for name, symbol in ELEMENT_NAME_TO_SYMBOL.items():
                if re.search(rf"\b{name}\b", payload):
                    ban_elements.append(symbol)
            for symbol in re.findall(r"\b[A-Z][a-z]?\b", raw_line):
                ban_elements.append(symbol)

    def _dedupe(items: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for item in items:
            key = str(item).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out

    return {
        "include_families": _dedupe(include_families),
        "exclude_families": _dedupe(exclude_families),
        "exclude_formulas": _dedupe(exclude_formulas),
        "add_elements": _dedupe(add_elements),
        "ban_elements": _dedupe(ban_elements),
    }


def _parse_structured_followups(text: str) -> dict[str, Any]:
    """LLM-first parsing for natural-language follow-ups with regex fallback."""
    regex_payload = _parse_structured_followups_regex(text)
    if not text:
        return regex_payload

    enable_llm_parse = os.getenv("CRITICALMAT_LLM_FOLLOWUP_PARSE", "1").strip().lower() not in {"0", "false", "no", "off"}
    if not enable_llm_parse:
        return regex_payload

    lines = _extract_followup_lines(text)
    if not lines:
        return regex_payload

    try:
        parsed = _extract_json(_call_model(followup_constraints_prompt("\n".join(lines)), temperature=0.1))
        llm_payload = _normalize_followup_payload(parsed)
    except Exception:
        return regex_payload

    # Merge LLM + regex (LLM primary, regex as safety net for symbols/aliases).
    merged = {
        "include_families": list(dict.fromkeys((llm_payload.get("include_families", []) or []) + (regex_payload.get("include_families", []) or []))),
        "exclude_families": list(dict.fromkeys((llm_payload.get("exclude_families", []) or []) + (regex_payload.get("exclude_families", []) or []))),
        "exclude_formulas": list(dict.fromkeys((llm_payload.get("exclude_formulas", []) or []) + (regex_payload.get("exclude_formulas", []) or []))),
        "add_elements": list(dict.fromkeys((llm_payload.get("add_elements", []) or []) + (regex_payload.get("add_elements", []) or []))),
        "ban_elements": list(dict.fromkeys((llm_payload.get("ban_elements", []) or []) + (regex_payload.get("ban_elements", []) or []))),
        "notes": str(llm_payload.get("notes", "") or "").strip(),
    }
    return merged

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


def _call_ollama(prompt: str, temperature: float = 0.2) -> str:
    """Call Ollama-compatible chat endpoint and return text response."""
    model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    host = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).rstrip("/")
    timeout_s = float(os.getenv("OLLAMA_TIMEOUT_S", "60"))

    response = requests.post(
        f"{host}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=timeout_s,
    )
    response.raise_for_status()
    payload = response.json()
    text = payload.get("message", {}).get("content", "") if isinstance(payload, dict) else ""
    text = str(text).strip()
    if not text:
        raise RuntimeError("Ollama returned an empty text response.")
    return text


def _call_model(prompt: str, temperature: float = 0.2) -> str:
    """Provider router for Gemini/Ollama model calls."""
    global _PROVIDER_LOGGED
    provider = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if provider not in {"gemini", "ollama"}:
        provider = "gemini"

    if not _PROVIDER_LOGGED:
        if provider == "ollama":
            model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
            host = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).rstrip("/")
            print(f"[agent.py] LLM provider=ollama model={model} host={host}")
        else:
            model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
            print(f"[agent.py] LLM provider=gemini model={model}")
        _PROVIDER_LOGGED = True

    if provider == "ollama":
        return _call_ollama(prompt, temperature=temperature)
    return _call_gemini(prompt, temperature=temperature)

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


def _extract_explicit_banned_elements(text: str) -> list[str]:
    """Preserve elements the user explicitly excludes, even if the LLM omits them."""
    if not text:
        return []

    found: list[str] = []
    lower = text.lower()
    exclusion_patterns = [
        r"(?:excludes?|excluding|without|no|avoid(?:ing)?|bans?|banned)\s+([^.;:]+)",
    ]
    valid_symbols = {
        "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
        "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
        "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
        "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
        "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
        "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
        "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
        "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
        "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
        "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
        "Md", "No", "Lr",
    }

    for pattern in exclusion_patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            phrase = match.group(1)
            phrase = re.split(
                r"\b(?:prioritizes?|requires?|minimizes?|maximizes?|seeks?|target(?:s|ing)?|for)\b",
                phrase,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
            for symbol in re.findall(r"\b[A-Z][a-z]?\b", phrase):
                if symbol in valid_symbols and symbol not in found:
                    found.append(symbol)

    for name, symbol in ELEMENT_NAME_TO_SYMBOL.items():
        if re.search(rf"\b{name}\b", lower) and re.search(
            rf"(without|no|exclude|excludes|excluding|avoid|avoids|avoiding|ban|banned)\b[^.;:]*\b{name}\b",
            lower,
        ):
            if symbol not in found:
                found.append(symbol)
        if re.search(rf"\b{name}\s*-\s*free\b", lower):
            if symbol not in found:
                found.append(symbol)

    for symbol in valid_symbols:
        if re.search(rf"\b{re.escape(symbol)}\s*-\s*free\b", text):
            if symbol not in found:
                found.append(symbol)

    return found


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

    for element in _extract_explicit_banned_elements(str(context)):
        if element not in banned_elements:
            banned_elements.append(element)

    followup = _parse_structured_followups(str(context))
    for element in followup.get("ban_elements", []) or []:
        if element not in banned_elements:
            banned_elements.append(element)
    for element in followup.get("add_elements", []) or []:
        if element not in allowed_elements:
            allowed_elements.append(element)
    # Families are stored in target_props so P1 can bias/filter without hardcoding per use-case.
    include_families = followup.get("include_families", []) or []
    exclude_families = followup.get("exclude_families", []) or []
    exclude_formulas = followup.get("exclude_formulas", []) or []
    if include_families:
        target_props["include_families"] = include_families
    if exclude_families:
        target_props["exclude_families"] = exclude_families
    if exclude_formulas:
        target_props["exclude_formulas"] = [str(item).strip() for item in exclude_formulas if str(item).strip()]

    # Remove duplicates while preserving order.
    allowed_elements = list(dict.fromkeys(allowed_elements))
    banned_elements = list(dict.fromkeys(banned_elements))

    # Safe defaults for downstream scoring and interpretation.
    normalized_material_class = str(target_props.get("material_class", "unknown")).strip().lower()
    if normalized_material_class not in VALID_MATERIAL_CLASSES:
        normalized_material_class = "unknown"
    target_props["material_class"] = normalized_material_class
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
        "exclude_radioactive": bool(exclude_radioactive),
        "require_solid_state": bool(require_solid_state),
        "require_practical_materials": bool(require_practical_materials),
        "require_manufacturable": bool(require_practical_materials),
        "avoid_toxic_elements": bool(avoid_toxic_elements),
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
        raw_response = _call_model(prompt, temperature=0.1)
        parsed = _extract_json(raw_response)
        # Always preserve the original user text so explicit exclusions like
        # "excludes Fe, Co" survive even if the LLM paraphrases the context.
        parsed["context"] = text
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
                "material_class": "unknown",
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

def interpret_results(
    candidates: list,
    spec: dict,
    iteration: int,
    ineligible_candidates: list[dict] | None = None,
) -> str:
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

    prompt = interpret_results_prompt(candidates_sorted, spec, iteration, ineligible_candidates=ineligible_candidates)

    try:
        return _call_model(prompt, temperature=0.3)
    except Exception as exc:
        print(f"[agent.py warning] Gemini interpretation failed. Using fallback. Reason: {exc}")
        eligible = [c for c in candidates_sorted if c.get("eligible", False)]
        ineligible = list(ineligible_candidates or [c for c in candidates_sorted if not c.get("eligible", False)])

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
            lines.append("INELIGIBLE CANDIDATES: None identified in this iteration.")

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

    material_class = str(memory.get("original_material_class", "") or "").strip().lower()
    prompt = generate_next_hypothesis_prompt(memory)

    try:
        response = _call_model(prompt, temperature=0.65)
        cleaned = response.replace("\n", " ").strip().strip('"').strip("'")

        # Keep only the first sentence if Gemini returns extra text.
        if "." in cleaned:
            cleaned = cleaned.split(".")[0].strip() + "."

        if not cleaned:
            raise ValueError("Gemini returned an empty next hypothesis.")

        lower = cleaned.lower()
        if material_class == "battery_material" and any(term in lower for term in ["magnet", "mn-al-c", "permanent magnet"]):
            return "Explore cobalt-free LiFePO4, NaFePO4, and manganese-rich phosphate cathode families for military drone batteries."
        if material_class == "semiconductor" and "magnet" in lower:
            return "Explore SiC, AlN, BN, ZnO, and TiO2 wide-bandgap semiconductor compounds for non-toxic radiation-tolerant defense electronics."

        return cleaned

    except Exception as exc:
        print(f"[agent.py warning] Gemini next-hypothesis failed. Using fallback. Reason: {exc}")
        if material_class == "battery_material":
            return (
                "Explore cobalt-free LiFePO4, NaFePO4, and manganese-rich phosphate cathode "
                "families for military drone batteries."
            )
        if material_class == "semiconductor":
            return (
                "Explore SiC, AlN, BN, ZnO, and TiO2 wide-bandgap semiconductor compounds "
                "for non-toxic radiation-tolerant defense electronics."
            )
        if material_class == "protective_coating":
            return (
                "Explore oxide, nitride, carbide, ceramic, SiC, and Zn/Al-rich coating systems "
                "for corrosion-resistant defense hardware."
            )
        if material_class == "high_temperature_structural_material":
            return (
                "Explore carbide, nitride, boride, silicide, refractory alloy, and stable oxide "
                "families for high-temperature structural applications."
            )
        return (
            "Explore Mn-Al binary and ternary compounds, particularly Mn4Al9 and "
            "MnAl families, which are known rare-earth-free permanent magnet "
            "candidates with high coercivity potential and full domestic sourcing."
        )


def decide_next_action(
    memory: dict,
    spec: dict,
    iteration: int,
    max_iterations: int,
    top_candidates: list[dict],
    interpretation: str,
) -> dict:
    """
    Decide constrained next action for lightweight agentic workflow.

    Returns:
    {
      "action": "retrieve_more" | "refine_direction" | "stop",
      "rationale": str,
      "next_hypothesis": str | None
    }
    """
    if iteration >= max_iterations:
        return {
            "action": "stop",
            "rationale": "Reached max iterations; finalizing with best available candidate.",
            "next_hypothesis": None,
        }

    best = dict((memory or {}).get("current_best", {}) or {})
    best_score = int(best.get("score", 0) or 0)
    if best_score >= 92:
        return {
            "action": "stop",
            "rationale": "Top score is high enough to stop early for demo stability.",
            "next_hypothesis": None,
        }

    fallback_next = generate_next_hypothesis(memory or {})
    heuristic_fallback = {
        "action": "retrieve_more" if best_score < 60 else "refine_direction",
        "rationale": (
            "Best score remains low; run one more retrieval pass."
            if best_score < 60
            else "Use a refined direction to improve candidate quality."
        ),
        "next_hypothesis": fallback_next,
    }

    prompt = decide_next_action_prompt(
        memory=memory or {},
        spec=spec or {},
        iteration=iteration,
        max_iterations=max_iterations,
        top_candidates=top_candidates or [],
        interpretation=str(interpretation or ""),
    )
    try:
        parsed = _extract_json(_call_model(prompt, temperature=0.2))
        action = str(parsed.get("action", "")).strip().lower()
        if action not in {"retrieve_more", "refine_direction", "stop"}:
            action = heuristic_fallback["action"]
        rationale = str(parsed.get("rationale", "")).strip() or heuristic_fallback["rationale"]
        next_hypothesis = parsed.get("next_hypothesis")
        if action == "stop":
            next_hypothesis = None
        elif not isinstance(next_hypothesis, str) or not next_hypothesis.strip():
            next_hypothesis = fallback_next
        else:
            next_hypothesis = next_hypothesis.strip()
        return {
            "action": action,
            "rationale": rationale,
            "next_hypothesis": next_hypothesis,
        }
    except Exception as exc:
        print(f"[agent.py warning] Action planner failed. Using fallback. Reason: {exc}")
        return heuristic_fallback


def generate_synthesis_recommendation(candidate: dict) -> str:
    """Return a short, realistic synthesis route for the winning candidate."""
    prompt = synthesis_recommendation_prompt(candidate or {})
    try:
        response = _call_model(prompt, temperature=0.25).replace("\n", " ").strip()
        if not response:
            raise ValueError("Empty synthesis recommendation from Gemini.")
        return response
    except Exception as exc:
        print(f"[agent.py warning] Gemini synthesis recommendation failed. Using fallback. Reason: {exc}")
        formula = str((candidate or {}).get("formula", "the candidate material"))
        return (
            f"Synthesize {formula} via arc melting of elemental precursors "
            f"followed by annealing at 800°C for 24 hours under argon atmosphere "
            f"as a suggested route for producing a sample for further physical validation."
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
        raw = _call_model(prompt, temperature=0.2)
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


def _looks_like_exact_formula(formula: str) -> bool:
    """Return true only for compact chemical formulas, not families/templates."""
    formula = str(formula or "").strip()
    if not formula:
        return False
    lower = formula.lower()
    template_tokens = (
        "based",
        "system",
        "family",
        "template",
        "candidate",
        "broaden",
        "high-confidence",
        "unknown",
    )
    if any(token in lower for token in template_tokens):
        return False
    if any(char in formula for char in (" ", "-", "/", ",", ";", ":", "<", ">", "+")):
        return False
    return bool(re.fullmatch(r"(?:[A-Z][a-z]?\d*(?:\.\d+)?)+", formula))


def _mp_doc_value(doc: Any, key: str) -> Any:
    if isinstance(doc, dict):
        return doc.get(key)
    return getattr(doc, key, None)


def verify_formula_in_materials_project(formula: str) -> dict:
    """
    Verify an exact formula in Materials Project without affecting ranking.

    Returns only metadata and never raises.
    """
    formula = str(formula or "").strip()
    if not _looks_like_exact_formula(formula):
        return {
            "existence_status": "FAMILY_OR_TEMPLATE",
            "verification_source": "none",
            "verification_id": None,
            "verification_note": "Candidate is a family/template rather than an exact chemical formula; skipped exact Materials Project lookup.",
        }

    if formula in _FORMULA_VERIFICATION_CACHE:
        return dict(_FORMULA_VERIFICATION_CACHE[formula])

    api_key = os.getenv("MP_API_KEY")
    if not api_key:
        result = {
            "existence_status": "VERIFY_ERROR",
            "verification_source": "none",
            "verification_id": None,
            "verification_note": "MP_API_KEY is not configured; Materials Project verification was skipped.",
        }
        _FORMULA_VERIFICATION_CACHE[formula] = result
        return dict(result)

    try:
        from mp_api.client import MPRester

        with MPRester(api_key) as mpr:
            docs = list(
                mpr.materials.summary.search(
                    formula=formula,
                    fields=["material_id", "formula_pretty"],
                )
            )
        if docs:
            material_id = str(_mp_doc_value(docs[0], "material_id") or "")
            result = {
                "existence_status": "VERIFIED_IN_DATABASE",
                "verification_source": "Materials Project",
                "verification_id": material_id or None,
                "verification_note": f"{formula} matched a Materials Project summary entry.",
            }
        else:
            result = {
                "existence_status": "NOT_FOUND_IN_DATABASE",
                "verification_source": "Materials Project",
                "verification_id": None,
                "verification_note": f"No Materials Project summary entry found for exact formula {formula}.",
            }
    except Exception as exc:
        result = {
            "existence_status": "VERIFY_ERROR",
            "verification_source": "Materials Project",
            "verification_id": None,
            "verification_note": f"Materials Project verification failed: {exc}",
        }

    _FORMULA_VERIFICATION_CACHE[formula] = result
    return dict(result)


def verify_top3_formulas(portfolio: list[dict]) -> list[dict]:
    """Attach Materials Project verification metadata to the top 3 items."""
    for entry in portfolio[:3]:
        formula = str(entry.get("formula", entry.get("candidate", "")) or "").strip()
        entry.update(verify_formula_in_materials_project(formula))
    return portfolio


def build_protocol_queries(candidate: dict, spec: dict) -> list[str]:
    """Build protocols.io search terms from material class and experiment context."""
    target_props = dict((spec or {}).get("target_props", {}) or {})
    material_class = str(target_props.get("material_class", "unknown") or "unknown").strip().lower()
    formula = str(candidate.get("formula", candidate.get("candidate", "")) or "").strip()
    family = str(candidate.get("family", candidate.get("material_family", "")) or "").strip()
    experiment = str(candidate.get("recommended_experiment", "") or "").strip()

    class_templates = {
        "permanent_magnet": [
            "XRD phase analysis magnetic alloy",
            "VSM magnetometry magnetic material",
            "SQUID magnetometry magnetic characterization",
            "arc melting alloy synthesis",
        ],
        "semiconductor": [
            "I-V characterization semiconductor",
            "C-V characterization semiconductor",
            "radiation testing semiconductor",
            "DLTS defect spectroscopy",
        ],
        "battery_material": [
            "coin cell assembly cathode",
            "charge discharge cycling battery",
            "electrochemical impedance spectroscopy battery",
            "XRD battery cathode cycling",
        ],
        "protective_coating": [
            "salt spray corrosion testing coating",
            "electrochemical impedance spectroscopy coating",
            "scratch adhesion coating",
            "SEM coating cross section",
        ],
        "high_temperature_structural_material": [
            "thermal cycling ceramic",
            "oxidation test high temperature alloy",
            "TGA DSC thermal stability",
            "hardness testing ceramic",
        ],
    }

    queries = [
        " ".join(part for part in [formula, family, material_class, experiment] if part),
        " ".join(part for part in [formula, family, material_class] if part),
    ]
    queries.extend(class_templates.get(material_class, []))

    deduped: list[str] = []
    seen: set[str] = set()
    for query in queries:
        cleaned = " ".join(str(query).split())
        key = cleaned.lower()
        if cleaned and key not in seen:
            deduped.append(cleaned)
            seen.add(key)
    return deduped[:6]


def _protocol_item_text(item: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)
        if value:
            return str(value).strip()
    return ""


def _normalize_protocol_item(item: dict, query: str) -> dict | None:
    title = _protocol_item_text(item, ("title", "name", "protocol_name"))
    url = _protocol_item_text(item, ("url", "uri", "protocol_uri", "public_url", "html_url"))
    if not title or not url or not url.startswith(("http://", "https://")):
        return None
    return {
        "title": title,
        "url": url,
        "query": query,
        "match_type": "protocols.io_search",
        "confidence": 80,
    }


def search_protocols_io(query: str) -> list[dict]:
    """
    Search protocols.io for protocol evidence, not material-property evidence.

    Endpoint details are intentionally isolated here so the API shape can be
    updated without touching ranking or portfolio logic.
    """
    query = " ".join(str(query or "").split())
    if not query:
        return []
    if query in _PROTOCOLS_IO_SEARCH_CACHE:
        return [dict(item) for item in _PROTOCOLS_IO_SEARCH_CACHE[query]]

    token = os.getenv("PROTOCOLS_IO_TOKEN") or os.getenv("PROTOCOLS_IO_API_KEY")
    if not token:
        _PROTOCOLS_IO_SEARCH_CACHE[query] = []
        return []

    base_url = os.getenv("PROTOCOLS_IO_BASE_URL", "https://www.protocols.io/api/v3").rstrip("/")
    url = f"{base_url}/protocols"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "filter": "public",
        "key": query,
        "order_field": "relevance",
        "order_dir": "desc",
        "page_size": 5,
        "page_id": 1,
        "fields": "title,name,url,uri,protocol_uri,public_url,html_url,id",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=8)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        _PROTOCOLS_IO_SEARCH_CACHE[query] = []
        return []

    raw_items = payload.get("items", []) if isinstance(payload, dict) else []
    matches: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_protocol_item(item, query)
        if normalized:
            matches.append(normalized)
        if len(matches) >= 3:
            break

    _PROTOCOLS_IO_SEARCH_CACHE[query] = matches
    return [dict(item) for item in matches]


def lookup_protocol_evidence(candidate: dict, spec: dict) -> dict:
    """Return real protocols.io protocol evidence when available."""
    queries = build_protocol_queries(candidate, spec)
    for query in queries:
        matches = search_protocols_io(query)
        if matches:
            confidence = max(int(match.get("confidence", 70) or 70) for match in matches)
            return {
                "protocol_evidence": matches,
                "protocol_confidence": min(90, max(70, confidence)),
                "protocol_note": f"Matched {len(matches)} public protocols.io protocol result(s) for query: {query}",
                "query": query,
            }

    return {
        "protocol_evidence": [],
        "protocol_confidence": 0,
        "protocol_note": "No matching public protocols.io protocol evidence found.",
        "query": queries[0] if queries else "",
    }


def attach_protocol_evidence_to_top3(portfolio: list[dict], spec: dict) -> list[dict]:
    """Attach protocol evidence/fallback source metadata to the top 3 items."""
    for entry in portfolio[:3]:
        lookup = lookup_protocol_evidence(entry, spec)
        matches = list(lookup.get("protocol_evidence", []) or [])
        entry["protocol_evidence"] = matches

        if matches:
            entry["protocol_confidence"] = int(lookup.get("protocol_confidence", 80) or 80)
            entry["protocol_note"] = str(lookup.get("protocol_note", "Matched public protocols.io evidence."))
            entry["recommended_experiment_source"] = "protocols.io"
            continue

        existence_status = str(entry.get("existence_status", "") or "")
        if existence_status == "FAMILY_OR_TEMPLATE":
            entry["protocol_confidence"] = 25
            entry["protocol_note"] = "Candidate is a family/template; using existing LLM or class-template experiment plan."
            entry["recommended_experiment_source"] = "class_template"
        elif existence_status == "VERIFIED_IN_DATABASE":
            entry["protocol_confidence"] = 45
            entry["protocol_note"] = "No matching public protocol found; using LLM-generated experiment plan for a Materials Project verified formula."
            entry["recommended_experiment_source"] = "llm_fallback_verified_formula"
        else:
            entry["protocol_confidence"] = 25
            entry["protocol_note"] = "No matching public protocol found; using LLM-generated experiment plan for an unverified or family-level candidate."
            entry["recommended_experiment_source"] = "llm_fallback_unverified_formula"
    return portfolio


def generate_lab_ready_portfolio(candidates: list[dict], spec: dict, memory: dict) -> dict:
    """Build ranked 2.0 portfolio with uncertainty and experiment plan."""
    def _material_class() -> str:
        target_props = dict((spec or {}).get("target_props", {}) or {})
        return str(target_props.get("material_class", "unknown") or "unknown").strip().lower()

    def _is_class_relevant(entry: dict, material_class: str) -> bool:
        formula = str(entry.get("candidate", entry.get("formula", ""))).strip().lower()
        family = str(entry.get("family", entry.get("material_family", ""))).strip().lower()
        band_gap = entry.get("band_gap")
        stability = float(entry.get("stability_above_hull", 1.0) or 1.0)
        metallic_tokens = {"fe", "ni", "co", "cu", "al"}
        coating_tokens = {"oxide", "nitride", "carbide", "ceramic", "tic", "sic", "al", "ti", "ta", "zn"}
        hts_tokens = {"carbide", "nitride", "boride", "silicide", "oxide", "refractory"}

        if material_class == "protective_coating":
            if formula in {"s", "s8", "ce"}:
                return False
            return any(token in formula or token in family for token in coating_tokens)
        if material_class == "semiconductor":
            if band_gap is not None:
                try:
                    if float(band_gap) <= 0:
                        return False
                except (TypeError, ValueError):
                    pass
            if formula in metallic_tokens and "/" not in formula:
                return False
            return True
        if material_class == "battery_material":
            if stability > 0.2:
                return False
            return any(token in family for token in ["oxide", "phosphate", "sulfide", "spinel", "layered", "olivine"])
        if material_class == "high_temperature_structural_material":
            return any(token in formula or token in family for token in hts_tokens)
        return True

    def _class_default_experiment(material_class: str) -> str:
        if material_class == "permanent_magnet":
            return "XRD phase identification + VSM/SQUID magnetic characterization after annealing and thermal demagnetization tests."
        if material_class == "protective_coating":
            return "EIS + salt spray + potentiodynamic polarization in 3.5% NaCl, with adhesion/scratch and SEM/XRD analysis."
        if material_class == "semiconductor":
            return "I-V/C-V with leakage characterization, radiation exposure, thermal cycling, and defect spectroscopy."
        if material_class == "battery_material":
            return "Coin-cell charge/discharge cycling + EIS + XRD before/after cycling with thermal safety screening."
        if material_class == "high_temperature_structural_material":
            return "Thermal cycling + oxidation testing + hardness/fatigue with TGA/DSC and XRD."
        return "XRD + SEM + relevant electrochemical/mechanical validation for practical screening."

    def _broaden_families_hint(material_class: str) -> str:
        mapping = {
            "permanent_magnet": "Mn-Al, Fe-N, ferrite and intermetallic magnet families",
            "protective_coating": "oxides, nitrides, carbides, ceramic and Zn/Al-rich coating systems",
            "semiconductor": "compound semiconductors and stable wide-band-gap materials",
            "battery_material": "oxide/phosphate/sulfide electrochemical host families",
            "high_temperature_structural_material": "carbides, nitrides, borides, silicides, refractory alloys",
        }
        return mapping.get(material_class, "class-relevant stable compound families")

    def _honest_no_candidate_payload(material_class: str, observed_candidates: list[dict] | None = None) -> dict:
        target_props = dict((spec or {}).get("target_props", {}) or {})
        banned = list((spec or {}).get("banned_elements", []) or [])
        reason = (
            f"No high-confidence candidate found for material class '{material_class}'. "
            f"Observed options either scored too low, failed post-check relevance, or remained too uncertain. "
            f"Suggested broadened search families: {_broaden_families_hint(material_class)}."
        )

        observed = [dict(item) for item in (observed_candidates or []) if isinstance(item, dict)]
        if observed:
            entries: list[dict] = []
            for idx, item in enumerate(observed[:3], start=1):
                formula = str(item.get("formula", item.get("candidate", f"Observed-{idx}")) or f"Observed-{idx}")
                family = str(item.get("material_family", item.get("family", "Unknown")) or "Unknown")
                overall = int(item.get("score", item.get("overall_score", 0)) or 0)
                stability = item.get("stability_above_hull")
                stability_text = "unknown"
                try:
                    if stability is not None:
                        stability_text = f"{float(stability):.3f} eV/atom"
                except (TypeError, ValueError):
                    stability_text = "unknown"
                supply_risk = item.get("supply_chain_risk")
                supply_text = "unknown"
                try:
                    if supply_risk is not None:
                        supply_text = f"{int(float(supply_risk))}%"
                except (TypeError, ValueError):
                    supply_text = "unknown"

                entries.append(
                    {
                        "rank": idx,
                        "candidate": formula,
                        "formula": formula,
                        "family": family,
                        "material_family": family,
                        "scores": {
                            "scientific_fit": max(0, min(100, overall)),
                            "stability": max(0, min(100, int(item.get("stability_score", 0) or 0))),
                            "supply_chain_safety": max(0, min(100, 100 - int(float(supply_risk or 100)))),
                            "manufacturability": max(0, min(100, int(item.get("manufacturability_score", 0) or 0))),
                            "evidence_confidence": max(0, min(100, int(item.get("evidence_confidence_score", 0) or 0))),
                            "overall": overall,
                        },
                        "overall_score": overall,
                        "scientific_fit_score": max(0, min(100, overall)),
                        "stability_score": max(0, min(100, int(item.get("stability_score", 0) or 0))),
                        "supply_chain_score": max(0, min(100, 100 - int(float(supply_risk or 100)))),
                        "manufacturability_score": max(0, min(100, int(item.get("manufacturability_score", 0) or 0))),
                        "evidence_confidence": max(0, min(100, int(item.get("evidence_confidence_score", 0) or 0))),
                        "main_uncertainty": (
                            f"Confidence remains low for deployment; stability={stability_text}, supply_chain_risk={supply_text}."
                        ),
                        "likely_failure_mode": (
                            "Insufficient confidence margin for TEST_FIRST selection under current hard constraints."
                        ),
                        "recommended_experiment": _class_default_experiment(material_class),
                        "rationale": (
                            "Returned as best observed option from retrieval, but not promoted because confidence/fit was insufficient."
                        ),
                        "status": "EXPLORE_LATER",
                        "eligible": bool(item.get("eligible", True)),
                        "mp_id": item.get("mp_id"),
                        "elements": item.get("elements"),
                        "band_gap": item.get("band_gap"),
                        "stability_above_hull": item.get("stability_above_hull"),
                        "supply_chain_risk": item.get("supply_chain_risk"),
                    }
                )

            test_queue = [
                f"{idx}. {entry['recommended_experiment']}"
                for idx, entry in enumerate(entries, start=1)
            ]
            return {
                "portfolio": entries,
                "test_queue": test_queue,
                "provenance_tree": {
                    "source": "criticalmat_agent_postcheck",
                    "notes": reason,
                    "constraints_snapshot": {
                        "material_class": material_class,
                        "exclude_radioactive": bool(target_props.get("exclude_radioactive", True)),
                        "require_solid_state": bool(target_props.get("require_solid_state", True)),
                        "banned_elements_sample": banned[:12],
                    },
                },
            }

        return {
            "portfolio": [
                {
                    "rank": 1,
                    "candidate": "No candidate selected",
                    "formula": "No candidate selected",
                    "family": "N/A",
                    "material_family": "N/A",
                    "scores": {
                        "scientific_fit": 0,
                        "stability": 0,
                        "supply_chain_safety": 0,
                        "manufacturability": 0,
                        "evidence_confidence": 0,
                        "overall": 0,
                    },
                    "overall_score": 0,
                    "scientific_fit_score": 0,
                    "stability_score": 0,
                    "supply_chain_score": 0,
                    "manufacturability_score": 0,
                    "evidence_confidence": 0,
                    "main_uncertainty": "No plausible class-relevant candidate was returned from retrieval after constraints.",
                    "likely_failure_mode": "Search space was too narrow or constraints were too strict for current data.",
                    "recommended_experiment": _class_default_experiment(material_class),
                    "rationale": reason,
                    "status": "EXPLORE_LATER",
                    "eligible": True,
                    "existence_status": "FAMILY_OR_TEMPLATE",
                    "verification_source": "none",
                    "verification_id": None,
                    "verification_note": "No exact candidate formula was available for Materials Project verification.",
                    "protocol_evidence": [],
                    "protocol_confidence": 25,
                    "protocol_note": "No matching public protocol found; using a class-template experiment plan.",
                    "recommended_experiment_source": "class_template",
                }
            ],
            "test_queue": [f"1. {_class_default_experiment(material_class)}"],
            "provenance_tree": {
                "source": "criticalmat_agent_postcheck",
                "notes": reason,
                "constraints_snapshot": {
                    "material_class": material_class,
                    "exclude_radioactive": bool(target_props.get("exclude_radioactive", True)),
                    "require_solid_state": bool(target_props.get("require_solid_state", True)),
                    "banned_elements_sample": banned[:12],
                },
            },
        }

    material_class = _material_class()
    eligible = [dict(c) for c in (candidates or []) if bool(c.get("eligible", True))]
    eligible.sort(key=lambda c: int(c.get("score", 0)), reverse=True)
    top = eligible[:5]
    prompt = lab_ready_portfolio_prompt(top, spec or {}, memory or {})

    def _fallback_portfolio() -> dict:
        fallback_entries = [
            {
                "rank": 1,
                "candidate": "Mn4Al9",
                "family": "Mn-Al",
                "scores": {
                    "scientific_fit": 88,
                    "stability": 79,
                    "supply_chain_safety": 100,
                    "manufacturability": 90,
                    "evidence_confidence": 90,
                    "overall": 89,
                },
                "main_uncertainty": "Phase stability of Mn-Al intermetallic ordering above 400C remains uncertain.",
                "likely_failure_mode": "Thermal exposure may reduce coercivity by phase decomposition.",
                "recommended_experiment": "XRD phase analysis post-anneal plus VSM coercivity/remanence characterization.",
                "status": "TEST_FIRST",
            },
            {
                "rank": 2,
                "candidate": str(top[1].get("formula", "Mn2O3")) if len(top) > 1 else "Mn2O3",
                "family": str(top[1].get("material_family", "Fe-O")) if len(top) > 1 else "Fe-O",
                "scores": {
                    "scientific_fit": int(top[1].get("scientific_fit_logic", 70)) if len(top) > 1 else 70,
                    "stability": int(top[1].get("stability_score", 62)) if len(top) > 1 else 62,
                    "supply_chain_safety": int(top[1].get("supply_chain_safety_score", 60)) if len(top) > 1 else 60,
                    "manufacturability": int(top[1].get("manufacturability_score", 80)) if len(top) > 1 else 80,
                    "evidence_confidence": int(top[1].get("evidence_confidence_score", 90)) if len(top) > 1 else 90,
                    "overall": int(top[1].get("score", 72)) if len(top) > 1 else 72,
                },
                "main_uncertainty": "Magnetic anisotropy and achievable coercivity under actuator-relevant processing are uncertain.",
                "likely_failure_mode": "Insufficient coercivity for guidance actuators despite acceptable stability.",
                "recommended_experiment": "SEM microstructure check and VSM loop measurement after controlled annealing.",
                "status": "BACKUP_TEST",
            },
            {
                "rank": 3,
                "candidate": "Fe",
                "family": "Fe-N",
                "scores": {
                    "scientific_fit": 45,
                    "stability": 95,
                    "supply_chain_safety": 85,
                    "manufacturability": 90,
                    "evidence_confidence": 75,
                    "overall": 76,
                },
                "main_uncertainty": "Pure Fe baseline may lack permanent-magnet coercivity without nitride/phase engineering.",
                "likely_failure_mode": "Low coercivity and remanence compared to actuator requirements.",
                "recommended_experiment": "SQUID/VSM baseline magnetic characterization to benchmark coercivity gap.",
                "status": "SAFE_FALLBACK",
            },
        ]
        return {
            "portfolio": fallback_entries,
            "test_queue": [
                "1. Arc melt Mn4Al9 precursors under argon - confirm phase by XRD",
                "2. VSM characterization of coercivity and remanence at room temperature",
                "3. Thermal stability test: anneal at 400C for 48h, then re-characterize",
            ],
            "provenance_tree": {
                "source": "criticalmat_agent_fallback",
                "notes": "Deterministic 2.0 fallback portfolio",
            },
        }

    try:
        raw = _call_model(prompt, temperature=0.25)
        parsed = _extract_json(raw)
        portfolio_payload = parsed if isinstance(parsed, dict) else {}
    except Exception as exc:
        print(f"[agent.py warning] Gemini portfolio generation failed. Using fallback. Reason: {exc}")
        portfolio_payload = _fallback_portfolio()

    entries = list((portfolio_payload or {}).get("portfolio", []) or [])
    if not entries:
        entries = _fallback_portfolio()["portfolio"]
    entries = sorted(entries, key=lambda entry: int(entry.get("rank", 999)))

    valid_status = {"TEST_FIRST", "BACKUP_TEST", "SAFE_FALLBACK", "EXPLORE_LATER", "INELIGIBLE"}
    normalized: list[dict] = []
    for idx, entry in enumerate(entries[:5], start=1):
        scores = dict(entry.get("scores", {}) or {})
        status = str(entry.get("status", "EXPLORE_LATER")).upper()
        if status not in valid_status:
            status = "EXPLORE_LATER"
        candidate_name = str(entry.get("candidate", entry.get("formula", f"Candidate-{idx}")))
        family = str(entry.get("family", entry.get("material_family", "Unknown")))
        scientific_fit = int(entry.get("scientific_fit_score", scores.get("scientific_fit", 0)) or 0)
        stability_score = int(entry.get("stability_score", scores.get("stability", 0)) or 0)
        supply_score = int(entry.get("supply_chain_score", scores.get("supply_chain_safety", 0)) or 0)
        manufacturability_score = int(entry.get("manufacturability_score", scores.get("manufacturability", 0)) or 0)
        evidence_confidence = int(entry.get("evidence_confidence", scores.get("evidence_confidence", 0)) or 0)
        overall = int(entry.get("overall_score", scores.get("overall", 0)) or 0)
        norm_entry = {
            "rank": int(entry.get("rank", idx) or idx),
            "candidate": candidate_name,
            "formula": str(entry.get("formula", candidate_name)),
            "family": family,
            "material_family": family,
            "scores": {
                "scientific_fit": scientific_fit,
                "stability": stability_score,
                "supply_chain_safety": supply_score,
                "manufacturability": manufacturability_score,
                "evidence_confidence": evidence_confidence,
                "overall": overall,
            },
            "overall_score": overall,
            "scientific_fit_score": scientific_fit,
            "stability_score": stability_score,
            "supply_chain_score": supply_score,
            "manufacturability_score": manufacturability_score,
            "evidence_confidence": evidence_confidence,
            "main_uncertainty": str(entry.get("main_uncertainty", "Material-specific uncertainty requires focused validation.")),
            "likely_failure_mode": str(entry.get("likely_failure_mode", "Performance decay under relevant operating conditions.")),
            "recommended_experiment": str(entry.get("recommended_experiment", _class_default_experiment(material_class))),
            "rationale": str(entry.get("rationale", "Ranked by class-aware scientific fit, stability, supply safety, and manufacturability.")),
            "status": status,
            "eligible": bool(entry.get("eligible", True)),
            "band_gap": entry.get("band_gap"),
            "stability_above_hull": entry.get("stability_above_hull"),
        }
        for source in top:
            if str(source.get("formula", "") or "").strip() == str(norm_entry.get("formula", "") or "").strip():
                for key in (
                    "magnetic_moment",
                    "total_magnetization",
                    "magnetization",
                    "magnetic_moment_total",
                    "supply_chain_risk",
                    "band_gap",
                    "stability_above_hull",
                    "elements",
                    "mp_id",
                ):
                    if norm_entry.get(key) is None and source.get(key) is not None:
                        norm_entry[key] = source.get(key)
                break
        if not norm_entry["eligible"] or status == "INELIGIBLE":
            continue
        if not _is_class_relevant(norm_entry, material_class):
            norm_entry["scores"]["overall"] = max(0, norm_entry["scores"]["overall"] - 35)
            norm_entry["overall_score"] = norm_entry["scores"]["overall"]
            norm_entry["status"] = "EXPLORE_LATER"
            norm_entry["rationale"] = (
                norm_entry["rationale"]
                + " Down-ranked during post-check because candidate appears weakly matched to target material class."
            )
        normalized.append(norm_entry)

    normalized = [entry for entry in normalized if bool(entry.get("eligible", True))]
    if not normalized:
        return _honest_no_candidate_payload(material_class, observed_candidates=top)

    normalized.sort(
        key=lambda row: row["scores"].get("overall", 0),
        reverse=True,
    )

    if not _is_class_relevant(normalized[0], material_class):
        return _honest_no_candidate_payload(material_class, observed_candidates=top)

    normalized = normalized[:5]
    if len(normalized) >= 3:
        normalized = normalized[:5]

    for idx, row in enumerate(normalized, start=1):
        row["rank"] = idx
        if idx == 1:
            row["status"] = "TEST_FIRST"
        elif idx == 2:
            row["status"] = "BACKUP_TEST"
        elif idx == 3:
            row["status"] = "SAFE_FALLBACK"
        else:
            row["status"] = "EXPLORE_LATER"

    verify_top3_formulas(normalized)
    attach_protocol_evidence_to_top3(normalized, spec or {})

    test_queue = list((portfolio_payload or {}).get("test_queue", []) or [])
    if not test_queue:
        test_queue = [
            f"{idx}. {entry['recommended_experiment']}"
            for idx, entry in enumerate(normalized[:3], start=1)
        ]

    return {
        "portfolio": normalized,
        "test_queue": [str(item) for item in test_queue],
        "provenance_tree": dict((portfolio_payload or {}).get("provenance_tree", {})),
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