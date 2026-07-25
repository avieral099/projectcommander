from datetime import time

import pandas as pd

from historical_data import get_historical_data


DEFAULT_RESOLUTION = "5"


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_opening_range(
    symbol,
    resolution=DEFAULT_RESOLUTION,
):
    candles = get_historical_data(
        symbol=symbol,
        resolution=resolution,
    )

    if not candles:
        raise RuntimeError(
            f"No candles available for opening range on {symbol}"
        )

    df = pd.DataFrame(
        candles,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ],
    )

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="s",
        utc=True,
    ).dt.tz_convert("Asia/Kolkata")

    trading_date = df["timestamp"].dt.date.max()

    day_df = df[
        df["timestamp"].dt.date
        == trading_date
    ].copy()

    if day_df.empty:
        raise RuntimeError(
            f"No current trading-day candles for {symbol}"
        )

    opening_candles = day_df[
        (
            day_df["timestamp"].dt.time
            >= time(9, 15)
        )
        & (
            day_df["timestamp"].dt.time
            < time(9, 30)
        )
    ]

    if opening_candles.empty:
        return {
            "symbol": symbol,
            "trading_date": str(trading_date),
            "timeframe": "15_MINUTE",
            "or_high": 0.0,
            "or_low": 0.0,
            "or_range": 0.0,
            "current_price": safe_float(
                day_df.iloc[-1]["close"]
            ),
            "status": "NOT_AVAILABLE",
        }

    or_high = safe_float(
        opening_candles["high"].max()
    )
    or_low = safe_float(
        opening_candles["low"].min()
    )
    or_range = or_high - or_low

    current_price = safe_float(
        day_df.iloc[-1]["close"]
    )

    if current_price > or_high:
        status = "ABOVE_ORH"
    elif current_price < or_low:
        status = "BELOW_ORL"
    else:
        status = "INSIDE_RANGE"

    return {
        "symbol": symbol,
        "trading_date": str(trading_date),
        "timeframe": "15_MINUTE",
        "or_high": round(or_high, 2),
        "or_low": round(or_low, 2),
        "or_range": round(or_range, 2),
        "current_price": round(
            current_price,
            2,
        ),
        "status": status,
    }
