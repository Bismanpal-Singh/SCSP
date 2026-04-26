"""Central policy profiles for scoring and eligibility.

This is intentionally declarative: material-class behavior is configured here
instead of being scattered across scorer/search/parser modules.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any


def _as_float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _as_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _as_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name, "1" if default else "0")
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class ClassPolicy:
    # Eligibility defaults
    exclude_radioactive: bool = True
    require_solid_state: bool = True
    require_practical_materials: bool = True
    require_manufacturable: bool = True
    avoid_toxic_elements: bool = True
    avoid_precious_metals: bool = False
    require_compound: bool = False

    # Thresholds
    max_stability_above_hull: float = 0.12
    min_magnetic_moment: float = 0.2
    max_element_count_practical: int = 6

    # Scoring weights (sum not required but recommended)
    w_scientific_fit: float = 0.30
    w_stability: float = 0.20
    w_supply_chain: float = 0.20
    w_manufacturability: float = 0.15
    w_evidence: float = 0.15

    # Family heuristic tuning (tie-break only)
    heuristic_weight: float = 0.45
    heuristic_cap: int = 10
    heuristic_margin: int = 8

    # Optional: family diversity target (used by selection/ranking)
    diversify: bool = True

    # Extra knobs
    mp_screen_fetch_limit: int = 100

    # P2 portfolio expectations
    portfolio_target_count: int = 5


DEFAULT_POLICIES: dict[str, ClassPolicy] = {
    "unknown": ClassPolicy(require_compound=False),
    "permanent_magnet": ClassPolicy(
        require_compound=True,
        min_magnetic_moment=0.2,
        max_stability_above_hull=0.12,
    ),
    "semiconductor": ClassPolicy(
        require_compound=True,
        max_stability_above_hull=0.18,
    ),
    "battery_material": ClassPolicy(
        require_compound=True,
        max_stability_above_hull=0.20,
    ),
    "protective_coating": ClassPolicy(
        require_compound=True,
        max_stability_above_hull=0.18,
    ),
    "high_temperature_structural_material": ClassPolicy(
        require_compound=True,
        max_stability_above_hull=0.20,
    ),
    "sensor_material": ClassPolicy(
        require_compound=True,
        max_stability_above_hull=0.18,
    ),
}


def get_policy(spec_or_target_props: dict[str, Any] | None) -> ClassPolicy:
    target_props = dict((spec_or_target_props or {}).get("target_props", spec_or_target_props) or {})
    material_class = str(target_props.get("material_class", "unknown") or "unknown").strip().lower()
    base = DEFAULT_POLICIES.get(material_class, DEFAULT_POLICIES["unknown"])

    # Allow per-run overrides coming from parser/spec.
    def _override_bool(name: str, current: bool) -> bool:
        if name in target_props:
            return bool(target_props.get(name))
        return current

    def _override_float(name: str, current: float) -> float:
        if name in target_props and target_props.get(name) is not None:
            try:
                return float(target_props.get(name))
            except (TypeError, ValueError):
                return current
        return current

    def _override_int(name: str, current: int) -> int:
        if name in target_props and target_props.get(name) is not None:
            try:
                return int(target_props.get(name))
            except (TypeError, ValueError):
                return current
        return current

    # Global env overrides (coarse tuning)
    env_prefix = "CRITICALMAT_POLICY_"
    heuristic_weight = _as_float_env(env_prefix + "HEURISTIC_WEIGHT", base.heuristic_weight)
    heuristic_cap = _as_int_env(env_prefix + "HEURISTIC_CAP", base.heuristic_cap)
    heuristic_margin = _as_int_env(env_prefix + "HEURISTIC_MARGIN", base.heuristic_margin)

    return ClassPolicy(
        exclude_radioactive=_override_bool("exclude_radioactive", base.exclude_radioactive),
        require_solid_state=_override_bool("require_solid_state", base.require_solid_state),
        require_practical_materials=_override_bool("require_practical_materials", base.require_practical_materials),
        require_manufacturable=_override_bool("require_manufacturable", base.require_manufacturable),
        avoid_toxic_elements=_override_bool("avoid_toxic_elements", base.avoid_toxic_elements),
        avoid_precious_metals=_override_bool("avoid_precious_metals", base.avoid_precious_metals),
        require_compound=_override_bool("require_compound", base.require_compound),
        max_stability_above_hull=_override_float("max_stability_above_hull", base.max_stability_above_hull),
        min_magnetic_moment=_override_float("min_magnetic_moment", base.min_magnetic_moment),
        max_element_count_practical=_override_int("max_element_count_practical", base.max_element_count_practical),
        w_scientific_fit=_override_float("w_scientific_fit", base.w_scientific_fit),
        w_stability=_override_float("w_stability", base.w_stability),
        w_supply_chain=_override_float("w_supply_chain", base.w_supply_chain),
        w_manufacturability=_override_float("w_manufacturability", base.w_manufacturability),
        w_evidence=_override_float("w_evidence", base.w_evidence),
        heuristic_weight=max(0.0, min(1.0, heuristic_weight)),
        heuristic_cap=max(0, heuristic_cap),
        heuristic_margin=max(0, heuristic_margin),
        diversify=_override_bool("diversify", base.diversify),
        mp_screen_fetch_limit=_override_int("mp_screen_fetch_limit", base.mp_screen_fetch_limit),
        portfolio_target_count=_override_int("portfolio_target_count", base.portfolio_target_count),
    )

