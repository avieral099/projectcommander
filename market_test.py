# Import Required Libraries

from fyers_apiv3 import fyersModel
from config import APP_ID, ACCESS_TOKEN

# Create FYERS Object

fyers = fyersModel.FyersModel(
    client_id=APP_ID,
    token=ACCESS_TOKEN,
    is_async=False
)

# Request Live Market Data

data = {
    "symbols": "NSE:NIFTY50-INDEX,NSE:NIFTYBANK-INDEX,BSE:SENSEX-INDEX"
}

# Fetch Market Quotes

response = fyers.quotes(data=data)

# Print Project Commander Dashboard

print("=" * 45)
print("        PROJECT COMMANDER")
print("=" * 45)

for item in response["d"]:
    quote = item["v"]

    print(f"{quote['short_name']}")
    print(f"LTP        : {quote['lp']}")
    print(f"CHANGE     : {quote['ch']}")
    print(f"CHANGE %   : {quote['chp']}")
    print("-" * 45)
    