from historical_data import get_historical_data
from live_cache import (
    get_live_quote as get_cached_live_quote,
    get_live_quotes as get_cached_live_quotes,
)


def get_live_quote(symbols):
    """
    Backward-compatible live quote function.

    Input:
        Single FYERS symbol
        OR comma-separated FYERS symbols

    Output:
        Existing project format:
        [
            {
                "n": symbol,
                "v": quote_values,
            }
        ]
    """

    if not symbols:
        return []

    symbol_list = [
        symbol.strip()
        for symbol in str(symbols).split(",")
        if symbol.strip()
    ]

    if not symbol_list:
        return []

    try:
        if len(symbol_list) == 1:
            symbol = symbol_list[0]
            quote = get_cached_live_quote(symbol)

            return [
                {
                    "n": symbol,
                    "v": quote,
                }
            ]

        quote_map = get_cached_live_quotes(
            symbol_list
        )

        return [
            {
                "n": symbol,
                "v": quote_map[symbol],
            }
            for symbol in symbol_list
            if symbol in quote_map
        ]

    except Exception as error:
        print(
            f"LIVE QUOTE ERROR: {error}"
        )
        return []


if __name__ == "__main__":
    print(
        "market_data.py ready — "
        "live cache connected"
    )
