# Import Required Libraries

from market_data import get_historical_data

# Fetch Historical Data
# Fetch Historical Data


# RSI Function

def calculate_rsi(prices, period=14):

    gains = []
    losses = []

    for i in range(1, period + 1):

        change = prices[i] - prices[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for i in range(period + 1, len(prices)):

        change = prices[i] - prices[i - 1]

        gain = max(change, 0)
        loss = abs(min(change, 0))

        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi
symbols = [
    "NSE:NIFTY50-INDEX",
    "NSE:NIFTYBANK-INDEX",
    "BSE:SENSEX-INDEX"
]

for symbol in symbols:

    candles = get_historical_data(
        symbol,
        "5"
    )

    close_prices = []

    for candle in candles:
        close_prices.append(candle[4])

    rsi = calculate_rsi(close_prices)

    print("=" * 50)
    print(symbol)
    print(f"RSI : {rsi:.2f}")

    if rsi > 70:
        print("STATUS : OVERBOUGHT 🔴")

    elif rsi < 30:
        print("STATUS : OVERSOLD 🟢")

    else:
        print("STATUS : NEUTRAL 🟡")

# Calculate RSI

rsi = calculate_rsi(close_prices)

# Print Dashboard

print("=" * 50)
print("        PROJECT COMMANDER")
print("           RSI ENGINE")
print("=" * 50)

print(f"RSI : {rsi:.2f}")

if rsi > 70:
    print("STATUS : OVERBOUGHT 🔴")

elif rsi < 30:
    print("STATUS : OVERSOLD 🟢")

else:
    print("STATUS : NEUTRAL 🟡")

print("=" * 50)
