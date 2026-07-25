import pandas as pd

from historical_data import get_historical_data


# =====================================================
# SETTINGS
# =====================================================

RSI_PERIOD = 14
DEFAULT_RESOLUTION = "1"


# =====================================================
# CALCULATE RSI
# =====================================================

def calculate_rsi(
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

    df["close"] = pd.to_numeric(
        df["close"],
        errors="coerce"
    )

    df.dropna(
        subset=["close"],
        inplace=True
    )

    if len(df) < RSI_PERIOD + 1:
        raise RuntimeError(
            f"Not enough candles for RSI on {symbol}. "
            f"Received {len(df)}, minimum required {RSI_PERIOD + 1}."
        )

    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder-style smoothing used for RSI
    avg_gain = gain.ewm(
        alpha=1 / RSI_PERIOD,
        adjust=False,
        min_periods=RSI_PERIOD
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / RSI_PERIOD,
        adjust=False,
        min_periods=RSI_PERIOD
    ).mean()

    rs = avg_gain / avg_loss

    df["rsi"] = 100 - (100 / (1 + rs))

    df.dropna(
        subset=["rsi"],
        inplace=True
    )

    if df.empty:
        raise RuntimeError(
            f"No valid RSI values generated for {symbol}."
        )

    latest = df.iloc[-1]

    rsi_value = float(latest["rsi"])

    if rsi_value >= 70:
        state = "OVERBOUGHT"
    elif rsi_value <= 30:
        state = "OVERSOLD"
    else:
        state = "NEUTRAL"

    return {
        "symbol": symbol,
        "timeframe": resolution,
        "timestamp": latest["timestamp"],
        "close": float(latest["close"]),
        "rsi": rsi_value,
        "state": state,
        "total_candles": len(df)
    }


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    TEST_SYMBOL = "NSE:NIFTY50-INDEX"

    result = calculate_rsi(
        symbol=TEST_SYMBOL
    )

    print("\n")
    print("=" * 55)
    print("                 RSI ENGINE")
    print("=" * 55)

    print(f"Symbol          : {result['symbol']}")
    print(f"Time Frame      : {result['timeframe']} Minute")
    print(f"Total Candles   : {result['total_candles']}")

    print("-" * 55)

    print(f"Time            : {result['timestamp']}")
    print(f"Close           : {result['close']:.2f}")
    print(f"RSI             : {result['rsi']:.2f}")
    print(f"State           : {result['state']}")

    print("=" * 55)