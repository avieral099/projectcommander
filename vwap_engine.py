import pandas as pd

from historical_data import get_historical_data


DEFAULT_RESOLUTION = "5"


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_vwap(symbol, resolution=DEFAULT_RESOLUTION):
    candles = get_historical_data(
        symbol=symbol,
        resolution=resolution,
    )

    if not candles:
        raise RuntimeError(
            f"No valid candle data available for VWAP on {symbol}"
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

    today = df["timestamp"].dt.date.max()
    day_df = df[
        df["timestamp"].dt.date == today
    ].copy()

    if day_df.empty:
        raise RuntimeError(
            f"No current trading-day candles for VWAP on {symbol}"
        )

    day_df["typical_price"] = (
        day_df["high"]
        + day_df["low"]
        + day_df["close"]
    ) / 3

    day_df["price_volume"] = (
        day_df["typical_price"]
        * day_df["volume"]
    )

    total_volume = safe_float(
        day_df["volume"].sum()
    )

    if total_volume <= 0:
        vwap = safe_float(
            day_df.iloc[-1]["close"]
        )
    else:
        vwap = safe_float(
            day_df["price_volume"].sum()
            / total_volume
        )

    latest = day_df.iloc[-1]
    close_price = safe_float(latest["close"])

    point_distance = close_price - vwap

    percentage_distance = (
        (point_distance / vwap) * 100
        if vwap
        else 0.0
    )

    if close_price > vwap:
        state = "ABOVE_VWAP"
    elif close_price < vwap:
        state = "BELOW_VWAP"
    else:
        state = "AT_VWAP"

    return {
        "symbol": symbol,
        "timeframe": str(resolution),
        "trading_date": str(today),
        "timestamp": latest["timestamp"].strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "close": round(close_price, 2),
        "vwap": round(vwap, 2),
        "point_distance": round(
            point_distance,
            2,
        ),
        "percentage_distance": round(
            percentage_distance,
            2,
        ),
        "state": state,
    }
