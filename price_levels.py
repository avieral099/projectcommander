# price_levels.py

from datetime import datetime
from zoneinfo import ZoneInfo

from market_data import get_historical_data


IST = ZoneInfo("Asia/Kolkata")


def candle_date(candle):
    """Convert FYERS candle timestamp into Indian-market date."""
    timestamp = int(candle[0])
    return datetime.fromtimestamp(timestamp, tz=IST).date()


def get_price_levels(symbol):
    """
    Return symbol-specific previous-day levels.

    During market hours:
        latest candle = today's daily candle
        previous candle = previous trading day

    On weekends / holidays:
        latest candle itself = previous trading day
    """

    candles = get_historical_data(
        symbol,
        "D",
    )

    if not candles:
        raise ValueError(f"No daily candle data received for {symbol}")

    if len(candles) < 2:
        raise ValueError(f"Insufficient daily candle data for {symbol}")

    today_ist = datetime.now(IST).date()
    latest_candle = candles[-1]
    latest_date = candle_date(latest_candle)

    # Market day: latest candle is today's candle.
    if latest_date == today_ist:
        previous_day = candles[-2]
        current_day = latest_candle
        today_open = current_day[1]

    # Weekend / holiday: latest candle is last trading day's candle.
    else:
        previous_day = latest_candle
        today_open = None

    return {
        "symbol": symbol,
        "previous_open": float(previous_day[1]),
        "previous_high": float(previous_day[2]),
        "previous_low": float(previous_day[3]),
        "previous_close": float(previous_day[4]),
        "today_open": (
            float(today_open)
            if today_open is not None
            else None
        ),
        "previous_day_date": str(candle_date(previous_day)),
    }


if __name__ == "__main__":
    test_symbols = [
        "NSE:NIFTY50-INDEX",
        "NSE:NIFTYBANK-INDEX",
        "BSE:SENSEX-INDEX",
    ]

    for test_symbol in test_symbols:
        try:
            levels = get_price_levels(test_symbol)

            print("=" * 65)
            print(test_symbol)
            print(f"PREVIOUS DAY DATE  : {levels['previous_day_date']}")
            print(f"PREVIOUS DAY OPEN  : {levels['previous_open']:.2f}")
            print(f"PREVIOUS DAY HIGH  : {levels['previous_high']:.2f}")
            print(f"PREVIOUS DAY LOW   : {levels['previous_low']:.2f}")
            print(f"PREVIOUS DAY CLOSE : {levels['previous_close']:.2f}")

            if levels["today_open"] is None:
                print("TODAY OPEN         : MARKET CLOSED")
            else:
                print(f"TODAY OPEN         : {levels['today_open']:.2f}")

        except Exception as error:
            print(f"PRICE LEVEL ERROR [{test_symbol}]: {error}")