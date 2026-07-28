from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

import pandas as pd


EMA_PERIODS = (20, 50, 100, 200)
REQUIRED = {"open", "high", "low", "close"}


@dataclass(frozen=True)
class DailyEvent:
    symbol: str
    timeframe: str
    event: str
    direction: str
    level: float
    close: float
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalise(data: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")

    frame = data.copy()
    frame.columns = [str(column).lower() for column in frame.columns]

    missing = REQUIRED.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")

    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        frame = frame.sort_values("timestamp")

    frame[["open", "high", "low", "close"]] = frame[
        ["open", "high", "low", "close"]
    ].apply(pd.to_numeric, errors="coerce")

    frame = frame.dropna(subset=["open", "high", "low", "close"])
    if frame.empty:
        raise ValueError("No usable daily candles")

    return frame.reset_index(drop=True)


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()
    average_loss = losses.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    rs = average_gain / average_loss.replace(0, pd.NA)
    return (100 - (100 / (1 + rs))).fillna(50)


def analyse_daily_structure(
    data: pd.DataFrame,
    *,
    symbol: str,
    rsi_period: int = 14,
    approaching_low: float = 25.0,
    oversold: float = 20.0,
    approaching_high: float = 75.0,
    overbought: float = 80.0,
) -> dict[str, Any]:
    frame = _normalise(data)

    minimum = max(EMA_PERIODS) + 2
    if len(frame) < minimum:
        raise ValueError(f"At least {minimum} daily candles required")

    for period in EMA_PERIODS:
        frame[f"ema_{period}"] = frame["close"].ewm(
            span=period,
            adjust=False,
        ).mean()

    frame["rsi"] = calculate_rsi(frame["close"], rsi_period)

    previous = frame.iloc[-2]
    latest = frame.iloc[-1]

    close = float(latest["close"])
    previous_close = float(previous["close"])
    rsi = float(latest["rsi"])
    previous_rsi = float(previous["rsi"])

    events: list[DailyEvent] = []
    position: dict[str, str] = {}

    for period in EMA_PERIODS:
        key = f"ema_{period}"
        level = float(latest[key])
        previous_level = float(previous[key])
        position[f"ema_{period}"] = "ABOVE" if close > level else "BELOW"

        if previous_close <= previous_level and close > level:
            events.append(DailyEvent(
                symbol, "1d", f"DAILY_EMA{period}_BREAKOUT", "UP",
                level, close, f"Daily close crossed above EMA {period}.",
            ))
        elif previous_close >= previous_level and close < level:
            events.append(DailyEvent(
                symbol, "1d", f"DAILY_EMA{period}_BREAKDOWN", "DOWN",
                level, close, f"Daily close crossed below EMA {period}.",
            ))

    rsi_state = "NEUTRAL"
    if rsi <= oversold:
        rsi_state = "RSI_20_OR_LOWER"
        events.append(DailyEvent(
            symbol, "1d", "DAILY_RSI_AT_20_ZONE", "WATCH",
            oversold, close, f"Daily RSI is {rsi:.2f}.",
        ))
    elif rsi <= approaching_low and rsi < previous_rsi:
        rsi_state = "RSI_APPROACHING_20"
        events.append(DailyEvent(
            symbol, "1d", "DAILY_RSI_APPROACHING_20", "WATCH",
            approaching_low, close,
            f"Daily RSI is falling towards 20 ({rsi:.2f}).",
        ))
    elif rsi >= overbought:
        rsi_state = "RSI_80_OR_HIGHER"
        events.append(DailyEvent(
            symbol, "1d", "DAILY_RSI_AT_80_ZONE", "WATCH",
            overbought, close, f"Daily RSI is {rsi:.2f}.",
        ))
    elif rsi >= approaching_high and rsi > previous_rsi:
        rsi_state = "RSI_APPROACHING_80"
        events.append(DailyEvent(
            symbol, "1d", "DAILY_RSI_APPROACHING_80", "WATCH",
            approaching_high, close,
            f"Daily RSI is rising towards 80 ({rsi:.2f}).",
        ))

    return {
        "symbol": symbol,
        "timeframe": "1d",
        "timestamp": (
            str(latest["timestamp"])
            if "timestamp" in latest.index
            else ""
        ),
        "close": round(close, 4),
        "emas": {
            str(period): round(float(latest[f"ema_{period}"]), 4)
            for period in EMA_PERIODS
        },
        "position": position,
        "rsi": round(rsi, 2),
        "previous_rsi": round(previous_rsi, 2),
        "rsi_state": rsi_state,
        "events": [event.to_dict() for event in events],
    }


def aggregate_daily_watch(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(results)
    output = {
        "total": len(rows),
        "rsi_approaching_20": [],
        "rsi_at_20": [],
        "rsi_approaching_80": [],
        "rsi_at_80": [],
        "daily_breakouts": [],
        "daily_breakdowns": [],
    }

    for row in rows:
        state = row.get("rsi_state")
        if state == "RSI_APPROACHING_20":
            output["rsi_approaching_20"].append(row)
        elif state == "RSI_20_OR_LOWER":
            output["rsi_at_20"].append(row)
        elif state == "RSI_APPROACHING_80":
            output["rsi_approaching_80"].append(row)
        elif state == "RSI_80_OR_HIGHER":
            output["rsi_at_80"].append(row)

        for event in row.get("events", []):
            name = str(event.get("event", ""))
            if "BREAKOUT" in name:
                output["daily_breakouts"].append(event)
            if "BREAKDOWN" in name:
                output["daily_breakdowns"].append(event)

    return output
