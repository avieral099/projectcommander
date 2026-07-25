from threading import Lock
from time import monotonic

from fyers_client import fyers


CACHE_TTL_SECONDS = 2

_cache = {}
_cache_time = 0.0
_cache_lock = Lock()


def safe_dict(value):
    return value if isinstance(value, dict) else {}


def refresh_live_cache(symbols, force=False):
    """
    Fetch all requested symbols in one FYERS quotes call
    and store them in memory.
    """

    global _cache
    global _cache_time

    symbol_list = [
        symbol.strip()
        for symbol in symbols
        if symbol and symbol.strip()
    ]

    if not symbol_list:
        raise ValueError("At least one symbol is required")

    now = monotonic()

    with _cache_lock:
        cache_is_fresh = (
            _cache
            and not force
            and now - _cache_time < CACHE_TTL_SECONDS
            and all(symbol in _cache for symbol in symbol_list)
        )

        if cache_is_fresh:
            return {
                symbol: _cache[symbol]
                for symbol in symbol_list
            }

    response = fyers.quotes(
        data={
            "symbols": ",".join(symbol_list),
        }
    )

    if not isinstance(response, dict):
        raise RuntimeError("Invalid FYERS quotes response")

    if response.get("s") != "ok":
        raise RuntimeError(
            f"Live quote error: "
            f"{response.get('message', response)}"
        )

    new_quotes = {}

    for item in response.get("d", []):
        symbol = item.get("n")
        values = safe_dict(item.get("v"))

        if symbol and values:
            new_quotes[symbol] = values

    missing_symbols = [
        symbol
        for symbol in symbol_list
        if symbol not in new_quotes
    ]

    if missing_symbols:
        raise RuntimeError(
            "Missing live quotes for: "
            + ", ".join(missing_symbols)
        )

    with _cache_lock:
        _cache.update(new_quotes)
        _cache_time = now

        return {
            symbol: _cache[symbol]
            for symbol in symbol_list
        }


def get_live_quote(symbol):
    """
    Return one symbol from cache.
    Automatically refresh if missing or stale.
    """

    quotes = refresh_live_cache([symbol])
    return quotes[symbol]


def get_live_quotes(symbols):
    """
    Return multiple symbols from one shared cache refresh.
    """

    return refresh_live_cache(symbols)


def clear_live_cache():
    global _cache
    global _cache_time

    with _cache_lock:
        _cache = {}
        _cache_time = 0.0


def get_live_cache_status():
    with _cache_lock:
        return {
            "entries": len(_cache),
            "symbols": list(_cache.keys()),
            "age_seconds": round(
                monotonic() - _cache_time,
                2,
            ) if _cache_time else None,
            "ttl_seconds": CACHE_TTL_SECONDS,
        }


if __name__ == "__main__":
    print("live_cache.py ready")
