from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from daily_structure_engine import analyse_daily_structure, aggregate_daily_watch
from market_scanner_provider import ProviderError, fetch_candles
from market_structure_5m_engine import analyse_5m_structure, aggregate_5m_breadth


def _previous_day_levels(daily: pd.DataFrame) -> tuple[float, float, float]:
    frame = daily.copy()
    frame.columns = [str(column).lower() for column in frame.columns]
    if len(frame) < 2:
        raise ValueError("At least two daily candles required for PDC/PDH/PDL")
    row = frame.iloc[-2]
    return float(row["close"]), float(row["high"]), float(row["low"])


def _opening_range(frame: pd.DataFrame, bars: int = 3) -> tuple[float, float]:
    normalised = frame.copy()
    normalised.columns = [str(column).lower() for column in normalised.columns]
    if len(normalised) < bars:
        return 0.0, 0.0
    first = normalised.iloc[:bars]
    return float(first["high"].max()), float(first["low"].min())


def scan_symbol(symbol: str) -> dict[str, Any]:
    five = fetch_candles(symbol, "5", days=12)
    daily = fetch_candles(symbol, "D", days=330)

    pdc, pdh, pdl = _previous_day_levels(daily)
    orh, orl = _opening_range(five, bars=3)

    return {
        "symbol": symbol,
        "intraday": analyse_5m_structure(
            five,
            symbol=symbol,
            pdc=pdc,
            pdh=pdh,
            pdl=pdl,
            orh=orh,
            orl=orl,
        ),
        "daily": analyse_daily_structure(
            daily,
            symbol=symbol,
        ),
    }


def run_scan(
    config_path: str | Path = "market_scanner_config.json",
    output_path: str | Path = "market_structure_snapshot.json",
) -> dict[str, Any]:
    config = json.loads(Path(config_path).read_text())
    symbols = list(config.get("symbols", []))

    results = []
    errors = []

    for symbol in symbols:
        try:
            results.append(scan_symbol(symbol))
        except Exception as error:
            errors.append({
                "symbol": symbol,
                "error": str(error),
            })

    intraday_results = [row["intraday"] for row in results]
    daily_results = [row["daily"] for row in results]

    snapshot = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "universe": config.get("universe_name", "CUSTOM"),
        "requested_symbols": len(symbols),
        "completed_symbols": len(results),
        "errors": errors,
        "breadth_5m": aggregate_5m_breadth(intraday_results),
        "daily_watch": aggregate_daily_watch(daily_results),
        "symbols": results,
    }

    Path(output_path).write_text(
        json.dumps(snapshot, indent=2, default=str)
    )
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="market_scanner_config.json")
    parser.add_argument("--output", default="market_structure_snapshot.json")
    args = parser.parse_args()

    snapshot = run_scan(args.config, args.output)
    print(
        "MARKET STRUCTURE SCAN COMPLETE | "
        f"{snapshot['completed_symbols']}/{snapshot['requested_symbols']} symbols"
    )
    print(f"OUTPUT: {args.output}")

    if snapshot["errors"]:
        print(f"ERRORS: {len(snapshot['errors'])}")
        for error in snapshot["errors"][:5]:
            print(f"- {error['symbol']}: {error['error']}")


if __name__ == "__main__":
    main()
