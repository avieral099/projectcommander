from __future__ import annotations

import argparse
import os
import time
from typing import Any

from premium_evidence_adapter import generate_premium_evidence


WIDTH = 100


def _clear() -> None:
    os.system("clear")


def render(data: dict[str, Any]) -> None:
    _clear()
    print("=" * WIDTH)
    print("OPERATION COMMANDER — PREMIUM EVIDENCE".center(WIDTH))
    print("=" * WIDTH)
    print(
        f"UPDATED {data.get('generated_at')} | "
        f"SOURCE {data.get('source')}"
    )
    print("-" * WIDTH)
    print(
        f"STATUS       {data.get('status'):<18}"
        f"INDEX        {data.get('index_symbol')}"
    )
    print(
        f"PREMIUM SIDE {data.get('premium_flow_side'):<18}"
        f"SCORE        {float(data.get('premium_score', 0)):>6.2f}/100"
    )
    print(
        f"COMMANDER    {data.get('commander_state'):<18}"
        f"DECAY        {data.get('decay_state')}"
    )
    print(
        f"ROTATION     {data.get('rotation_state'):<18}"
        f"STRADDLE     {data.get('straddle_structure')}"
    )
    print(
        f"SPOT         {float(data.get('spot_price', 0)):>10.2f}      "
        f"ATM STRADDLE {float(data.get('atm_straddle', 0)):>10.2f}"
    )

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
    parser.add_argument("--db-source")
    parser.add_argument("--output", default="premium_evidence_snapshot.json")
    parser.add_argument("--refresh", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    while True:
        try:
            data = generate_premium_evidence(
                json_source=args.json_source,
                db_source=args.db_source,
                output_path=args.output,
            )
            render(data)
        except Exception as error:
            _clear()
            print(f"PREMIUM EVIDENCE ERROR: {error}")

        if args.once:
            break

        time.sleep(max(1, args.refresh))


if __name__ == "__main__":
    main()
