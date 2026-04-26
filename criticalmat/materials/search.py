"""Materials Project retrieval, viability filtering, and risk enrichment for P1."""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from itertools import combinations
from typing import Any
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from mp_api.client import MPRester

from criticalmat.materials.scorer import score_candidate
from criticalmat.core.policy import get_policy

# Two-stage "virtual screening": fetch many MP summaries, rank locally, return top `limit`.
SCREEN_FETCH_DEFAULT = 100
SCREEN_FETCH_MAX = 500

CHINA_CONTROLLED_RISK: dict[str, int] = {
    "Nd": 95,
    "Dy": 95,
    "Tb": 90,
    "Ho": 85,
    "Pr": 85,
    "Eu": 80,
    "Gd": 75,
    "Co": 60,
}

RADIOACTIVE_TOXIC_ELEMENTS = {
    "Pu",
    "U",
    "Th",
    "Am",
    "Cm",
    "Np",
    "Ra",
    "Po",
}

# Single-element phases that are gaseous (or impractical as solids) near ambient conditions.
NON_SOLID_SINGLE_ELEMENTS = {"H", "He", "N", "O", "F", "Ne", "Cl", "Ar", "Kr", "Xe", "Rn"}

HEURISTIC_WEIGHT_DEFAULT = 0.45
HEURISTIC_CAP_DEFAULT = 10
HEURISTIC_MARGIN_DEFAULT = 8


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _to_int(value: Any, default: int) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _heuristic_tuning() -> tuple[float, int, int]:
    """Read ranking heuristic tuning from env with safe defaults."""
    weight = _to_float(os.getenv("CRITICALMAT_HEURISTIC_WEIGHT"), HEURISTIC_WEIGHT_DEFAULT)
    cap = _to_int(os.getenv("CRITICALMAT_HEURISTIC_CAP"), HEURISTIC_CAP_DEFAULT)
    margin = _to_int(os.getenv("CRITICALMAT_HEURISTIC_MARGIN"), HEURISTIC_MARGIN_DEFAULT)
    return (
        max(0.0, min(weight, 1.0)),
        max(0, cap),
        max(0, margin),
    )


def _doc_get(doc: Any, key: str, default: Any = None) -> Any:
    if isinstance(doc, dict):
        return doc.get(key, default)
    return getattr(doc, key, default)


def _extract_elements(doc: Any) -> list[str]:
    raw = _doc_get(doc, "elements", [])
    if raw is None:
        return []
    elements: list[str] = []
    for el in raw:
        symbol = getattr(el, "symbol", None)
        elements.append(str(symbol or el))
    return elements


def _extract_magnetic_moment(doc: Any) -> float:
    # MP fields can vary by endpoint/client version, so we check multiple names.
    keys = (
        "total_magnetization",
        "total_magnetization_normalized_formula_units",
        "total_magnetization_normalized_vol",
        "magnetic_moment",
    )
    for key in keys:
        value = _doc_get(doc, key, None)
        if value is not None:
            return _to_float(value, default=0.0)
    return 0.0


def _family_tag(elements: list[str]) -> str:
    e = set(elements)
    if {"Fe", "N"}.issubset(e):
        return "Fe-N"
    if {"Mn", "Al"}.issubset(e):
        return "Mn-Al"
    if "Fe" in e and "O" in e:
        return "Fe-O"
    if {"Fe", "Co"}.issubset(e):
        return "Fe-Co"
    if len(e) == 1:
        return "Elemental"
    return "Other"


def _normalize_candidate(doc: Any) -> dict:
    elements = _extract_elements(doc)
    is_radioactive = any(el in RADIOACTIVE_TOXIC_ELEMENTS for el in elements)
    is_single_element = len(set(elements)) <= 1
    is_solid_likely = not (is_single_element and any(el in NON_SOLID_SINGLE_ELEMENTS for el in elements))

    mp_id = str(_doc_get(doc, "material_id", "unknown"))
    family = _family_tag(elements)
    return {
        "formula": str(_doc_get(doc, "formula_pretty", "unknown")),
        "magnetic_moment": _extract_magnetic_moment(doc),
        "formation_energy": _to_float(_doc_get(doc, "formation_energy_per_atom", None), default=0.0),
        "stability_above_hull": _to_float(_doc_get(doc, "energy_above_hull", None), default=1.0),
        "band_gap": _to_float(_doc_get(doc, "band_gap", None), default=0.0),
        "elements": elements,
        "element_count": len(set(elements)),
        "mp_id": mp_id,
        "is_radioactive": is_radioactive,
        "is_solid_likely": is_solid_likely,
        "is_solid_state": is_solid_likely,
        "material_family": family,
        "raw_source_metadata": {
            "mp_id": mp_id,
            "structure_notes": "MP summary entry for virtual screening candidate.",
        },
    }


def _build_search_kwargs(
    allowed_elements: list[str],
    banned_elements: list[str],
    limit: int,
    chemsys: str | None = None,
) -> dict:
    fields = [
        "material_id",
        "formula_pretty",
        "elements",
        "formation_energy_per_atom",
        "energy_above_hull",
        "band_gap",
        "total_magnetization",
        "total_magnetization_normalized_formula_units",
        "total_magnetization_normalized_vol",
    ]
    kwargs: dict[str, Any] = {"fields": fields, "num_elements": (1, 8), "limit": max(1, limit)}
    if allowed_elements:
        kwargs["elements"] = allowed_elements
    if banned_elements:
        kwargs["exclude_elements"] = banned_elements
    if chemsys:
        kwargs["chemsys"] = chemsys
    return kwargs


def _filter_by_allowed_any(candidates: list[dict], allowed_elements: list[str]) -> list[dict]:
    if not allowed_elements:
        return candidates
    allowed_set = set(allowed_elements)
    filtered = [c for c in candidates if any(el in allowed_set for el in (c.get("elements", []) or []))]
    return filtered if filtered else candidates


def _query_mp_http(
    api_key: str,
    allowed_elements: list[str],
    banned_elements: list[str],
    limit: int,
    chemsys: str | None = None,
) -> list[dict]:
    """Fallback query path when mp-api client is incompatible."""
    fields = [
        "material_id",
        "formula_pretty",
        "elements",
        "formation_energy_per_atom",
        "energy_above_hull",
        "band_gap",
        "total_magnetization",
        "total_magnetization_normalized_formula_units",
        "total_magnetization_normalized_vol",
    ]
    params: dict[str, Any] = {"_fields": ",".join(fields), "_limit": max(1, limit)}
    if allowed_elements:
        params["elements"] = ",".join(allowed_elements)
    if banned_elements:
        params["exclude_elements"] = ",".join(banned_elements)
    if chemsys:
        params["chemsys"] = chemsys

    url = f"https://api.materialsproject.org/materials/summary/?{urlencode(params)}"
    response = requests.get(
        url,
        headers={"X-API-KEY": api_key, "accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    payload = json.loads(response.text)
    data = payload.get("data", [])
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _magnet_task(target_props: dict | None) -> bool:
    props = target_props or {}
    material_class = str(props.get("material_class", "")).lower()
    if "magnet" in material_class:
        return True
    return _to_bool(props.get("needs_magnetism", False))


def _material_class(target_props: dict | None) -> str:
    props = target_props or {}
    return str(props.get("material_class", "unknown") or "unknown").strip().lower()


def _is_pure_element(candidate: dict) -> bool:
    return len(set(candidate.get("elements", []) or [])) <= 1


def _normalize_family_token(text: str) -> str:
    token = str(text or "").strip().lower().replace("_", "-")
    alias_map = {
        "mn al": "mn-al",
        "mnal": "mn-al",
        "mn-al-c": "mn-al-c",
        "mn al c": "mn-al-c",
        "fe n": "fe-n",
        "iron nitride": "fe-n",
        "ferrites": "ferrite",
        "oxides": "oxide",
        "sulfides": "sulfide",
        "phosphates": "phosphate",
    }
    return alias_map.get(token, token)


def _normalize_formula_token(text: str) -> str:
    subscript_digits = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
    normalized = str(text or "").translate(subscript_digits).strip().lower()
    return re.sub(r"[^a-z0-9]", "", normalized)


def _family_constraints_allow(candidate: dict, target_props: dict | None) -> bool:
    props = target_props or {}
    include_families = [_normalize_family_token(x) for x in (props.get("include_families", []) or [])]
    exclude_families = [_normalize_family_token(x) for x in (props.get("exclude_families", []) or [])]
    exclude_formulas = [_normalize_formula_token(x) for x in (props.get("exclude_formulas", []) or [])]
    family = _normalize_family_token(str(candidate.get("material_family", "") or ""))
    formula = _normalize_family_token(str(candidate.get("formula", "") or ""))
    formula_plain = _normalize_formula_token(str(candidate.get("formula", "") or ""))

    if exclude_families and any(token and (token in family or token in formula) for token in exclude_families):
        return False
    if exclude_formulas and any(token and token == formula_plain for token in exclude_formulas):
        return False
    if include_families:
        return any(token and (token in family or token in formula) for token in include_families)
    return True


def _is_class_relevant_candidate(candidate: dict, target_props: dict | None) -> bool:
    if not _family_constraints_allow(candidate, target_props):
        return False

    material_class = _material_class(target_props)
    elements = set(candidate.get("elements", []) or [])
    formula = str(candidate.get("formula", "") or "").lower()
    family = str(candidate.get("material_family", "") or "").lower()
    band_gap = _to_float(candidate.get("band_gap", 0.0), 0.0)
    is_pure = _is_pure_element(candidate)

    if material_class == "semiconductor":
        if is_pure and not elements.intersection({"C", "Si", "Ge"}):
            return False
        return band_gap > 0.0

    if material_class == "battery_material":
        if is_pure:
            return False
        family_ok = any(
            token in formula or token in family
            for token in ("li", "na", "mn", "fe", "po4", "oxide", "phosphate", "sulfide")
        )
        return family_ok

    if material_class == "protective_coating":
        if is_pure or formula in {"s", "s8", "ce"}:
            return False
        if elements.intersection({"O", "N", "C"}) and len(elements) >= 2:
            return True
        return any(
            token in formula or token in family
            for token in ("oxide", "nitride", "carbide", "ceramic", "sic", "tio", "al", "ta", "zn")
        )

    if material_class == "high_temperature_structural_material":
        if is_pure:
            return False
        return any(
            token in formula or token in family
            for token in ("carbide", "nitride", "boride", "silicide", "oxide", "refractory", "c", "n", "b", "si", "o")
        )

    if material_class == "permanent_magnet":
        # Pure Fe is useful as a baseline, but compounds/alloys should outrank it.
        return True

    return True


def _practicality_rules(target_props: dict | None) -> dict[str, float]:
    props = target_props or {}
    policy = get_policy({"target_props": props})
    return {
        "max_stability_above_hull": _to_float(props.get("max_stability_above_hull", policy.max_stability_above_hull), default=float(policy.max_stability_above_hull)),
        "min_magnetic_moment": _to_float(props.get("min_magnetic_moment", policy.min_magnetic_moment), default=float(policy.min_magnetic_moment)),
        "max_element_count_practical": float(getattr(policy, "max_element_count_practical", 6)),
    }


def apply_supply_chain_filter(candidates: list[dict]) -> list[dict]:
    """Add deterministic `supply_chain_risk` (0-100) for each candidate."""
    filtered: list[dict] = []
    for candidate in candidates:
        elements = candidate.get("elements", []) or []
        risky = [CHINA_CONTROLLED_RISK.get(el, 0) for el in elements]
        if risky:
            # Max risky element dominates, with a small bump for multiple risky elements.
            risk_score = min(100, max(risky) + 8 * max(0, len([r for r in risky if r > 0]) - 1))
        else:
            risk_score = 0
        enriched = dict(candidate)
        enriched["supply_chain_risk"] = int(risk_score)
        filtered.append(enriched)
    return filtered


def _apply_viability_filters(candidates: list[dict], target_props: dict | None) -> list[dict]:
    props = target_props or {}
    if not candidates:
        return []

    is_magnet_task = _magnet_task(props)
    material_class = _material_class(props)
    policy = get_policy({"target_props": props})
    require_solid_state = _to_bool(props.get("require_solid_state", policy.require_solid_state), default=bool(policy.require_solid_state))
    exclude_radioactive = _to_bool(props.get("exclude_radioactive", policy.exclude_radioactive), default=bool(policy.exclude_radioactive))
    require_practical_materials = _to_bool(props.get("require_practical_materials", policy.require_practical_materials), default=bool(policy.require_practical_materials))
    require_compound = _to_bool(props.get("require_compound", is_magnet_task), default=is_magnet_task)
    rules = _practicality_rules(props)

    filtered: list[dict] = []
    for candidate in candidates:
        elements = set(candidate.get("elements", []) or [])
        if exclude_radioactive and candidate.get("is_radioactive", False):
            continue
        if require_solid_state and not candidate.get("is_solid_likely", True):
            continue
        if (require_compound or material_class in {"battery_material", "protective_coating", "high_temperature_structural_material"}) and len(elements) < 2:
            continue
        if not _is_class_relevant_candidate(candidate, props):
            continue
        if is_magnet_task and _to_float(candidate.get("magnetic_moment", 0.0), 0.0) < rules["min_magnetic_moment"]:
            continue
        if _to_float(candidate.get("stability_above_hull", 1.0), 1.0) > rules["max_stability_above_hull"]:
            continue

        enriched = dict(candidate)
        if require_practical_materials and len(elements) > 6:
            continue
        enriched["is_practical"] = True
        filtered.append(enriched)

    if material_class in {"semiconductor", "battery_material", "protective_coating", "high_temperature_structural_material"}:
        return filtered
    # Do not return empty for broad/general tasks unless truly nothing passed; keep caller resilient.
    return filtered if filtered else candidates


def _screen_fetch_limit(target_props: dict | None, final_limit: int) -> int:
    """How many MP rows to pull before local rank-and-truncate (default 100, capped)."""
    final_limit = max(1, final_limit)
    props = target_props or {}
    policy = get_policy({"target_props": props})
    raw = props.get("mp_screen_fetch_limit", int(policy.mp_screen_fetch_limit))
    try:
        cap = int(raw)
    except (TypeError, ValueError):
        cap = SCREEN_FETCH_DEFAULT
    cap = max(final_limit, min(cap, SCREEN_FETCH_MAX))
    return cap


def _rank_candidates(candidates: list[dict], target_props: dict | None) -> list[dict]:
    if not candidates:
        return []
    props = target_props or {}
    spec = {"target_props": props}
    material_class = _material_class(props)
    preferred = [str(f).strip().lower().replace("_", "-") for f in (props.get("preferred_families", []) or [])]
    policy = get_policy({"target_props": props})
    heuristic_weight = float(policy.heuristic_weight)
    heuristic_cap = int(policy.heuristic_cap)
    heuristic_margin = int(policy.heuristic_margin)
    base_scores = [int(score_candidate(dict(candidate), spec)) for candidate in candidates]
    top_base_score = max(base_scores) if base_scores else 0
    ranked = []
    for candidate, base_score in zip(candidates, base_scores):
        enriched = dict(candidate)
        family_tag = str(enriched.get("material_family", "")).lower().replace("_", "-")
        formula = str(enriched.get("formula", "") or "").lower()
        family_bonus = 0
        if preferred:
            if family_tag in preferred:
                # Earlier preferred families get slightly higher boost.
                family_bonus = max(4, 10 - 2 * preferred.index(family_tag))
            elif family_tag == "elemental":
                family_bonus = -8
        if _is_pure_element(enriched):
            if material_class in {"semiconductor", "battery_material", "protective_coating", "high_temperature_structural_material"}:
                family_bonus -= 45
            elif material_class == "permanent_magnet":
                family_bonus -= 15
        if material_class == "semiconductor":
            band_gap = _to_float(enriched.get("band_gap", 0.0), 0.0)
            if band_gap > 0:
                family_bonus += 25
            else:
                family_bonus -= 60
            if any(token in formula for token in ("sic", "aln", "bn", "zno", "tio2", "c")):
                family_bonus += 15
        elif material_class == "battery_material":
            if any(token in formula for token in ("lifepo4", "nafepo4", "mn", "po4", "li", "na")):
                family_bonus += 20
        elif material_class == "protective_coating":
            if any(token in formula or token in family_tag for token in ("sic", "tio", "al", "ta", "zn", "oxide", "nitride", "carbide")):
                family_bonus += 20
        # Keep heuristics as a controlled tie-break, not a dominant score driver.
        if (top_base_score - base_score) <= heuristic_margin:
            scaled_bonus = int(round(family_bonus * heuristic_weight))
            if heuristic_cap > 0:
                scaled_bonus = max(-heuristic_cap, min(heuristic_cap, scaled_bonus))
        else:
            scaled_bonus = 0

        enriched["base_score"] = base_score
        enriched["heuristic_bonus"] = scaled_bonus
        enriched["prelim_score"] = base_score + scaled_bonus
        ranked.append(enriched)
    ranked.sort(key=lambda c: c.get("prelim_score", 0), reverse=True)
    return ranked


def _diversify_candidates(candidates: list[dict], final_limit: int) -> list[dict]:
    """Prefer family diversity before filling remainder from score order."""
    if not candidates:
        return []

    buckets: dict[str, list[dict]] = defaultdict(list)
    for candidate in candidates:
        family = str(candidate.get("material_family", "Other"))
        buckets[family].append(candidate)

    # Stable order by best score per family.
    families = sorted(
        buckets.keys(),
        key=lambda fam: buckets[fam][0].get("prelim_score", 0),
        reverse=True,
    )

    diversified: list[dict] = []
    seen_mp_ids: set[str] = set()
    while len(diversified) < final_limit:
        progressed = False
        for family in families:
            if not buckets[family]:
                continue
            candidate = buckets[family].pop(0)
            mp_id = str(candidate.get("mp_id", ""))
            if mp_id in seen_mp_ids:
                continue
            seen_mp_ids.add(mp_id)
            diversified.append(candidate)
            progressed = True
            if len(diversified) >= final_limit:
                break
        if not progressed:
            break
    return diversified[: max(1, final_limit)]


def _set_practicality_flag(candidates: list[dict], target_props: dict | None) -> list[dict]:
    rules = _practicality_rules(target_props)
    is_magnet_task = _magnet_task(target_props)
    marked: list[dict] = []
    for candidate in candidates:
        practical = (
            not candidate.get("is_radioactive", False)
            and candidate.get("is_solid_state", True)
            and _to_float(candidate.get("stability_above_hull", 1.0), 1.0) <= rules["max_stability_above_hull"]
        )
        if is_magnet_task:
            practical = practical and (
                _to_float(candidate.get("magnetic_moment", 0.0), 0.0) >= rules["min_magnetic_moment"]
            )
        enriched = dict(candidate)
        enriched["is_practical"] = bool(practical)
        marked.append(enriched)
    return marked


def apply_hard_filters(candidates: list[dict], spec: dict) -> tuple[list[dict], list[dict]]:
    """Apply hard eligibility filters and split into eligible/ineligible lists."""
    eligible_candidates: list[dict] = []
    ineligible_candidates: list[dict] = []
    radioactive_elements = {"U", "Th", "Ra", "Po", "Ac", "Pa"}

    target_props = dict((spec or {}).get("target_props", {}) or {})
    material_class = _material_class(target_props)
    banned_elements = set((spec or {}).get("banned_elements", []) or [])
    excluded_formula_tokens = {
        _normalize_formula_token(item)
        for item in (target_props.get("exclude_formulas", []) or [])
        if _normalize_formula_token(item)
    }
    exclude_radioactive = bool(
        (spec or {}).get("exclude_radioactive", target_props.get("exclude_radioactive", True))
    )
    require_solid_state = bool(
        (spec or {}).get("require_solid_state", target_props.get("require_solid_state", True))
    )

    for candidate in candidates or []:
        enriched = dict(candidate)
        elements = set(enriched.get("elements", []) or [])
        formula_token = _normalize_formula_token(enriched.get("formula", ""))
        reasons: list[str] = []

        banned_overlap = sorted(elements & banned_elements)
        if banned_overlap:
            reasons.append(f"Contains banned element: {', '.join(banned_overlap)}")
        if excluded_formula_tokens and formula_token in excluded_formula_tokens:
            reasons.append("Matches an explicitly excluded previous winner")

        radioactive_overlap = sorted(elements & radioactive_elements)
        if exclude_radioactive and radioactive_overlap:
            reasons.append(f"Contains radioactive element: {', '.join(radioactive_overlap)}")

        if require_solid_state and not bool(enriched.get("is_solid_state", True)):
            reasons.append("Not solid-state material")
        if material_class in {"semiconductor", "battery_material", "protective_coating", "high_temperature_structural_material"}:
            if not _is_class_relevant_candidate(enriched, target_props):
                reasons.append(f"Not a plausible {material_class} candidate")

        if reasons:
            enriched["eligible"] = False
            enriched["status"] = "INELIGIBLE"
            enriched["reason"] = "; ".join(reasons)
            ineligible_candidates.append(enriched)
        else:
            enriched["eligible"] = True
            enriched["status"] = "ELIGIBLE"
            eligible_candidates.append(enriched)

    return eligible_candidates, ineligible_candidates


def _fetch_docs(api_key: str, allowed_elements: list[str], banned_elements: list[str], fetch_n: int) -> list[Any]:
    kwargs = _build_search_kwargs(allowed_elements, banned_elements, fetch_n)
    try:
        with MPRester(api_key) as mpr:
            try:
                return list(mpr.materials.summary.search(**kwargs))
            except TypeError:
                kwargs.pop("num_elements", None)
                return list(mpr.materials.summary.search(**kwargs))
    except Exception:
        # Python 3.13 currently has compatibility issues in parts of mp-api dependencies.
        return _query_mp_http(api_key, allowed_elements, banned_elements, fetch_n)


def _fetch_docs_by_chemsys(
    api_key: str,
    allowed_elements: list[str],
    banned_elements: list[str],
    total_limit: int,
) -> list[Any]:
    """Fetch compound-focused rows via pairwise chemsys (e.g., Fe-O, Fe-N)."""
    elems = sorted(set(allowed_elements))
    if len(elems) < 2:
        return []
    pairs = ["-".join(pair) for pair in combinations(elems, 2)]
    if not pairs:
        return []

    per_pair = max(8, min(25, total_limit // max(1, len(pairs[:10]))))
    docs: list[Any] = []
    seen_ids: set[str] = set()
    for chemsys in pairs[:10]:
        try:
            kwargs = _build_search_kwargs([], banned_elements, per_pair, chemsys=chemsys)
            with MPRester(api_key) as mpr:
                try:
                    batch = list(mpr.materials.summary.search(**kwargs))
                except TypeError:
                    kwargs.pop("num_elements", None)
                    batch = list(mpr.materials.summary.search(**kwargs))
        except Exception:
            batch = _query_mp_http(
                api_key,
                [],
                banned_elements,
                per_pair,
                chemsys=chemsys,
            )

        for doc in batch:
            material_id = str(_doc_get(doc, "material_id", ""))
            if material_id in seen_ids:
                continue
            seen_ids.add(material_id)
            docs.append(doc)
            if len(docs) >= total_limit:
                return docs
    return docs


def get_candidates(
    allowed_elements: list[str],
    banned_elements: list[str],
    target_props: dict,
    limit: int = 50,
) -> list[dict]:
    """Query Materials Project and return practical, enriched candidate dicts."""
    load_dotenv()
    api_key = os.getenv("MP_API_KEY")
    if not api_key:
        raise RuntimeError("Missing MP_API_KEY in environment/.env")

    final_limit = max(1, limit)
    fetch_n = _screen_fetch_limit(target_props, final_limit)

    # MP `elements` behaves as a conjunction; for long allowed lists we query broadly,
    # then apply a local "contains any allowed element" filter.
    primary_allowed = allowed_elements if len(allowed_elements) <= 2 else []
    docs = _fetch_docs(api_key, primary_allowed, banned_elements, fetch_n)
    if _magnet_task(target_props) and len(allowed_elements) >= 2:
        docs = docs + _fetch_docs_by_chemsys(api_key, allowed_elements, banned_elements, fetch_n)
    normalized = [_normalize_candidate(doc) for doc in docs]
    normalized = _filter_by_allowed_any(normalized, allowed_elements)

    # For magnet tasks, widen once if we still have no multi-element chemistry.
    if _magnet_task(target_props) and not any(len(set(c.get("elements", []) or [])) > 1 for c in normalized):
        widen_n = min(SCREEN_FETCH_MAX, max(fetch_n * 2, 160))
        broad_docs = _fetch_docs(api_key, [], banned_elements, widen_n)
        broad_norm = _filter_by_allowed_any([_normalize_candidate(doc) for doc in broad_docs], allowed_elements)
        normalized = broad_norm if broad_norm else normalized

    # Fallback widening: if strict element-conjunction returns no hits, broaden search.
    if not normalized and allowed_elements:
        widen_n = min(SCREEN_FETCH_MAX, max(fetch_n * 2, 120))
        broad_docs = _fetch_docs(api_key, [], banned_elements, widen_n)
        broad_norm = [_normalize_candidate(doc) for doc in broad_docs]
        allowed_set = {el for el in allowed_elements}
        normalized = [
            c for c in broad_norm if any(el in allowed_set for el in (c.get("elements", []) or []))
        ]

    viable = _apply_viability_filters(normalized, target_props)
    enriched = apply_supply_chain_filter(viable)
    ranked = _rank_candidates(enriched, target_props)
    diversified = _diversify_candidates(ranked, final_limit)
    return _set_practicality_flag(diversified, target_props)
