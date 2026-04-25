"""Materials Project retrieval and supply-chain filtering for P1 scope."""

from __future__ import annotations

import os
from typing import Any
import json
from urllib.parse import urlencode

from dotenv import load_dotenv
from mp_api.client import MPRester
import requests

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


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


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


def _normalize_candidate(doc: Any) -> dict:
    return {
        "formula": str(_doc_get(doc, "formula_pretty", "unknown")),
        "magnetic_moment": _extract_magnetic_moment(doc),
        "formation_energy": _to_float(_doc_get(doc, "formation_energy_per_atom", None), default=0.0),
        "stability_above_hull": _to_float(_doc_get(doc, "energy_above_hull", None), default=1.0),
        "band_gap": _to_float(_doc_get(doc, "band_gap", None), default=0.0),
        "elements": _extract_elements(doc),
        "mp_id": str(_doc_get(doc, "material_id", "unknown")),
    }


def _build_search_kwargs(
    allowed_elements: list[str],
    banned_elements: list[str],
    limit: int,
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
    return kwargs


def _query_mp_http(
    api_key: str,
    allowed_elements: list[str],
    banned_elements: list[str],
    limit: int,
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


def _rank_and_truncate(
    candidates: list[dict],
    target_props: dict | None,
    final_limit: int,
) -> list[dict]:
    """Preliminary full `score_candidate` on each row, sort desc, keep top `final_limit`."""
    if not candidates:
        return []
    spec = {"target_props": target_props or {}}
    ranked = sorted(
        candidates,
        key=lambda c: score_candidate(c, spec),
        reverse=True,
    )
    return ranked[: max(1, final_limit)]


def get_candidates(
    allowed_elements: list[str],
    banned_elements: list[str],
    target_props: dict,
    limit: int = 50,
) -> list[dict]:
    """Query Materials Project and return normalized candidate dicts."""
    load_dotenv()
    api_key = os.getenv("MP_API_KEY")
    if not api_key:
        raise RuntimeError("Missing MP_API_KEY in environment/.env")

    final_limit = max(1, limit)
    fetch_n = _screen_fetch_limit(target_props, final_limit)

    kwargs = _build_search_kwargs(allowed_elements, banned_elements, fetch_n)
    docs: list[Any]
    try:
        with MPRester(api_key) as mpr:
            try:
                docs = mpr.materials.summary.search(**kwargs)
            except TypeError:
                # Compatibility fallback for older/newer client argument handling.
                kwargs.pop("num_elements", None)
                docs = mpr.materials.summary.search(**kwargs)
    except Exception:
        # Python 3.13 currently has compatibility issues in parts of mp-api dependencies.
        docs = _query_mp_http(api_key, allowed_elements, banned_elements, fetch_n)

    normalized = [_normalize_candidate(doc) for doc in docs]

    # Fallback widening: if strict element-conjunction returns no hits, broaden search.
    if not normalized and allowed_elements:
        widen_n = min(SCREEN_FETCH_MAX, max(fetch_n * 2, 120))
        broadened_kwargs = _build_search_kwargs([], banned_elements, widen_n)
        try:
            with MPRester(api_key) as mpr:
                try:
                    broad_docs = mpr.materials.summary.search(**broadened_kwargs)
                except TypeError:
                    broadened_kwargs.pop("num_elements", None)
                    broad_docs = mpr.materials.summary.search(**broadened_kwargs)
        except Exception:
            broad_docs = _query_mp_http(api_key, [], banned_elements, widen_n)

        broad_norm = [_normalize_candidate(doc) for doc in broad_docs]
        allowed_set = {el for el in allowed_elements}
        normalized = [
            c for c in broad_norm if any(el in allowed_set for el in (c.get("elements", []) or []))
        ]

    enriched = apply_supply_chain_filter(normalized)
    return _rank_and_truncate(enriched, target_props, final_limit)
