# Import Required Libraries

from fyers_client import fyers


# Get Live Quote

def get_live_quote(symbols):

    data = {
        "symbols": symbols
    }

    response = fyers.quotes(data=data)

   # print("FYERS RESPONSE :", response)

    if "d" in response:
        return response["d"]

   # print("FYERS ERROR :", response.get("message", response))

    return []


# Get Historical Data

def get_historical_data(symbol, resolution):

    data = {
        "symbol": symbol,
        "resolution": resolution,
        "date_format": "1",
        "range_from": "2026-07-01",
        "range_to": "2026-07-22",
        "cont_flag": "1"
    }

    response = fyers.history(data=data)

   # print("HISTORICAL RESPONSE :", response)

    if "candles" in response:
        return response["candles"]

    print("HISTORICAL ERROR :", response.get("message", response))

    return []
