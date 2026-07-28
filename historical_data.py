from datetime import datetime, timedelta
from threading import Lock
from time import monotonic, sleep

from fyers_client import fyers


CACHE_TTL_SECONDS = 60
MIN_REQUEST_INTERVAL_SECONDS = 0.50
MAX_RETRIES = 4

_cache = {}
_cache_lock = Lock()

_request_lock = Lock()
_last_request_time = 0.0


def get_date_range(resolution):
    today = datetime.now().date()
    resolution = str(resolution).upper()

    if resolution == "D":
        start_date = today - timedelta(days=120)

    elif resolution in {"60", "30", "15"}:
        start_date = today - timedelta(days=30)

    elif resolution in {"10", "5"}:
        start_date = today - timedelta(days=15)

    else:
        start_date = today - timedelta(days=7)

    return (
        start_date.strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d"),
    )


def _cache_key(
    symbol,
    resolution,
    range_from,
    range_to,
):
    return (
        str(symbol),
        str(resolution),
        str(range_from),
        str(range_to),
    )


def clear_historical_cache(symbol=None):
    with _cache_lock:
        if symbol is None:
            _cache.clear()
            return

        keys = [
            key
            for key in _cache
            if key[0] == symbol
        ]

        for key in keys:
            _cache.pop(key, None)


def _paced_history_request(request_data):
    """
    FYERS historical requests ko controlled speed par bhejta hai.
    Request-limit response par automatic retry karta hai.
    """

    global _last_request_time

    last_response = None

    for attempt in range(MAX_RETRIES):
        with _request_lock:
            elapsed = (
                monotonic()
                - _last_request_time
            )

            wait_time = (
                MIN_REQUEST_INTERVAL_SECONDS
                - elapsed
            )

            if wait_time > 0:
                sleep(wait_time)

            response = fyers.history(
                data=request_data
            )

            _last_request_time = monotonic()

        last_response = response

        if (
            isinstance(response, dict)
            and response.get("s") == "ok"
            and response.get("candles")
        ):
            return response

        message = str(
            response.get("message", "")
            if isinstance(response, dict)
            else response
        ).lower()

        if "request limit" not in message:
            return response

        retry_delay = 1.5 * (attempt + 1)

        print(
            f"HISTORICAL RATE LIMIT — "
            f"retry {attempt + 1}/{MAX_RETRIES} "
            f"after {retry_delay:.1f}s"
        )

        sleep(retry_delay)

    return last_response


def get_historical_data(
    symbol,
    resolution,
    range_from=None,
    range_to=None,
    force_refresh=False,
):
    if not symbol:
        raise ValueError(
            "Historical data symbol is required"
        )

    resolution = str(resolution)

    if range_from is None or range_to is None:
        dynamic_from, dynamic_to = (
            get_date_range(resolution)
        )

        range_from = (
            range_from or dynamic_from
        )

        range_to = (
            range_to or dynamic_to
        )

    key = _cache_key(
        symbol,
        resolution,
        range_from,
        range_to,
    )

    now = monotonic()
    stale_candles = None

    with _cache_lock:
        cached = _cache.get(key)

        if cached:
            stale_candles = cached["candles"]
            age = now - cached["stored_at"]

            if (
                not force_refresh
                and age < CACHE_TTL_SECONDS
            ):
                return cached["candles"]

    request_data = {
        "symbol": symbol,
        "resolution": resolution,
        "date_format": "1",
        "range_from": range_from,
        "range_to": range_to,
        "cont_flag": "1",
    }

    response = _paced_history_request(
        request_data
    )

    if not isinstance(response, dict):
        if stale_candles:
            return stale_candles

        raise RuntimeError(
            f"Invalid historical response for "
            f"{symbol}, resolution {resolution}"
        )

    if (
        response.get("s") != "ok"
        or not response.get("candles")
    ):
        if stale_candles:
            return stale_candles

        raise RuntimeError(
            f"Historical error [{symbol}, "
            f"{resolution}]: "
            f"{response.get('message', response)}"
        )

    candles = response["candles"]

    with _cache_lock:
        _cache[key] = {
            "stored_at": monotonic(),
            "candles": candles,
        }

    return candles


def get_cache_status():
    with _cache_lock:
        return {
            "entries": len(_cache),
            "keys": list(_cache.keys()),
        }


if __name__ == "__main__":
    print(
        "historical_data.py ready — "
        "cache, pacing and retry enabled"
    )
