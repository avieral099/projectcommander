from datetime import datetime, timedelta
from threading import Lock
from time import monotonic

from fyers_client import fyers


# Cache settings
CACHE_TTL_SECONDS = 60

_cache = {}
_cache_lock = Lock()


def get_date_range(resolution):
    """
    Return a suitable dynamic date range for FYERS historical data.
    """

    today = datetime.now().date()
    resolution = str(resolution).upper()

    if resolution == "D":
        start_date = today - timedelta(days=120)

    elif resolution in {"60", "30", "15"}:
        start_date = today - timedelta(days=30)

    elif resolution in {"10", "5"}:
        start_date = today - timedelta(days=15)

    else:
        # 1-minute and other short intraday resolutions
        start_date = today - timedelta(days=7)

    return (
        start_date.strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d"),
    )


def _cache_key(symbol, resolution, range_from, range_to):
    return (
        str(symbol),
        str(resolution),
        str(range_from),
        str(range_to),
    )


def clear_historical_cache(symbol=None):
    """
    Clear all cached candles or only candles belonging to one symbol.
    """

    with _cache_lock:
        if symbol is None:
            _cache.clear()
            return

        keys_to_remove = [
            key
            for key in _cache
            if key[0] == symbol
        ]

        for key in keys_to_remove:
            _cache.pop(key, None)


def get_historical_data(
    symbol,
    resolution,
    range_from=None,
    range_to=None,
    force_refresh=False,
):
    """
    Fetch FYERS historical candle data with temporary in-memory caching.

    Return format:
        [
            [timestamp, open, high, low, close, volume],
            ...
        ]
    """

    if not symbol:
        raise ValueError("Historical data symbol is required")

    resolution = str(resolution)

    if range_from is None or range_to is None:
        dynamic_from, dynamic_to = get_date_range(
            resolution
        )

        range_from = range_from or dynamic_from
        range_to = range_to or dynamic_to

    key = _cache_key(
        symbol,
        resolution,
        range_from,
        range_to,
    )

    now = monotonic()

    if not force_refresh:
        with _cache_lock:
            cached = _cache.get(key)

            if cached:
                age = now - cached["stored_at"]

                if age < CACHE_TTL_SECONDS:
                    return cached["candles"]

    request_data = {
        "symbol": symbol,
        "resolution": resolution,
        "date_format": "1",
        "range_from": range_from,
        "range_to": range_to,
        "cont_flag": "1",
    }

    response = fyers.history(
        data=request_data
    )

    if not isinstance(response, dict):
        raise RuntimeError(
            f"Invalid historical response for "
            f"{symbol}, resolution {resolution}"
        )

    if response.get("s") != "ok":
        message = response.get(
            "message",
            response,
        )

        raise RuntimeError(
            f"Historical error [{symbol}, "
            f"{resolution}]: {message}"
        )

    candles = response.get(
        "candles",
        [],
    )

    if not candles:
        raise RuntimeError(
            f"No historical candles received for "
            f"{symbol}, resolution {resolution}"
        )

    with _cache_lock:
        _cache[key] = {
            "stored_at": now,
            "candles": candles,
        }

    return candles


def get_cache_status():
    """
    Return cache information for debugging.
    """

    with _cache_lock:
        return {
            "entries": len(_cache),
            "keys": list(_cache.keys()),
        }


if __name__ == "__main__":
    print(
        "historical_data.py ready — "
        "cache enabled"
    )
