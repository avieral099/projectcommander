import pandas as pd

from market_data import get_historical_data


# =====================================================
# SETTINGS
# =====================================================

DEFAULT_RESOLUTION = "1"


# =====================================================
# VWAP ENGINE
# =====================================================

def calculate_vwap(
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

    # Convert timestamp to Indian market time
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
        subset=["high", "low", "close", "volume"],
        inplace=True
    )

    if df.empty:
        raise RuntimeError(
            f"No valid candle data available for VWAP on {symbol}."
        )

    # Trading date used to reset VWAP every session
    df["trading_date"] = df["timestamp"].dt.date

    # Typical Price
    df["typical_price"] = (
        df["high"]
        + df["low"]
        + df["close"]
    ) / 3

    # Typical Price × Volume
    df["tpv"] = (
        df["typical_price"]
        * df["volume"]
    )

    # Reset cumulative calculations every trading day
    df["cumulative_tpv"] = (
        df.groupby("trading_date")["tpv"]
        .cumsum()
    )

    df["cumulative_volume"] = (
        df.groupby("trading_date")["volume"]
        .cumsum()
    )

    # Avoid division by zero
    df["vwap"] = (
        df["cumulative_tpv"]
        / df["cumulative_volume"].replace(0, pd.NA)
    )

    df.dropna(
        subset=["vwap"],
        inplace=True
    )

    if df.empty:
        raise RuntimeError(
            f"No valid VWAP values generated for {symbol}. "
            "The instrument may not have usable volume data."
        )

    latest = df.iloc[-1]

    close_price = float(latest["close"])
    vwap_value = float(latest["vwap"])

    point_distance = close_price - vwap_value

    if vwap_value != 0:
        percentage_distance = (
            point_distance / vwap_value
        ) * 100
    else:
        percentage_distance = 0.0

    if close_price > vwap_value:
        state = "ABOVE_VWAP"
    elif close_price < vwap_value:
        state = "BELOW_VWAP"
    else:
        state = "AT_VWAP"

    return {
        "symbol": symbol,
        "timeframe": resolution,
        "timestamp": latest["timestamp"],
        "trading_date": latest["trading_date"],
        "close": close_price,
        "vwap": vwap_value,
        "point_distance": round(point_distance, 2),
        "percentage_distance": round(
            percentage_distance,
            2
        ),
        "state": state,
        "total_candles": len(df)
    }


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    TEST_SYMBOL = "NSE:NIFTY50-INDEX"

    try:
        result = calculate_vwap(
            symbol=TEST_SYMBOL
        )

        print("\n")
        print("=" * 55)
        print("               VWAP ENGINE")
        print("=" * 55)

        print(f"Symbol          : {result['symbol']}")
        print(f"Time Frame      : {result['timeframe']} Minute")
        print(f"Trading Date    : {result['trading_date']}")
        print(f"Time            : {result['timestamp']}")

        print("-" * 55)

        print(f"Close           : {result['close']:.2f}")
        print(f"VWAP            : {result['vwap']:.2f}")
        print(
            f"Point Distance  : "
            f"{result['point_distance']:.2f}"
        )
        print(
            f"Percent Distance: "
            f"{result['percentage_distance']:.2f}%"
        )
        print(f"State           : {result['state']}")

        print("=" * 55)

    except Exception as error:
        print("\n")
        print("=" * 55)
        print("              VWAP ENGINE ERROR")
        print("=" * 55)
        print(error)
        print("=" * 55)