from __future__ import annotations

import inspect
from datetime import datetime, timedelta
from typing import Any, Callable

import pandas as pd


class ProviderError(RuntimeError):
    pass


def _find_history_function() -> Callable[..., Any]:
    try:
        import historical_data
    except ImportError as error:
        raise ProviderError("historical_data.py could not be imported") from error

    names = (
        "get_historical_data",
        "fetch_historical_data",
        "get_history",
        "fetch_history",
        "historical_data",
    )

    for name in names:
        function = getattr(historical_data, name, None)
        if callable(function):
            return function

    raise ProviderError(
        "No supported historical-data function found in historical_data.py. "
        "Supported names: " + ", ".join(names)
    )


def _to_frame(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value

    if isinstance(value, dict):
        for key in ("candles", "data", "rows"):
            if key in value:
                value = value[key]
                break

    if isinstance(value, list):
        if not value:
            return pd.DataFrame()

        if isinstance(value[0], dict):
            return pd.DataFrame(value)

        if isinstance(value[0], (list, tuple)) and len(value[0]) >= 6:
            columns = ["timestamp", "open", "high", "low", "close", "volume"]
            return pd.DataFrame(value, columns=columns[:len(value[0])])

    raise ProviderError(f"Unsupported historical response type: {type(value).__name__}")


def fetch_candles(
    symbol: str,
    resolution: str,
    *,
    days: int,
) -> pd.DataFrame:
    function = _find_history_function()
    end = datetime.now()
    start = end - timedelta(days=days)

    attempts = [
        {
            "symbol": symbol,
            "resolution": resolution,
            "range_from": start.strftime("%Y-%m-%d"),
            "range_to": end.strftime("%Y-%m-%d"),
            "force_refresh": True,
        },
        {
            "symbol": symbol,
            "resolution": resolution,
            "date_from": start.strftime("%Y-%m-%d"),
            "date_to": end.strftime("%Y-%m-%d"),
        },
        {
            "symbol": symbol,
            "resolution": resolution,
            "days": days,
        },
    ]

    errors: list[str] = []
    signature = inspect.signature(function)

    for kwargs in attempts:
        accepted = {
            key: value
            for key, value in kwargs.items()
            if key in signature.parameters
        }

        try:
            response = function(**accepted)
            frame = _to_frame(response)
            if not frame.empty:
                return frame
        except Exception as error:
            errors.append(f"{accepted}: {error}")

    raise ProviderError(
        f"Unable to fetch {symbol} resolution={resolution}. "
        + " | ".join(errors[-3:])
    )
