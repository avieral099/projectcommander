from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

import pandas as pd


EMA_PERIODS = (5, 20, 50, 100, 200)
REQUIRED = {"open", "high", "low", "close", "volume"}


@dataclass(frozen=True)
class StructureEvent:
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

    numeric = ["open", "high", "low", "close", "volume"]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    frame = frame.dropna(subset=["open", "high", "low", "close"])
    if frame.empty:
        raise ValueError("No usable candles")

    return frame.reset_index(drop=True)


def _crossed_above(previous_close: float, close: float, previous_level: float, level: float) -> bool:
    return previous_close <= previous_level and close > level


def _crossed_below(previous_close: float, close: float, previous_level: float, level: float) -> bool:
    return previous_close >= previous_level and close < level


def calculate_vwap(frame: pd.DataFrame) -> pd.Series:
    typical = (frame["high"] + frame["low"] + frame["close"]) / 3.0
    cumulative_volume = frame["volume"].fillna(0).cumsum()
    value = (typical * frame["volume"].fillna(0)).cumsum()
    return (value / cumulative_volume.replace(0, pd.NA)).ffill()


def analyse_5m_structure(
    data: pd.DataFrame,
    *,
    symbol: str,
    pdc: float,
    pdh: float,
    pdl: float,
    orh: float = 0.0,
    orl: float = 0.0,
) -> dict[str, Any]:
    frame = _normalise(data)

    minimum = max(EMA_PERIODS) + 2
    if len(frame) < minimum:
        raise ValueError(f"At least {minimum} 5-minute candles required")

    for period in EMA_PERIODS:
        frame[f"ema_{period}"] = frame["close"].ewm(
            span=period,
            adjust=False,
        ).mean()

    frame["vwap"] = calculate_vwap(frame)

    previous = frame.iloc[-2]
    latest = frame.iloc[-1]
    close = float(latest["close"])
    previous_close = float(previous["close"])

    events: list[StructureEvent] = []
    position: dict[str, str] = {}

    for period in EMA_PERIODS:
        key = f"ema_{period}"
        level = float(latest[key])
        previous_level = float(previous[key])
        position[f"ema_{period}"] = "ABOVE" if close > level else "BELOW"

        if _crossed_above(previous_close, close, previous_level, level):
            events.append(StructureEvent(
                symbol, "5m", f"EMA{period}_BREAKOUT", "UP", level, close,
                f"Price crossed above 5-minute EMA {period}.",
            ))
        elif _crossed_below(previous_close, close, previous_level, level):
            events.append(StructureEvent(
                symbol, "5m", f"EMA{period}_BREAKDOWN", "DOWN", level, close,
                f"Price crossed below 5-minute EMA {period}.",
            ))

    vwap = float(latest["vwap"]) if pd.notna(latest["vwap"]) else 0.0
    previous_vwap = float(previous["vwap"]) if pd.notna(previous["vwap"]) else 0.0
    position["vwap"] = "ABOVE" if close > vwap else "BELOW"

    if vwap > 0:
        if _crossed_above(previous_close, close, previous_vwap, vwap):
            events.append(StructureEvent(
                symbol, "5m", "VWAP_RECLAIM", "UP", vwap, close,
                "Price reclaimed intraday VWAP.",
            ))
        elif _crossed_below(previous_close, close, previous_vwap, vwap):
            events.append(StructureEvent(
                symbol, "5m", "VWAP_LOSS", "DOWN", vwap, close,
                "Price lost intraday VWAP.",
            ))

    reference_levels = {
        "PDC": float(pdc or 0.0),
        "PDH": float(pdh or 0.0),
        "PDL": float(pdl or 0.0),
        "ORH": float(orh or 0.0),
        "ORL": float(orl or 0.0),
    }

    for name, level in reference_levels.items():
        if level <= 0:
            position[name.lower()] = "NOT_READY"
            continue

        position[name.lower()] = "ABOVE" if close > level else "BELOW"

        if previous_close <= level < close:
            event = {
                "PDC": "PDC_RECLAIM",
                "PDH": "PDH_BREAKOUT",
                "PDL": "PDL_RECLAIM",
                "ORH": "ORH_BREAKOUT",
                "ORL": "ORL_RECLAIM",
            }[name]
            events.append(StructureEvent(
                symbol, "5m", event, "UP", level, close,
                f"Price crossed above {name}.",
            ))
        elif previous_close >= level > close:
            event = {
                "PDC": "PDC_LOSS",
                "PDH": "PDH_REJECTION",
                "PDL": "PDL_BREAKDOWN",
                "ORH": "ORH_LOSS",
                "ORL": "ORL_BREAKDOWN",
            }[name]
            events.append(StructureEvent(
                symbol, "5m", event, "DOWN", level, close,
                f"Price crossed below {name}.",
            ))

    ema_values = [float(latest[f"ema_{period}"]) for period in EMA_PERIODS]
    bullish_stack = close > ema_values[0] > ema_values[1] > ema_values[2] > ema_values[3] > ema_values[4]
    bearish_stack = close < ema_values[0] < ema_values[1] < ema_values[2] < ema_values[3] < ema_values[4]

    stack = "BULLISH_STACK" if bullish_stack else "BEARISH_STACK" if bearish_stack else "TRANSITION"

    return {
        "symbol": symbol,
        "timeframe": "5m",
        "timestamp": (
            str(latest["timestamp"])
            if "timestamp" in latest.index
            else ""
        ),
        "close": round(close, 4),
        "previous_close": round(previous_close, 4),
        "emas": {
            str(period): round(float(latest[f"ema_{period}"]), 4)
            for period in EMA_PERIODS
        },
        "vwap": round(vwap, 4),
        "levels": {
            key.lower(): round(value, 4)
            for key, value in reference_levels.items()
        },
        "position": position,
        "stack": stack,
        "events": [event.to_dict() for event in events],
    }


def aggregate_5m_breadth(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(results)
    total = len(rows)

    breadth = {
        "total": total,
        "above_ema5": 0,
        "above_ema20": 0,
        "above_ema50": 0,
        "above_ema100": 0,
        "above_ema200": 0,
        "above_vwap": 0,
        "above_pdc": 0,
        "above_pdh": 0,
        "below_pdl": 0,
        "bullish_stack": 0,
        "bearish_stack": 0,
        "transition": 0,
        "fresh_breakouts": [],
        "fresh_breakdowns": [],
    }

    for row in rows:
        position = row.get("position", {})
        for period in EMA_PERIODS:
            if position.get(f"ema_{period}") == "ABOVE":
                breadth[f"above_ema{period}"] += 1

        if position.get("vwap") == "ABOVE":
            breadth["above_vwap"] += 1
        if position.get("pdc") == "ABOVE":
            breadth["above_pdc"] += 1
        if position.get("pdh") == "ABOVE":
            breadth["above_pdh"] += 1
        if position.get("pdl") == "BELOW":
            breadth["below_pdl"] += 1

        stack = row.get("stack", "TRANSITION")
        if stack == "BULLISH_STACK":
            breadth["bullish_stack"] += 1
        elif stack == "BEARISH_STACK":
            breadth["bearish_stack"] += 1
        else:
            breadth["transition"] += 1

        for event in row.get("events", []):
            name = str(event.get("event", ""))
            if any(token in name for token in ("BREAKOUT", "RECLAIM")):
                breadth["fresh_breakouts"].append(event)
            if any(token in name for token in ("BREAKDOWN", "LOSS", "REJECTION")):
                breadth["fresh_breakdowns"].append(event)

    return breadth
