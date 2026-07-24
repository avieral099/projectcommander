# Import Required Libraries

from market_data import get_historical_data

# Fetch Daily Historical Data

candles = get_historical_data(
    "NSE:NIFTY50-INDEX",
    "D",
    
)

# Get Previous Day Candle

previous_day = candles[-2]

# Get Current Day Candle

today = candles[-1]

# Extract Levels

previous_high = previous_day[2]
previous_low = previous_day[3]
previous_close = previous_day[4]

today_open = today[1]

# Dashboard

print("=" * 55)
print("      PROJECT COMMANDER")
print("        PRICE LEVELS")
print("=" * 55)

print(f"PREVIOUS DAY HIGH   : {previous_high}")
print(f"PREVIOUS DAY LOW    : {previous_low}")
print(f"PREVIOUS DAY CLOSE  : {previous_close}")
print(f"TODAY OPEN          : {today_open}")

print("=" * 55)