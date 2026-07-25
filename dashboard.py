# dashboard.py

from market_data import get_live_quote
from price_levels import get_price_levels
from vwap_engine import calculate_vwap
from ema_engine import calculate_ema


SYMBOLS = (
    "NSE:NIFTY50-INDEX,"
    "NSE:NIFTYBANK-INDEX,"
    "BSE:SENSEX-INDEX"
)


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def main():
    print("=" * 70)
    print("                       PROJECT COMMANDER")
    print("=" * 70)

    try:
        quotes = get_live_quote(SYMBOLS)
    except Exception as error:
        print(f"LIVE MARKET DATA ERROR: {error}")
        return

    if not quotes:
        print("LIVE MARKET DATA NOT AVAILABLE")
        return

    for item in quotes:
        quote = item.get("v", {})
        symbol = item.get("n")

        if not symbol:
            print("SYMBOL MISSING IN FYERS RESPONSE")
            continue

        short_name = quote.get(
            "short_name",
            symbol,
        )

        # --------------------------------------------------
        # Symbol-specific price levels
        # --------------------------------------------------
        try:
            levels = get_price_levels(symbol)

            previous_open = safe_float(
                levels.get("previous_open")
            )
            previous_high = safe_float(
                levels.get("previous_high")
            )
            previous_low = safe_float(
                levels.get("previous_low")
            )
            previous_close = safe_float(
                levels.get("previous_close")
            )

            today_open = levels.get("today_open")
            previous_day_date = levels.get(
                "previous_day_date",
                "UNKNOWN",
            )

        except Exception as error:
            print(f"PRICE LEVEL ERROR [{symbol}]: {error}")

            previous_open = 0.0
            previous_high = 0.0
            previous_low = 0.0
            previous_close = 0.0
            today_open = None
            previous_day_date = "ERROR"

        # --------------------------------------------------
        # Symbol-specific VWAP
        # --------------------------------------------------
        try:
            vwap_result = calculate_vwap(
                symbol=symbol,
                resolution="5",
            )

            vwap_value = safe_float(
                vwap_result.get("vwap")
            )
            vwap_state = vwap_result.get(
                "state",
                "UNKNOWN",
            )
            vwap_distance = safe_float(
                vwap_result.get("percentage_distance")
            )

        except Exception as error:
            print(f"VWAP ERROR [{symbol}]: {error}")

            vwap_value = 0.0
            vwap_state = "ERROR"
            vwap_distance = 0.0

        # --------------------------------------------------
        # Symbol-specific EMA75 High / Low
        # --------------------------------------------------
        try:
            ema_result = calculate_ema(
                symbol=symbol,
                resolution="5",
            )

            ema75_high = safe_float(
                ema_result.get("ema75_high")
            )
            ema75_low = safe_float(
                ema_result.get("ema75_low")
            )

            ema75_high_relation = ema_result.get(
                "ema75_high_relation",
                "UNKNOWN",
            )
            ema75_low_relation = ema_result.get(
                "ema75_low_relation",
                "UNKNOWN",
            )

            ema_distance_high = safe_float(
                ema_result.get("percentage_distance_high")
            )
            ema_distance_low = safe_float(
                ema_result.get("percentage_distance_low")
            )

            ema_structure = ema_result.get(
                "structure_state",
                "UNKNOWN",
            )

        except Exception as error:
            print(f"EMA ERROR [{symbol}]: {error}")

            ema75_high = 0.0
            ema75_low = 0.0
            ema75_high_relation = "ERROR"
            ema75_low_relation = "ERROR"
            ema_distance_high = 0.0
            ema_distance_low = 0.0
            ema_structure = "ERROR"

        # --------------------------------------------------
        # Live quote values
        # --------------------------------------------------
        ltp = safe_float(quote.get("lp"))
        change = safe_float(quote.get("ch"))
        change_pct = safe_float(quote.get("chp"))

        # --------------------------------------------------
        # Print dashboard
        # --------------------------------------------------
        print(f"\n{short_name}")
        print("=" * 70)

        print(f"SYMBOL                 : {symbol}")
        print(f"LTP                    : {ltp:.2f}")
        print(f"CHANGE                 : {change:.2f}")
        print(f"CHANGE %               : {change_pct:.2f}%")

        print("-" * 70)

        print(f"PREVIOUS DAY DATE      : {previous_day_date}")
        print(f"PREVIOUS DAY OPEN      : {previous_open:.2f}")
        print(f"PREVIOUS DAY HIGH      : {previous_high:.2f}")
        print(f"PREVIOUS DAY LOW       : {previous_low:.2f}")
        print(f"PREVIOUS DAY CLOSE     : {previous_close:.2f}")

        if today_open is None:
            print("TODAY OPEN             : MARKET CLOSED")
        else:
            print(
                f"TODAY OPEN             : "
                f"{safe_float(today_open):.2f}"
            )

        print("-" * 70)

        print(f"VWAP                   : {vwap_value:.2f}")
        print(f"VWAP STATE             : {vwap_state}")
        print(f"VWAP DISTANCE          : {vwap_distance:.2f}%")

        print("-" * 70)

        print(f"EMA75 HIGH             : {ema75_high:.2f}")
        print(f"EMA75 HIGH RELATION    : {ema75_high_relation}")
        print(f"EMA75 HIGH DISTANCE    : {ema_distance_high:.2f}%")

        print(f"EMA75 LOW              : {ema75_low:.2f}")
        print(f"EMA75 LOW RELATION     : {ema75_low_relation}")
        print(f"EMA75 LOW DISTANCE     : {ema_distance_low:.2f}%")

        print(f"EMA STRUCTURE          : {ema_structure}")
        print("=" * 70)


if __name__ == "__main__":
    main()