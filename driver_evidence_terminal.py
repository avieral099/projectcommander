from __future__ import annotations

import argparse
import os
import time
from typing import Any

from driver_evidence_adapter import generate_driver_evidence


WIDTH = 104


def _clear() -> None:
    os.system("clear")


def _row(item: dict[str, Any]) -> str:
    return (
        f"{item.get('name', 'UNKNOWN'):<18} "
        f"{item.get('side', 'UNKNOWN'):<8} "
        f"SCORE {float(item.get('score', 0)):>6.2f} "
        f"CHG {float(item.get('change_pct', 0)):>7.2f}% "
        f"{item.get('state', 'UNKNOWN')}"
    )


def render(data: dict[str, Any]) -> None:
    _clear()
    print("=" * WIDTH)
    print("OPERATION COMMANDER — DRIVER EVIDENCE".center(WIDTH))
    print("=" * WIDTH)
    print(
        f"UPDATED {data.get('generated_at')} | "
        f"SOURCE {data.get('source')}"
    )
    print("-" * WIDTH)
    print(
        f"STATUS       {data.get('status'):<18}"
        f"SIDE         {data.get('driver_side'):<10}"
        f"SCORE {float(data.get('driver_score', 0)):>6.2f}/100"
    )
    print(
        f"STATE        {data.get('driver_state'):<18}"
        f"AGREEMENT    {float(data.get('agreement_pct', 0)):>6.2f}%"
    )
    print(
        f"PARTICIPATION {data.get('participation')}"
    )

    print("\nLEADERS")
    print("-" * WIDTH)
    leaders = data.get("leaders", [])
    if leaders:
        for item in leaders:
            print(_row(item))
    else:
        print("No aligned leaders.")

    print("\nLAGGARDS")
    print("-" * WIDTH)
    laggards = data.get("laggards", [])
    if laggards:
        for item in laggards:
            print(_row(item))
    else:
        print("No opposing laggards.")

    print("\nMISSING FIELDS")
    print("-" * WIDTH)
    missing = data.get("missing_fields", [])
    print(", ".join(missing) if missing else "None")

    print("-" * WIDTH)
    print(data.get("note"))
    print("=" * WIDTH)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-source")
    parser.add_argument("--output", default="driver_evidence_snapshot.json")
    parser.add_argument("--refresh", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    while True:
        try:
            data = generate_driver_evidence(
                json_source=args.json_source,
                output_path=args.output,
            )
            render(data)
        except Exception as error:
            _clear()
            print(f"DRIVER EVIDENCE ERROR: {error}")

        if args.once:
            break

        time.sleep(max(1, args.refresh))


if __name__ == "__main__":
    main()
