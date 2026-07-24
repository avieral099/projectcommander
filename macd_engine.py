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

def calculate_ema_series(prices, period):

    multiplier = 2 / (period + 1)

    ema_values = []

    ema = sum(prices[:period]) / period

    ema_values.append(ema)

    for price in prices[period:]:

        ema = ((price - ema) * multiplier) + ema

        ema_values.append(ema)

    return ema_values

# Calculate EMA 12 and EMA 26

ema12 = calculate_ema_series(close_prices, 12)

ema26 = calculate_ema_series(close_prices, 26)

# Match Length

difference = len(ema12) - len(ema26)

ema12 = ema12[difference:]

# MACD Line

macd = []

for i in range(len(ema26)):
    macd.append(ema12[i] - ema26[i])

# Signal Line

signal = calculate_ema_series(macd, 9)

# Latest Values

latest_macd = macd[-1]

latest_signal = signal[-1]
print("Candles:", len(candles))
print("First close:",  close_prices[0])
print("Last close:",   close_prices[-1])
print("MACD exact:",   repr(latest_macd))
print("Signal exact:", repr(latest_signal))

# Dashboard

print("=" * 55)
print("      PROJECT COMMANDER")
print("          MACD ENGINE")
print("=" * 55)

print(f"MACD        : {latest_macd:.2f}")
print(f"SIGNAL      : {latest_signal:.2f}")

print("-" * 55)

if latest_macd > latest_signal:

    print("STATUS : BULLISH 🟢")

elif latest_macd < latest_signal:

    print("STATUS : BEARISH 🔴")

else:

    print("STATUS : NEUTRAL 🟡")

print("=" * 55)