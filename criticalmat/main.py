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
    best = result.get("best_candidate", {})

    print("\n=== Final Result ===")
    if not best:
        print("No viable candidate found.")
        return
    print(f"Formula: {best.get('formula')}")
    print(f"Score: {best.get('score')} / 100")
    print(f"Magnetic moment: {best.get('magnetic_moment')} μB")
    print(f"Supply chain risk: {best.get('supply_chain_risk', 'N/A')}% China dependency")
    print(f"Synthesis route: {best.get('synthesis_recommendation', 'N/A')}")


if __name__ == "__main__":
    main()
