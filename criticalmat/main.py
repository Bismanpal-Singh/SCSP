"""CLI entry point for CriticalMat mock loop."""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from .loop import run_agent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CriticalMat autonomous loop")
    parser.add_argument(
        "--hypothesis",
        type=str,
        default="Find a permanent magnet for missile guidance systems without neodymium.",
        help="Initial plain-English hypothesis.",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=5,
        help="Maximum loop iterations.",
    )
    return parser


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    result = run_agent(args.hypothesis, max_iterations=args.max_iterations)
    best = result.get("best_candidate", {})

    print("\n=== Final Result ===")
    if not best:
        print("No viable candidate found.")
        return
    print(
        f"Best candidate: {best.get('formula')} | "
        f"Score: {best.get('score')} | "
        f"Magnetic moment: {best.get('magnetic_moment')}"
    )


if __name__ == "__main__":
    main()
