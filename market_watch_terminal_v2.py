from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any


WIDTH = 96


def _clear() -> None:
    os.system("clear")


def _short(symbol: str) -> str:
    return symbol.replace("NSE:", "").replace("-EQ", "")


def _event_line(event: dict[str, Any]) -> str:
    return (
        f"{_short(str(event.get('symbol', ''))):<14} "
        f"{str(event.get('event', 'UNKNOWN')):<28} "
        f"Close {float(event.get('close', 0.0)):>10.2f}"
    )


def _print_list(title: str, values: list[dict[str, Any]], limit: int = 8) -> None:
    print(f"\n{title}")
    print("-" * WIDTH)
    if not values:
        print("No fresh events.")
        return
    for event in values[:limit]:
        if "events" in event:
            print(
                f"{_short(str(event.get('symbol', ''))):<14} "
                f"RSI {float(event.get('rsi', 0.0)):>6.2f} | "
                f"{event.get('rsi_state', 'NEUTRAL')}"
            )
        else:
            print(_event_line(event))


def render(snapshot: dict[str, Any]) -> None:
    breadth = snapshot.get("breadth_5m", {})
    daily = snapshot.get("daily_watch", {})
    total = int(breadth.get("total", 0))

    _clear()
    print("=" * WIDTH)
    print("COMMANDER — MARKET STRUCTURE WATCH".center(WIDTH))
    print("=" * WIDTH)
    print(
        f"UPDATED {snapshot.get('generated_at', 'NO DATA')} | "
        f"UNIVERSE {snapshot.get('universe', 'UNKNOWN')} | "
        f"SCANNED {snapshot.get('completed_symbols', 0)}/"
        f"{snapshot.get('requested_symbols', 0)}"
    )

    print("\n5-MINUTE MARKET BREADTH")
    print("-" * WIDTH)
    print(
        f"Above EMA5   {breadth.get('above_ema5', 0):>3}/{total:<3}   "
        f"Above EMA20  {breadth.get('above_ema20', 0):>3}/{total:<3}   "
        f"Above EMA50  {breadth.get('above_ema50', 0):>3}/{total:<3}"
    )
    print(
        f"Above EMA100 {breadth.get('above_ema100', 0):>3}/{total:<3}   "
        f"Above EMA200 {breadth.get('above_ema200', 0):>3}/{total:<3}   "
        f"Above VWAP   {breadth.get('above_vwap', 0):>3}/{total:<3}"
    )
    print(
        f"Above PDC    {breadth.get('above_pdc', 0):>3}/{total:<3}   "
        f"Above PDH    {breadth.get('above_pdh', 0):>3}/{total:<3}   "
        f"Below PDL    {breadth.get('below_pdl', 0):>3}/{total:<3}"
    )
    print(
        f"Bull Stack   {breadth.get('bullish_stack', 0):>3}       "
        f"Bear Stack   {breadth.get('bearish_stack', 0):>3}       "
        f"Transition   {breadth.get('transition', 0):>3}"
    )

    _print_list("FRESH 5-MINUTE BREAKOUTS / RECLAIMS", breadth.get("fresh_breakouts", []))
    _print_list("FRESH 5-MINUTE BREAKDOWNS / LOSSES", breadth.get("fresh_breakdowns", []))
    _print_list("DAILY RSI APPROACHING 20", daily.get("rsi_approaching_20", []))
    _print_list("DAILY RSI AT / BELOW 20", daily.get("rsi_at_20", []))
    _print_list("DAILY EMA BREAKDOWNS", daily.get("daily_breakdowns", []))

    errors = snapshot.get("errors", [])
    print("\nSYSTEM")
    print("-" * WIDTH)
    print(f"Scanner errors: {len(errors)}")
    print("=" * WIDTH)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default="market_structure_snapshot.json")
    parser.add_argument("--refresh", type=int, default=5)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    path = Path(args.snapshot)

    while True:
        try:
            snapshot = json.loads(path.read_text())
            render(snapshot)
        except FileNotFoundError:
            _clear()
            print("Waiting for market_structure_snapshot.json")
        except Exception as error:
            _clear()
            print(f"MARKET WATCH ERROR: {error}")

        if args.once:
            break
        time.sleep(max(args.refresh, 1))


if __name__ == "__main__":
    main()
