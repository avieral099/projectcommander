import pandas as pd
import pandas_ta as ta

from historical_data import get_historical_data


# =====================================================
# SETTINGS
# =====================================================

DEFAULT_RESOLUTION = "1"

SUPERTREND_LENGTH = 10
SUPERTREND_MULTIPLIER = 3.0


# =====================================================
# SUPERTREND ENGINE
# =====================================================

def calculate_supertrend(
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
        subset=["high", "low", "close"],
        inplace=True
    )

    if len(df) < SUPERTREND_LENGTH + 1:
        raise RuntimeError(
            f"Not enough candles for Supertrend on {symbol}. "
            f"Received {len(df)} candles."
        )

    supertrend_data = ta.supertrend(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        length=SUPERTREND_LENGTH,
        multiplier=SUPERTREND_MULTIPLIER
    )

    if supertrend_data is None or supertrend_data.empty:
        raise RuntimeError(
            f"Supertrend calculation failed for {symbol}."
        )

    value_column = next(
        (
            column
            for column in supertrend_data.columns
            if column.startswith("SUPERT_")
            and not column.startswith("SUPERTd_")
            and not column.startswith("SUPERTl_")
            and not column.startswith("SUPERTs_")
        ),
        None
    )

    direction_column = next(
        (
            column
            for column in supertrend_data.columns
            if column.startswith("SUPERTd_")
        ),
        None
    )

    if value_column is None or direction_column is None:
        raise RuntimeError(
            "Unable to identify Supertrend columns. "
            f"Available columns: {list(supertrend_data.columns)}"
        )

    df = pd.concat(
        [df, supertrend_data],
        axis=1
    )

    df.dropna(
        subset=[value_column, direction_column],
        inplace=True
    )

    if df.empty:
        raise RuntimeError(
            f"No valid Supertrend values generated for {symbol}."
        )

    latest = df.iloc[-1]

    close_price = float(latest["close"])
    supertrend_value = float(latest[value_column])
    direction = int(latest[direction_column])
    point_distance = close_price - supertrend_value

    if supertrend_value != 0:
        percentage_distance = (
            point_distance / supertrend_value
        ) * 100
    else:
        percentage_distance = 0.0

    if direction == 1:
        state = "BULLISH"
        price_position = "ABOVE_SUPERTREND"

    elif direction == -1:
        state = "BEARISH"
        price_position = "BELOW_SUPERTREND"

    else:
        state = "NEUTRAL"
        price_position = "AT_SUPERTREND"

    return {
        "symbol": symbol,
        "timeframe": resolution,
        "timestamp": latest["timestamp"],
        "close": close_price,
        "supertrend": supertrend_value,
        "direction": direction,
        "state": state,
        "price_position": price_position,
        "point_distance": round(point_distance, 2),
        "percentage_distance": round(
            percentage_distance,
            2
        ),
        "total_candles": len(df)
    }


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    TEST_SYMBOL = "NSE:NIFTY50-INDEX"

    try:
        result = calculate_supertrend(
            symbol=TEST_SYMBOL
        )

        print("\n")
        print("=" * 55)
        print("              SUPERTREND ENGINE")
        print("=" * 55)

        print(f"Symbol          : {result['symbol']}")
        print(f"Time Frame      : {result['timeframe']} Minute")
        print(f"Total Candles   : {result['total_candles']}")

        print("-" * 55)

        print(f"Time            : {result['timestamp']}")
        print(f"Close           : {result['close']:.2f}")
        print(f"Supertrend      : {result['supertrend']:.2f}")
        print(
            f"Point Distance  : "
            f"{result['point_distance']:.2f}"
        )
        print(
            f"Percent Distance: "
            f"{result['percentage_distance']:.2f}%"
        )
        print(f"Direction       : {result['direction']}")
        print(f"State           : {result['state']}")
        print(f"Price Position  : {result['price_position']}")

        print("=" * 55)

    except Exception as error:
        print("\n")
        print("=" * 55)
        print("          SUPERTREND ENGINE ERROR")
        print("=" * 55)
        print(error)
        print("=" * 55)