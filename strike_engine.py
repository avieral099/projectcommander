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


def round_to_nearest_strike(spot_price, strike_step):
    """
    Round spot price to the nearest valid strike.

    Python's built-in round uses bankers rounding, so we use
    explicit half-up logic for predictable strike selection.
    """
    return int(
        ((float(spot_price) + strike_step / 2) // strike_step)
        * strike_step
    )


def get_spot_price(symbol):
    quote_response = get_live_quote(symbol)

    if not quote_response:
        raise RuntimeError(
            f"No live quote received for {symbol}"
        )

    quote = quote_response[0].get("v", {})
    spot_price = quote.get("lp")

    if spot_price is None:
        raise RuntimeError(
            f"LTP missing in live quote for {symbol}"
        )

    return float(spot_price)


def calculate_strike_universe(symbol, spot_price=None):
    """
    Build ATM, ITM and OTM strike universe for CALL and PUT.

    CALL:
        ITM strikes are below ATM.
        OTM strikes are above ATM.

    PUT:
        ITM strikes are above ATM.
        OTM strikes are below ATM.
    """

    if symbol not in INDEX_CONFIG:
        raise ValueError(
            f"Unsupported index symbol: {symbol}"
        )

    config = INDEX_CONFIG[symbol]
    strike_step = int(config["strike_step"])

    if spot_price is None:
        spot_price = get_spot_price(symbol)

    spot_price = float(spot_price)

    if spot_price <= 0:
        raise ValueError(
            f"Invalid spot price for {symbol}: {spot_price}"
        )

    atm_strike = round_to_nearest_strike(
        spot_price,
        strike_step,
    )

    call_strikes = {
        "ITM2": atm_strike - (2 * strike_step),
        "ITM1": atm_strike - strike_step,
        "ATM": atm_strike,
        "OTM1": atm_strike + strike_step,
        "OTM2": atm_strike + (2 * strike_step),
    }

    put_strikes = {
        "ITM2": atm_strike + (2 * strike_step),
        "ITM1": atm_strike + strike_step,
        "ATM": atm_strike,
        "OTM1": atm_strike - strike_step,
        "OTM2": atm_strike - (2 * strike_step),
    }

    distance_from_atm = round(
        spot_price - atm_strike,
        2,
    )

    return {
        "symbol": symbol,
        "index_name": config["name"],
        "spot_price": round(spot_price, 2),
        "strike_step": strike_step,
        "atm_strike": atm_strike,
        "distance_from_atm": distance_from_atm,
        "call_strikes": call_strikes,
        "put_strikes": put_strikes,
    }


def print_strike_universe(result):
    print("=" * 70)
    print(
        f"{result['index_name']} STRIKE UNIVERSE"
    )
    print("=" * 70)

    print(
        f"SPOT PRICE          : "
        f"{result['spot_price']:.2f}"
    )
    print(
        f"STRIKE STEP         : "
        f"{result['strike_step']}"
    )
    print(
        f"ATM STRIKE          : "
        f"{result['atm_strike']}"
    )
    print(
        f"DISTANCE FROM ATM   : "
        f"{result['distance_from_atm']:+.2f}"
    )

    print("-" * 70)
    print("CALL STRIKES")
    print("-" * 70)

    for moneyness, strike in result[
        "call_strikes"
    ].items():
        print(
            f"{moneyness:<5}              : "
            f"{strike} CE"
        )

    print("-" * 70)
    print("PUT STRIKES")
    print("-" * 70)

    for moneyness, strike in result[
        "put_strikes"
    ].items():
        print(
            f"{moneyness:<5}              : "
            f"{strike} PE"
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
            result = calculate_strike_universe(
                symbol
            )
            print_strike_universe(result)

        except Exception as error:
            print("=" * 70)
            print(
                f"STRIKE ENGINE ERROR [{symbol}]"
            )
            print(error)
            print("=" * 70)
