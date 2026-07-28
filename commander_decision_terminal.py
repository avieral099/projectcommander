from __future__ import annotations

import argparse
import os
import time
from typing import Any

from commander_decision_engine import generate_decision


WIDTH = 100


def _clear() -> None:
    os.system("clear")


def render(decision: dict[str, Any]) -> None:
    _clear()

    print("=" * WIDTH)
    print("OPERATION COMMANDER — DECISION CONTEXT".center(WIDTH))
    print("=" * WIDTH)
    print(
        f"UPDATED {decision.get('generated_at')} | "
        f"UNIVERSE {decision.get('universe')} | "
        f"SCANNED {decision.get('scanned')}/{decision.get('total')}"
    )
    print("-" * WIDTH)
    print(
        f"REGIME      {decision.get('regime'):<22}"
        f"CONFIDENCE  {float(decision.get('confidence', 0)):>6.2f}/100"
    )
    print(
        f"QUALITY     {decision.get('quality'):<22}"
        f"RISK        {decision.get('risk')}"
    )
    print(
        f"MARKET SIDE {decision.get('directional_side'):<21}"
        f"ACTION      {decision.get('market_action')}"
    )
    print("-" * WIDTH)
    print(
        f"BULL SCORE  {float(decision.get('bull_score', 0)):>6.2f}/100     "
        f"BEAR SCORE  {float(decision.get('bear_score', 0)):>6.2f}/100"
    )
    print(
        f"BREADTH     {decision.get('breadth'):<18}"
        f"MOMENTUM    {decision.get('momentum'):<18}"
        f"TREND {decision.get('trend')}"
    )

    print("\nWHY")
    print("-" * WIDTH)
    for reason in decision.get("why", []):
        print(f"- {reason}")

    print("\nBLOCKERS")
    print("-" * WIDTH)
    blockers = decision.get("blockers", [])
    if blockers:
        for blocker in blockers:
            print(f"- {blocker}")
    else:
        print("No market-health blocker.")

    print("\nWARNINGS")
    print("-" * WIDTH)
    warnings = decision.get("warnings", [])
    if warnings:
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("No warning carried from Market Health.")

    print("-" * WIDTH)
    print(f"EXECUTION ALLOWED : {decision.get('execution_allowed')}")
    print(f"NOTE              : {decision.get('execution_note')}")
    print("=" * WIDTH)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--health", default="market_health_snapshot.json")
    parser.add_argument("--output", default="commander_decision_snapshot.json")
    parser.add_argument("--refresh", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    while True:
        try:
            render(generate_decision(args.health, args.output))
        except Exception as error:
            _clear()
            print(f"COMMANDER DECISION ERROR: {error}")

        if args.once:
            break

        time.sleep(max(args.refresh, 1))


if __name__ == "__main__":
    main()
