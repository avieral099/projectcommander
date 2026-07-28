from __future__ import annotations

import argparse
import os
import time
from typing import Any

from commander_evidence_fusion import generate_fusion


WIDTH = 104


def _clear() -> None:
    os.system("clear")


def _line(name: str, evidence: dict[str, Any]) -> None:
    print(
        f"{name:<10} "
        f"STATUS {evidence.get('status', 'UNKNOWN'):<14} "
        f"SIDE {evidence.get('side', 'UNKNOWN'):<8} "
        f"SCORE {float(evidence.get('score', 0)):>6.2f} "
        f"STATE {evidence.get('state', evidence.get('regime', 'UNKNOWN'))}"
    )


def render(result: dict[str, Any]) -> None:
    _clear()

    print("=" * WIDTH)
    print("OPERATION COMMANDER — EVIDENCE FUSION".center(WIDTH))
    print("=" * WIDTH)
    print(
        f"UPDATED {result.get('generated_at')} | "
        f"UNIVERSE {result.get('universe')}"
    )
    print("-" * WIDTH)

    _line("MARKET", result.get("market", {}))
    _line("PREMIUM", result.get("premium", {}))
    _line("DRIVERS", result.get("drivers", {}))

    print("-" * WIDTH)
    print(
        f"FUSED SIDE     {result.get('fused_side'):<12} "
        f"COMBINED SCORE {float(result.get('combined_score', 0)):>6.2f}/100"
    )
    print(
        f"AGREEMENT      {result.get('agreement_votes')} votes     "
        f"CONTEXT        {result.get('context')}"
    )
    print(
        f"EXECUTION ALLOWED : {result.get('execution_allowed')}"
    )

    print("\nMISSING EVIDENCE")
    print("-" * WIDTH)
    missing = result.get("missing_evidence", [])
    print(", ".join(missing) if missing else "None")

    print("\nBLOCKERS")
    print("-" * WIDTH)
    blockers = result.get("blockers", [])
    if blockers:
        for blocker in blockers:
            print(f"- {blocker}")
    else:
        print("No blocker.")

    print("-" * WIDTH)
    print(result.get("note"))
    print("=" * WIDTH)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision", default="commander_decision_snapshot.json")
    parser.add_argument("--health", default="market_health_snapshot.json")
    parser.add_argument("--premium", default="premium_evidence_snapshot.json")
    parser.add_argument("--drivers", default="driver_evidence_snapshot.json")
    parser.add_argument("--output", default="commander_fused_evidence_snapshot.json")
    parser.add_argument("--refresh", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    while True:
        try:
            result = generate_fusion(
                args.decision,
                args.health,
                args.premium,
                args.drivers,
                args.output,
            )
            render(result)
        except Exception as error:
            _clear()
            print(f"EVIDENCE FUSION ERROR: {error}")

        if args.once:
            break

        time.sleep(max(1, args.refresh))


if __name__ == "__main__":
    main()
