# Import Required Libraries

from fyers_apiv3 import fyersModel
from config import APP_ID, ACCESS_TOKEN
from datetime import datetime

# Create FYERS Object

fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=ACCESS_TOKEN,
    is_async=False
)

# Request Historical Data

data = {
    "symbol": "NSE:NIFTY50-INDEX",
    "resolution": "5",
    "date_format": "1",
    "range_from": "2026-07-01",
    "range_to": "2026-07-21",
    "cont_flag": "1"
}

# Fetch Historical Data

response = fyers.history(data=data)

# Get All Candles

candles = response["candles"]

# Get Latest Candle

latest = candles[-1]

# Convert Timestamp to Readable Time

time = datetime.fromtimestamp(latest[0]).strftime("%d-%m-%Y %H:%M:%S")

# Print Dashboard

print("=" * 45)
print("        PROJECT COMMANDER")
print("=" * 45)

print(f"Symbol         : NIFTY50")
print(f"Time Frame     : 5 Minutes")
print(f"Total Candles  : {len(candles)}")

print("-" * 45)

print(f"Time           : {time}")
print(f"Open           : {latest[1]}")
print(f"High           : {latest[2]}")
print(f"Low            : {latest[3]}")
print(f"Close          : {latest[4]}")
print(f"Volume         : {latest[5]}")

print("=" * 45)
