import pandas as pd

from historical_data import get_historical_data


# =====================================================
# MACD SETTINGS
# =====================================================

FAST_PERIOD = 12
SLOW_PERIOD = 26
SIGNAL_PERIOD = 9
DEFAULT_RESOLUTION = "1"


# =====================================================
# CALCULATE MACD
# =====================================================

def calculate_macd(
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

    for column in [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df.dropna(
        subset=["close"],
        inplace=True
    )

    minimum_candles = SLOW_PERIOD + SIGNAL_PERIOD

    if len(df) < minimum_candles:
        raise RuntimeError(
            f"Not enough candles for MACD on {symbol}. "
            f"Received {len(df)}, minimum required {minimum_candles}."
        )

    df["ema_fast"] = df["close"].ewm(
        span=FAST_PERIOD,
        adjust=False
    ).mean()

    df["ema_slow"] = df["close"].ewm(
        span=SLOW_PERIOD,
        adjust=False
    ).mean()

    df["macd"] = (
        df["ema_fast"]
        - df["ema_slow"]
    )

    df["signal_line"] = df["macd"].ewm(
        span=SIGNAL_PERIOD,
        adjust=False
    ).mean()

    df["histogram"] = (
        df["macd"]
        - df["signal_line"]
    )

    latest = df.iloc[-1]

    macd_value = float(latest["macd"])
    signal_value = float(latest["signal_line"])
    histogram_value = float(latest["histogram"])

    if macd_value > signal_value:
        state = "ABOVE_SIGNAL_LINE"
    elif macd_value < signal_value:
        state = "BELOW_SIGNAL_LINE"
    else:
        state = "AT_SIGNAL_LINE"

    return {
        "symbol": symbol,
        "timeframe": resolution,
        "timestamp": latest["timestamp"],
        "close": float(latest["close"]),
        "macd": macd_value,
        "signal_line": signal_value,
        "histogram": histogram_value,
        "state": state,
        "total_candles": len(df)
    }


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    TEST_SYMBOL = "NSE:NIFTY50-INDEX"

    result = calculate_macd(
        symbol=TEST_SYMBOL
    )

    print("\n")
    print("=" * 55)
    print("                 MACD ENGINE")
    print("=" * 55)

    print(f"Symbol          : {result['symbol']}")
    print(f"Time Frame      : {result['timeframe']} Minute")
    print(f"Total Candles   : {result['total_candles']}")

    print("-" * 55)

    print(f"Time            : {result['timestamp']}")
    print(f"Close           : {result['close']:.2f}")
    print(f"MACD            : {result['macd']:.4f}")
    print(f"Signal Line     : {result['signal_line']:.4f}")
    print(f"Histogram       : {result['histogram']:.4f}")
    print(f"State           : {result['state']}")

    print("=" * 55)