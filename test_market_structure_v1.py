from __future__ import annotations

import math
from datetime import datetime, timedelta

import pandas as pd

from daily_structure_engine import analyse_daily_structure
from market_structure_5m_engine import analyse_5m_structure, aggregate_5m_breadth


def candles(count: int, start: float, step: float, minutes: int) -> pd.DataFrame:
    rows = []
    value = start
    timestamp = datetime(2026, 1, 1, 9, 15)
    for index in range(count):
        open_price = value
        close_price = value + step + math.sin(index / 7) * 0.15
        rows.append({
            "timestamp": timestamp,
            "open": open_price,
            "high": max(open_price, close_price) + 1,
            "low": min(open_price, close_price) - 1,
            "close": close_price,
            "volume": 1000 + index,
        })
        value = close_price
        timestamp += timedelta(minutes=minutes)
    return pd.DataFrame(rows)


five = candles(240, 100, 0.12, 5)
five.loc[five.index[-2], "close"] = 125
five.loc[five.index[-1], "close"] = 140

result_5m = analyse_5m_structure(
    five,
    symbol="NSE:TEST-EQ",
    pdc=130,
    pdh=138,
    pdl=110,
    orh=135,
    orl=115,
)

assert result_5m["timeframe"] == "5m"
assert "5" in result_5m["emas"]
assert result_5m["position"]["pdh"] == "ABOVE"
assert any(event["event"] == "PDH_BREAKOUT" for event in result_5m["events"])

breadth = aggregate_5m_breadth([result_5m])
assert breadth["total"] == 1
assert breadth["above_pdh"] == 1

daily = candles(260, 500, -0.55, 1440)
daily_result = analyse_daily_structure(
    daily,
    symbol="NSE:COALINDIA-EQ",
)

assert daily_result["timeframe"] == "1d"
assert set(daily_result["emas"]) == {"20", "50", "100", "200"}
assert isinstance(daily_result["rsi"], float)

print("ALL MARKET STRUCTURE V1 TESTS PASSED")
