# pdc_engine.py

from price_levels import get_price_levels


def calculate_pdc(symbol):
    """
    Analyse the previous daily candle for a given symbol.

    Wick and body percentages are measured against:
        Previous Day Total Range = Previous High - Previous Low
    """

    levels = get_price_levels(symbol)

    previous_open = float(levels["previous_open"])
    previous_high = float(levels["previous_high"])
    previous_low = float(levels["previous_low"])
    previous_close = float(levels["previous_close"])

    total_range = previous_high - previous_low

    if total_range <= 0:
        raise ValueError(
            f"Invalid previous-day range for {symbol}: "
            f"high={previous_high}, low={previous_low}"
        )

    body_points = abs(previous_close - previous_open)

    upper_wick_points = (
        previous_high
        - max(previous_open, previous_close)
    )

    lower_wick_points = (
        min(previous_open, previous_close)
        - previous_low
    )

    # Protection against tiny floating-point negatives
    upper_wick_points = max(0.0, upper_wick_points)
    lower_wick_points = max(0.0, lower_wick_points)

    body_percent = round(
        (body_points / total_range) * 100,
        2,
    )

    upper_wick_percent = round(
        (upper_wick_points / total_range) * 100,
        2,
    )

    lower_wick_percent = round(
        (lower_wick_points / total_range) * 100,
        2,
    )

    bullish = previous_close > previous_open
    bearish = previous_close < previous_open
    doji = body_percent < 10

    # Strength currently reflects body dominance
    strength = body_percent

    # Candle classification
    if doji:
        candle_type = "DOJI"

    elif bullish and body_percent >= 80:
        candle_type = "BULLISH_MARUBOZU"

    elif bearish and body_percent >= 80:
        candle_type = "BEARISH_MARUBOZU"

    elif bullish and lower_wick_percent >= 40:
        candle_type = "BULLISH_HAMMER"

    elif bearish and upper_wick_percent >= 40:
        candle_type = "BEARISH_SHOOTING_STAR"

    elif bullish and body_percent >= 60:
        candle_type = "STRONG_BULLISH"

    elif bearish and body_percent >= 60:
        candle_type = "STRONG_BEARISH"

    elif bullish:
        candle_type = "BULLISH"

    elif bearish:
        candle_type = "BEARISH"

    else:
        candle_type = "NEUTRAL"

    # Close-position classification
    close_position_percent = round(
        ((previous_close - previous_low) / total_range) * 100,
        2,
    )

    if close_position_percent >= 75:
        close_position = "NEAR_HIGH"
    elif close_position_percent <= 25:
        close_position = "NEAR_LOW"
    else:
        close_position = "MID_RANGE"

    return {
        "symbol": symbol,
        "timeframe": "1D",
        "previous_day_date": levels.get(
            "previous_day_date",
            "UNKNOWN",
        ),

        "previous_open": previous_open,
        "previous_high": previous_high,
        "previous_low": previous_low,
        "previous_close": previous_close,

        "total_range_points": round(total_range, 2),
        "body_points": round(body_points, 2),
        "upper_wick_points": round(
            upper_wick_points,
            2,
        ),
        "lower_wick_points": round(
            lower_wick_points,
            2,
        ),

        "body_percent": body_percent,
        "upper_wick_percent": upper_wick_percent,
        "lower_wick_percent": lower_wick_percent,

        "bullish": bullish,
        "bearish": bearish,
        "doji": doji,

        "strength": strength,
        "candle_type": candle_type,

        "close_position_percent": close_position_percent,
        "close_position": close_position,

        "wick_percentage_benchmark": (
            "PERCENT_OF_PREVIOUS_DAY_HIGH_LOW_RANGE"
        ),
    }


def print_pdc_result(result):
    print("=" * 70)
    print(result["symbol"])
    print("=" * 70)

    print(f"TIMEFRAME             : {result['timeframe']}")
    print(
        f"PREVIOUS DAY DATE     : "
        f"{result['previous_day_date']}"
    )

    print("-" * 70)

    print(
        f"PREVIOUS OPEN         : "
        f"{result['previous_open']:.2f}"
    )
    print(
        f"PREVIOUS HIGH         : "
        f"{result['previous_high']:.2f}"
    )
    print(
        f"PREVIOUS LOW          : "
        f"{result['previous_low']:.2f}"
    )
    print(
        f"PREVIOUS CLOSE        : "
        f"{result['previous_close']:.2f}"
    )

    print("-" * 70)

    print(
        f"TOTAL RANGE           : "
        f"{result['total_range_points']:.2f} points"
    )
    print(
        f"BODY                  : "
        f"{result['body_points']:.2f} points"
    )
    print(
        f"UPPER WICK            : "
        f"{result['upper_wick_points']:.2f} points"
    )
    print(
        f"LOWER WICK            : "
        f"{result['lower_wick_points']:.2f} points"
    )

    print("-" * 70)

    print(
        f"BODY %                : "
        f"{result['body_percent']:.2f}%"
    )
    print(
        f"UPPER WICK %          : "
        f"{result['upper_wick_percent']:.2f}%"
    )
    print(
        f"LOWER WICK %          : "
        f"{result['lower_wick_percent']:.2f}%"
    )

    print("-" * 70)

    print(f"CANDLE TYPE           : {result['candle_type']}")
    print(f"STRENGTH              : {result['strength']:.2f}")
    print(
        f"CLOSE POSITION        : "
        f"{result['close_position']}"
    )
    print(
        f"CLOSE POSITION %      : "
        f"{result['close_position_percent']:.2f}%"
    )

    print("=" * 70)


if __name__ == "__main__":
    symbols = [
        "NSE:NIFTY50-INDEX",
        "NSE:NIFTYBANK-INDEX",
        "BSE:SENSEX-INDEX",
    ]

    for symbol in symbols:
        try:
            result = calculate_pdc(symbol)
            print_pdc_result(result)

        except Exception as error:
            print("=" * 70)
            print(f"PDC ENGINE ERROR [{symbol}]")
            print(error)
            print("=" * 70)