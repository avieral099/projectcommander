import pandas as pd

from historical_data import get_historical_data


DEFAULT_RESOLUTION = "5"
EMA_PERIOD = 75


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_ema(
    symbol,
    resolution=DEFAULT_RESOLUTION,
):
    candles = get_historical_data(
        symbol=symbol,
        resolution=resolution,
    )

    if not candles:
        raise RuntimeError(
            f"No candles available for EMA75 on {symbol}"
        )

    if len(candles) < EMA_PERIOD:
        raise RuntimeError(
            f"Not enough candles for EMA75 on {symbol}. "
            f"Received {len(candles)} candles."
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

    df["ema75_high"] = (
        df["high"]
        .ewm(
            span=EMA_PERIOD,
            adjust=False,
        )
        .mean()
    )

    df["ema75_low"] = (
        df["low"]
        .ewm(
            span=EMA_PERIOD,
            adjust=False,
        )
        .mean()
    )

    latest = df.iloc[-1]

    close_price = safe_float(latest["close"])
    ema_high = safe_float(latest["ema75_high"])
    ema_low = safe_float(latest["ema75_low"])

    point_distance_high = (
        close_price - ema_high
    )
    point_distance_low = (
        close_price - ema_low
    )

    percentage_distance_high = (
        (point_distance_high / ema_high) * 100
        if ema_high
        else 0.0
    )

    percentage_distance_low = (
        (point_distance_low / ema_low) * 100
        if ema_low
        else 0.0
    )

    if close_price > ema_high:
        high_relation = "ABOVE"
    elif close_price < ema_high:
        high_relation = "BELOW"
    else:
        high_relation = "AT"

    if close_price > ema_low:
        low_relation = "ABOVE"
    elif close_price < ema_low:
        low_relation = "BELOW"
    else:
        low_relation = "AT"

    if close_price > ema_high:
        structure_state = "ABOVE_BOTH"
    elif close_price < ema_low:
        structure_state = "BELOW_BOTH"
    else:
        structure_state = "BETWEEN_EMA75_HIGH_LOW"

    return {
        "symbol": symbol,
        "timeframe": str(resolution),
        "timestamp": latest["timestamp"].strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "close": round(close_price, 2),

        "ema75_high": round(ema_high, 2),
        "ema75_high_relation": high_relation,
        "point_distance_high": round(
            point_distance_high,
            2,
        ),
        "percentage_distance_high": round(
            percentage_distance_high,
            2,
        ),

        "ema75_low": round(ema_low, 2),
        "ema75_low_relation": low_relation,
        "point_distance_low": round(
            point_distance_low,
            2,
        ),
        "percentage_distance_low": round(
            percentage_distance_low,
            2,
        ),

        "structure_state": structure_state,
    }
