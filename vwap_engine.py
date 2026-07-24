# Import Required Libraries
from market_data import get_historical_data
# Fetch Intraday Data (5 Minute)
candles = get_historical_data(
    "NSE:NIFTY50-INDEX",
    "5"
)
# Initialize Variables
cumulative_tpv = 0
cumulative_volume = 0
# Calculate VWAP
for candle in candles:
    high = candle[2]
    low = candle[3]
    close = candle[4]
    volume = candle[5]
    typical_price = (high + low + close) / 3
    cumulative_tpv += typical_price * volume
    cumulative_volume += volume
# Final VWAP
vwap = cumulative_tpv / cumulative_volume
# Print Result
print("=" * 55)
print("             VWAP ENGINE")
print("=" * 55)
print(f"VWAP : {vwap:.2f}")
print("=" * 55)