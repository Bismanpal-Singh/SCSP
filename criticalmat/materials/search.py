"""Materials Project retrieval, viability filtering, and risk enrichment for P1."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from itertools import combinations
from typing import Any
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from mp_api.client import MPRester

from criticalmat.materials.scorer import score_candidate

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
        return "fe_n"
    if {"Mn", "Al"}.issubset(e):
        return "mn_al"
    if "Fe" in e and "O" in e:
        return "ferrite"
    if {"Fe", "Co"}.issubset(e):
        return "fe_co"
    if len(e) == 1:
        return "elemental"
    return "other_alloy_or_compound"


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
        "is_solid_state_flag": is_solid_likely,
        "family_tag": family,
        "material_family_tag": family,
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


def _practicality_rules(target_props: dict | None) -> dict[str, float]:
    props = target_props or {}
    return {
        "max_stability_above_hull": _to_float(props.get("max_stability_above_hull", 0.12), default=0.12),
        "min_magnetic_moment": _to_float(props.get("min_magnetic_moment", 0.2), default=0.2),
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
            risk_score = 5
        enriched = dict(candidate)
        enriched["supply_chain_risk"] = int(risk_score)
        filtered.append(enriched)
    return filtered


def _apply_viability_filters(candidates: list[dict], target_props: dict | None) -> list[dict]:
    props = target_props or {}
    if not candidates:
        return []

    is_magnet_task = _magnet_task(props)
    require_solid_state = _to_bool(props.get("require_solid_state", True), default=True)
    exclude_radioactive = _to_bool(props.get("exclude_radioactive", True), default=True)
    require_practical_materials = _to_bool(props.get("require_practical_materials", True), default=True)
    require_compound = _to_bool(props.get("require_compound", is_magnet_task), default=is_magnet_task)
    rules = _practicality_rules(props)

    filtered: list[dict] = []
    for candidate in candidates:
        elements = set(candidate.get("elements", []) or [])
        if exclude_radioactive and candidate.get("is_radioactive", False):
            continue
        if require_solid_state and not candidate.get("is_solid_likely", True):
            continue
        if require_compound and len(elements) < 2:
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

    # Do not return empty unless truly nothing passed; keep caller resilient.
    return filtered if filtered else candidates


def _screen_fetch_limit(target_props: dict | None, final_limit: int) -> int:
    """How many MP rows to pull before local rank-and-truncate (default 100, capped)."""
    final_limit = max(1, final_limit)
    props = target_props or {}
    raw = props.get("mp_screen_fetch_limit", SCREEN_FETCH_DEFAULT)
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
    preferred = [str(f).strip().lower() for f in (props.get("preferred_families", []) or [])]
    ranked = []
    for candidate in candidates:
        enriched = dict(candidate)
        base_score = score_candidate(enriched, spec)
        family_tag = str(enriched.get("family_tag", "")).lower()
        family_bonus = 0
        if preferred:
            if family_tag in preferred:
                # Earlier preferred families get slightly higher boost.
                family_bonus = max(4, 10 - 2 * preferred.index(family_tag))
            elif family_tag == "elemental":
                family_bonus = -8
        enriched["prelim_score"] = base_score + family_bonus
        ranked.append(enriched)
    ranked.sort(key=lambda c: c.get("prelim_score", 0), reverse=True)
    return ranked


def _diversify_candidates(candidates: list[dict], final_limit: int) -> list[dict]:
    """Prefer family diversity before filling remainder from score order."""
    if not candidates:
        return []

    buckets: dict[str, list[dict]] = defaultdict(list)
    for candidate in candidates:
        family = str(candidate.get("family_tag", "other_alloy_or_compound"))
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
            and candidate.get("is_solid_likely", True)
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
