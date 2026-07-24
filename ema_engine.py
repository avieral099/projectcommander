# Import Required Libraries

from market_data import get_historical_data

# Fetch Historical Data

candles = get_historical_data(
    "NSE:NIFTY50-INDEX",
    "5"
)

# Extract Closing Prices

close_prices = []

for candle in candles:
    close_prices.append(candle[4])

# EMA Function

def calculate_ema(prices, period):

    multiplier = 2 / (period + 1)

    ema = sum(prices[:period]) / period

    for price in prices[period:]:
        ema = ((price - ema) * multiplier) + ema

    return ema

# Calculate EMAs

ema20 = calculate_ema(close_prices, 20)
ema50 = calculate_ema(close_prices, 50)
ema100 = calculate_ema(close_prices, 100)
ema200 = calculate_ema(close_prices, 200)

# Print Dashboard

print("=" * 50)
print("        PROJECT COMMANDER")
print("          EMA ENGINE")
print("=" * 50)

print(f"EMA 20      : {ema20:.2f}")
print(f"EMA 50      : {ema50:.2f}")
print(f"EMA 100     : {ema100:.2f}")
print(f"EMA 200     : {ema200:.2f}")

print("=" * 50)
