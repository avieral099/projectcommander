from market_data import get_live_quote


INDEX_CONFIG = {
    "NSE:NIFTY50-INDEX": {
        "name": "NIFTY",
        "strike_step": 50,
    },
    "NSE:NIFTYBANK-INDEX": {
        "name": "BANKNIFTY",
        "strike_step": 100,
    },
    "BSE:SENSEX-INDEX": {
        "name": "SENSEX",
        "strike_step": 100,
    },
}


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def round_to_nearest_strike(
    spot_price,
    strike_step,
):
    """
    Predictable half-up strike rounding.
    """

    spot_price = safe_float(spot_price)

    return int(
        (
            (
                spot_price
                + strike_step / 2
            )
            // strike_step
        )
        * strike_step
    )


def get_spot_price(symbol):
    """
    Spot LTP now comes through market_data,
    which is already connected to shared live cache.
    """

    quote_response = get_live_quote(symbol)

    if not quote_response:
        raise RuntimeError(
            f"No cached live quote received for {symbol}"
        )

    quote = quote_response[0].get(
        "v",
        {},
    )

    spot_price = quote.get("lp")

    if spot_price is None:
        raise RuntimeError(
            f"LTP missing in cached quote for {symbol}"
        )

    spot_price = safe_float(spot_price)

    if spot_price <= 0:
        raise RuntimeError(
            f"Invalid spot price for {symbol}: "
            f"{spot_price}"
        )

    return spot_price


def calculate_strike_universe(
    symbol,
    spot_price=None,
):
    """
    Build ATM, ITM1/2 and OTM1/2 strikes.

    CALL:
        ITM below ATM
        OTM above ATM

    PUT:
        ITM above ATM
        OTM below ATM
    """

    if symbol not in INDEX_CONFIG:
        raise ValueError(
            f"Unsupported index symbol: {symbol}"
        )

    config = INDEX_CONFIG[symbol]
    strike_step = int(
        config["strike_step"]
    )

    if spot_price is None:
        spot_price = get_spot_price(symbol)

    spot_price = safe_float(spot_price)

    if spot_price <= 0:
        raise ValueError(
            f"Invalid spot price for {symbol}: "
            f"{spot_price}"
        )

    atm_strike = round_to_nearest_strike(
        spot_price,
        strike_step,
    )

    call_strikes = {
        "ITM2": (
            atm_strike
            - 2 * strike_step
        ),
        "ITM1": (
            atm_strike
            - strike_step
        ),
        "ATM": atm_strike,
        "OTM1": (
            atm_strike
            + strike_step
        ),
        "OTM2": (
            atm_strike
            + 2 * strike_step
        ),
    }

    put_strikes = {
        "ITM2": (
            atm_strike
            + 2 * strike_step
        ),
        "ITM1": (
            atm_strike
            + strike_step
        ),
        "ATM": atm_strike,
        "OTM1": (
            atm_strike
            - strike_step
        ),
        "OTM2": (
            atm_strike
            - 2 * strike_step
        ),
    }

    return {
        "symbol": symbol,
        "index_name": config["name"],
        "spot_price": round(
            spot_price,
            2,
        ),
        "strike_step": strike_step,
        "atm_strike": atm_strike,
        "distance_from_atm": round(
            spot_price - atm_strike,
            2,
        ),
        "call_strikes": call_strikes,
        "put_strikes": put_strikes,
    }
