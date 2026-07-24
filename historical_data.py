from datetime import datetime

from fyers_apiv3 import fyersModel

from config import APP_ID


# =====================================================
# LOAD ACCESS TOKEN
# =====================================================

with open("access_token.txt", "r") as file:
    ACCESS_TOKEN = file.read().strip()


# =====================================================
# CREATE FYERS OBJECT
# =====================================================

fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=ACCESS_TOKEN,
    is_async=False
)


# =====================================================
# REQUEST HISTORICAL DATA
# =====================================================

data = {
    "symbol": "NSE:NIFTY50-INDEX",
    "resolution": "1",
    "date_format": "1",
    "range_from": "2026-07-01",
    "range_to": "2026-07-21",
    "cont_flag": "1"
}


# =====================================================
# FETCH HISTORICAL DATA
# =====================================================

response = fyers.history(data=data)


# =====================================================
# VALIDATE RESPONSE
# =====================================================

if response.get("s") == "error":
    print("\nFYERS Historical Data Error")
    print(response)
    raise SystemExit(1)

if "candles" not in response:
    print("\nUnexpected FYERS response")
    print(response)
    raise SystemExit(1)


# =====================================================
# GET ALL CANDLES
# =====================================================

candles = response["candles"]


if not candles:
    print("\nNo candle data received.")
    raise SystemExit(1)


# =====================================================
# GET LATEST CANDLE
# =====================================================

latest = candles[-1]

timestamp = latest[0]
open_price = latest[1]
high_price = latest[2]
low_price = latest[3]
close_price = latest[4]
volume = latest[5]

time = datetime.fromtimestamp(timestamp).strftime("%d-%m-%Y %H:%M:%S")


# =====================================================
# PRINT DASHBOARD
# =====================================================

print("\n")
print("=" * 50)
print("           PROJECT COMMANDER")
print("=" * 50)

print(f"Symbol          : NIFTY50")
print(f"Time Frame      : 1 Minute")
print(f"Total Candles   : {len(candles)}")

print("-" * 50)

print(f"Time            : {time}")
print(f"Open            : {open_price}")
print(f"High            : {high_price}")
print(f"Low             : {low_price}")
print(f"Close           : {close_price}")
print(f"Volume          : {volume}")

print("=" * 50)