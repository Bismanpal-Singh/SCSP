"""CLI entry point for CriticalMat mock loop."""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from .core.loop import run_agent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CriticalMat autonomous loop")
    parser.add_argument(
        "--hypothesis",
        type=str,
        default=None,
        help="Initial plain-English hypothesis. If omitted, prompt interactively.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum loop iterations.",
    )
    parser.add_argument(
        "--mock-p1",
        action="store_true",
        help="Use mock P1 candidate retrieval/scoring instead of real P1 modules.",
    )
    parser.add_argument(
        "--real-p2",
        action="store_true",
        help="Force real P2 functions (default behavior already tries real P2 with safe fallback).",
    )
    parser.add_argument(
        "--mock-p2",
        action="store_true",
        help="Use mock P2 reasoning functions only.",
    )
    parser.add_argument(
        "--strict-real",
        action="store_true",
        help="Disable all mock fallbacks; fail fast if real P1/P2 paths fail.",
    )
    return parser


def _material_class_from_result(result: dict) -> str:
    constraints = dict(result.get("constraints", {}) or {})
    target_props = dict(constraints.get("target_props", {}) or {})
    return str(target_props.get("material_class", "unknown") or "unknown").strip().lower()


def _print_final_summary(result: dict) -> None:
    best = result.get("best_candidate", {})
    material_class = _material_class_from_result(result)

    print("\n=== Final Result ===")
    if not best:
        print("No viable candidate found.")
        return

    print(f"Formula: {best.get('formula', best.get('candidate', 'N/A'))}")
    print(f"Score: {best.get('score', best.get('overall_score', 'N/A'))} / 100")

    stability = best.get("stability_above_hull")
    if stability is None:
        stability = "N/A"
    else:
        stability = f"{float(stability):.3f} eV/atom"

    supply = best.get("supply_chain_risk", best.get("supply_chain_score", "N/A"))
    experiment = best.get("recommended_experiment") or best.get("synthesis_recommendation") or "N/A"

    if material_class == "permanent_magnet":
        print(f"Magnetic moment: {best.get('magnetic_moment', 'N/A')} μB")
        print(f"Supply chain risk: {supply}% China dependency")
        print(f"Synthesis route: {experiment}")
    elif material_class == "semiconductor":
        print(f"Band gap: {best.get('band_gap', 'N/A')} eV")
        print(f"Stability: {stability}")
        print(f"Radiation/electrical test: {experiment}")
    elif material_class == "protective_coating":
        print(f"Coating relevance: {best.get('material_family', best.get('family', 'N/A'))}")
        print(f"Stability: {stability}")
        print(f"Corrosion test: {experiment}")
    elif material_class == "battery_material":
        print(f"Stability: {stability}")
        print(f"Supply chain risk: {supply}")
        print(f"Cycling/electrochemical test: {experiment}")
    elif material_class == "high_temperature_structural_material":
        print(f"Thermal/stability proxy: {stability}")
        print(f"Oxidation/mechanical test: {experiment}")
    else:
        print(f"Stability: {stability}")
        print(f"Supply chain risk: {supply}")
        print(f"Recommended experiment: {experiment}")


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    hypothesis = args.hypothesis
    if not hypothesis:
        hypothesis = input("Enter hypothesis: ").strip()
    if not hypothesis:
        hypothesis = "Find a permanent magnet for missile guidance systems without neodymium."

    result = run_agent(
        hypothesis,
        max_iterations=args.max_iterations,
        use_real_p1=not args.mock_p1,
        use_real_p2=(args.real_p2 or not args.mock_p2),
        allow_mock_fallback=not args.strict_real,
    )
    _print_final_summary(result)


if __name__ == "__main__":
    main()
