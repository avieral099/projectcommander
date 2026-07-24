# Import Required Libraries

from ema_engine import ema20, ema50, ema100, ema200
from rsi_engine import rsi
from price_levels import previous_high, previous_low, previous_close

# Print Header

print("=" * 60)
print("          PROJECT COMMANDER SIGNAL ENGINE")
print("=" * 60)

# EMA

print(f"EMA20               : {ema20:.2f}")
print(f"EMA50               : {ema50:.2f}")
print(f"EMA100              : {ema100:.2f}")
print(f"EMA200              : {ema200:.2f}")

print("-" * 60)

# Previous Day Levels

print(f"Previous Day High   : {previous_high}")
print(f"Previous Day Low    : {previous_low}")
print(f"Previous Day Close  : {previous_close}")

print("-" * 60)

# RSI

print(f"RSI                 : {rsi:.2f}")

print("-" * 60)

# Trend

if ema20 > ema50 and ema50 > ema100:

    trend = "BULLISH 🟢"

elif ema20 < ema50 and ema50 < ema100:

    trend = "BEARISH 🔴"

else:

    trend = "SIDEWAYS 🟡"

print(f"TREND               : {trend}")

print("=" * 60)
