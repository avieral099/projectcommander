from datetime import datetime
from zoneinfo import ZoneInfo

from market_data import get_historical_data, get_live_quote


IST = ZoneInfo("Asia/Kolkata")


def timestamp_to_ist(timestamp):
    return datetime.fromtimestamp(
        int(timestamp),
        tz=IST,
    )


def calculate_opening_range(
    symbol,
    start_time="09:15",
    end_time="09:30",
):
    """
    Calculate the opening range from 09:15 inclusive
    to 09:30 exclusive using 1-minute candles.
    """

    candles = get_historical_data(
        symbol,
        "1",
    )

    if not candles:
        raise RuntimeError(
            f"No 1-minute historical candles received for {symbol}"
        )

    latest_trading_date = timestamp_to_ist(
        candles[-1][0]
    ).date()

    start_hour, start_minute = map(
        int,
        start_time.split(":"),
    )

    end_hour, end_minute = map(
        int,
        end_time.split(":"),
    )

    opening_candles = []

    for candle in candles:
        candle_time = timestamp_to_ist(
            candle[0]
        )

        if candle_time.date() != latest_trading_date:
            continue

        candle_minutes = (
            candle_time.hour * 60
            + candle_time.minute
        )

        start_minutes = (
            start_hour * 60
            + start_minute
        )

        end_minutes = (
            end_hour * 60
            + end_minute
        )

        if start_minutes <= candle_minutes < end_minutes:
            opening_candles.append(candle)

    if not opening_candles:
        raise RuntimeError(
            f"No opening-range candles found for {symbol} "
            f"between {start_time} and {end_time}"
        )

    or_high = max(
        float(candle[2])
        for candle in opening_candles
    )

    or_low = min(
        float(candle[3])
        for candle in opening_candles
    )

    or_range = or_high - or_low

    quote_response = get_live_quote(symbol)

    if not quote_response:
        raise RuntimeError(
            f"No live quote received for {symbol}"
        )

    quote = quote_response[0].get(
        "v",
        {},
    )

    ltp = float(
        quote.get(
            "lp",
            0.0,
        )
    )

    if ltp > or_high:
        status = "ABOVE_ORH"
    elif ltp < or_low:
        status = "BELOW_ORL"
    else:
        status = "INSIDE_RANGE"

    return {
        "symbol": symbol,
        "trading_date": str(
            latest_trading_date
        ),
        "start_time": start_time,
        "end_time": end_time,
        "candle_count": len(
            opening_candles
        ),
        "or_high": round(
            or_high,
            2,
        ),
        "or_low": round(
            or_low,
            2,
        ),
        "or_range": round(
            or_range,
            2,
        ),
        "ltp": round(
            ltp,
            2,
        ),
        "status": status,
    }


def print_opening_range(result):
    print("=" * 70)
    print(result["symbol"])
    print("=" * 70)
    print(
        f"TRADING DATE      : "
        f"{result['trading_date']}"
    )
    print(
        f"OPENING WINDOW    : "
        f"{result['start_time']} - "
        f"{result['end_time']}"
    )
    print(
        f"CANDLE COUNT      : "
        f"{result['candle_count']}"
    )
    print("-" * 70)
    print(
        f"OR HIGH           : "
        f"{result['or_high']:.2f}"
    )
    print(
        f"OR LOW            : "
        f"{result['or_low']:.2f}"
    )
    print(
        f"OR RANGE          : "
        f"{result['or_range']:.2f}"
    )
    print(
        f"LTP               : "
        f"{result['ltp']:.2f}"
    )
    print(
        f"STATUS            : "
        f"{result['status']}"
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
            result = calculate_opening_range(
                symbol
            )

            print_opening_range(
                result
            )

        except Exception as error:
            print("=" * 70)
            print(
                f"OPENING RANGE ERROR "
                f"[{symbol}]"
            )
            print(error)
            print("=" * 70)
