import pandas as pd

from market_data import get_historical_data


# =====================================================
# SETTINGS
# =====================================================

DEFAULT_RESOLUTION = "1"
EMA_PERIOD = 75


# =====================================================
# EMA ENGINE
# =====================================================

def calculate_ema(
    symbol,
    resolution=DEFAULT_RESOLUTION
):
    candles = get_historical_data(
        symbol=symbol,
        resolution=resolution
    )

    df = pd.DataFrame(
        candles,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]
    )

    df["timestamp"] = (
        pd.to_datetime(
            df["timestamp"],
            unit="s",
            utc=True
        )
        .dt.tz_convert("Asia/Kolkata")
        .dt.tz_localize(None)
    )

    for column in ["high", "low", "close"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df.dropna(
        subset=["high", "low", "close"],
        inplace=True
    )

    if len(df) < EMA_PERIOD:
        raise RuntimeError(
            f"Not enough candles for EMA{EMA_PERIOD} on {symbol}. "
            f"Received {len(df)} candles."
        )

    df["ema75_high"] = (
        df["high"]
        .ewm(
            span=EMA_PERIOD,
            adjust=False
        )
        .mean()
    )

    df["ema75_low"] = (
        df["low"]
        .ewm(
            span=EMA_PERIOD,
            adjust=False
        )
        .mean()
    )

    latest = df.iloc[-1]

    close_price = float(latest["close"])
    ema_high = float(latest["ema75_high"])
    ema_low = float(latest["ema75_low"])

    point_distance_high = close_price - ema_high
    point_distance_low = close_price - ema_low

    percentage_distance_high = (
        point_distance_high / ema_high
    ) * 100

    percentage_distance_low = (
        point_distance_low / ema_low
    ) * 100

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
        "timeframe": resolution,
        "timestamp": latest["timestamp"],
        "close": close_price,

        "ema75_high": ema_high,
        "ema75_high_relation": high_relation,
        "point_distance_high": round(
            point_distance_high,
            2
        ),
        "percentage_distance_high": round(
            percentage_distance_high,
            2
        ),

        "ema75_low": ema_low,
        "ema75_low_relation": low_relation,
        "point_distance_low": round(
            point_distance_low,
            2
        ),
        "percentage_distance_low": round(
            percentage_distance_low,
            2
        ),

        "structure_state": structure_state,
        "total_candles": len(df)
    }


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    TEST_SYMBOL = "NSE:NIFTY50-INDEX"

    result = calculate_ema(
        TEST_SYMBOL
    )

    print("\n")
    print("=" * 60)
    print("                 EMA75 ENGINE")
    print("=" * 60)

    print(f"Symbol              : {result['symbol']}")
    print(f"Time Frame          : {result['timeframe']} Minute")
    print(f"Time                : {result['timestamp']}")
    print(f"Close               : {result['close']:.2f}")

    print("-" * 60)

    print(f"EMA75 High          : {result['ema75_high']:.2f}")
    print(
        f"High Relation       : "
        f"{result['ema75_high_relation']}"
    )
    print(
        f"Distance High       : "
        f"{result['point_distance_high']:.2f}"
    )
    print(
        f"Distance High %     : "
        f"{result['percentage_distance_high']:.2f}%"
    )

    print("-" * 60)

    print(f"EMA75 Low           : {result['ema75_low']:.2f}")
    print(
        f"Low Relation        : "
        f"{result['ema75_low_relation']}"
    )
    print(
        f"Distance Low        : "
        f"{result['point_distance_low']:.2f}"
    )
    print(
        f"Distance Low %      : "
        f"{result['percentage_distance_low']:.2f}%"
    )

    print("-" * 60)

    print(
        f"Structure State     : "
        f"{result['structure_state']}"
    )

    print("=" * 60)