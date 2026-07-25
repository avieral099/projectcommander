from market_data import get_live_quote
from price_levels import get_price_levels
from vwap_engine import calculate_vwap
from ema_engine import calculate_ema
from opening_range_engine import calculate_opening_range


DRIVER_SYMBOLS = {
    "NIFTYIT": "NSE:NIFTYIT-INDEX",
    "RELIANCE": "NSE:RELIANCE-EQ",
    "HDFCBANK": "NSE:HDFCBANK-EQ",
    "ICICIBANK": "NSE:ICICIBANK-EQ",
    "TCS": "NSE:TCS-EQ",
    "INFOSYS": "NSE:INFY-EQ",
}


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_bulk_live_quotes():
    symbols = list(DRIVER_SYMBOLS.values())
    quote_response = get_live_quote(
        ",".join(symbols)
    )

    quote_map = {}

    for item in quote_response:
        symbol = item.get("n")
        values = item.get("v", {})

        if symbol and values:
            quote_map[symbol] = values

    missing = [
        symbol
        for symbol in symbols
        if symbol not in quote_map
    ]

    if missing:
        raise RuntimeError(
            "Missing cached quotes for: "
            + ", ".join(missing)
        )

    return quote_map

def get_driver_snapshot(name, symbol, quote_map):
    quote = quote_map.get(symbol)

    if not quote:
        raise RuntimeError(
            f"No bulk live quote received for {symbol}"
        )

    ltp = safe_float(quote.get("lp"))
    change = safe_float(quote.get("ch"))
    change_pct = safe_float(quote.get("chp"))
    volume = int(safe_float(quote.get("volume")))

    levels = get_price_levels(symbol)

    pdc = safe_float(levels.get("previous_close"))
    pdh = safe_float(levels.get("previous_high"))
    pdl = safe_float(levels.get("previous_low"))

    vwap_result = calculate_vwap(
        symbol=symbol,
        resolution="5",
    )

    ema_result = calculate_ema(
        symbol=symbol,
        resolution="5",
    )

    try:
        opening_range = calculate_opening_range(symbol)

        or_high = safe_float(
            opening_range.get("or_high")
        )
        or_low = safe_float(
            opening_range.get("or_low")
        )
        or_status = opening_range.get(
            "status",
            "UNKNOWN",
        )

    except Exception as error:
        or_high = 0.0
        or_low = 0.0
        or_status = f"NOT_AVAILABLE: {error}"

    vwap = safe_float(vwap_result.get("vwap"))

    ema75_high = safe_float(
        ema_result.get("ema75_high")
    )
    ema75_low = safe_float(
        ema_result.get("ema75_low")
    )

    return {
        "name": name,
        "symbol": symbol,

        "ltp": ltp,
        "change": change,
        "change_pct": change_pct,
        "volume": volume,

        "pdc": pdc,
        "pdh": pdh,
        "pdl": pdl,

        "above_pdc": (
            pdc > 0 and ltp > pdc
        ),
        "below_pdc": (
            pdc > 0 and ltp < pdc
        ),

        "above_pdh": (
            pdh > 0 and ltp > pdh
        ),
        "below_pdh": (
            pdh > 0 and ltp < pdh
        ),

        "above_pdl": (
            pdl > 0 and ltp > pdl
        ),
        "below_pdl": (
            pdl > 0 and ltp < pdl
        ),

        "vwap": vwap,
        "vwap_state": vwap_result.get(
            "state",
            "UNKNOWN",
        ),
        "above_vwap": (
            vwap > 0 and ltp > vwap
        ),
        "below_vwap": (
            vwap > 0 and ltp < vwap
        ),

        "ema75_high": ema75_high,
        "ema75_low": ema75_low,
        "ema_structure": ema_result.get(
            "structure_state",
            "UNKNOWN",
        ),

        "above_ema75_high": (
            ema75_high > 0
            and ltp > ema75_high
        ),
        "below_ema75_low": (
            ema75_low > 0
            and ltp < ema75_low
        ),

        "or_high": or_high,
        "or_low": or_low,
        "or_status": or_status,

        "above_or_high": (
            or_high > 0
            and ltp > or_high
        ),
        "below_or_low": (
            or_low > 0
            and ltp < or_low
        ),
        "inside_opening_range": (
            or_high > 0
            and or_low > 0
            and or_low <= ltp <= or_high
        ),
    }


def collect_driver_data():
    result = {}

    try:
        quote_map = get_bulk_live_quotes()

    except Exception as error:
        for name, symbol in DRIVER_SYMBOLS.items():
            result[name] = {
                "name": name,
                "symbol": symbol,
                "error": str(error),
            }

        return result

    for name, symbol in DRIVER_SYMBOLS.items():
        try:
            result[name] = get_driver_snapshot(
                name=name,
                symbol=symbol,
                quote_map=quote_map,
            )

        except Exception as error:
            result[name] = {
                "name": name,
                "symbol": symbol,
                "error": str(error),
            }

    return result
