import pandas as pd
import pandas_ta as ta

from historical_data import candles

# =====================================================
# CREATE DATAFRAME
# =====================================================

df = pd.DataFrame(
    candles,
    columns=[
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]
)

# =====================================================
# FORMAT DATA
# =====================================================

df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

df["open"] = df["open"].astype(float)
df["high"] = df["high"].astype(float)
df["low"] = df["low"].astype(float)
df["close"] = df["close"].astype(float)

# =====================================================
# SUPERTREND
# =====================================================

st = ta.supertrend(
    high=df["high"],
    low=df["low"],
    close=df["close"],
    length=10,
    multiplier=3
)

df = pd.concat([df, st], axis=1)

# =====================================================
# LATEST CANDLE
# =====================================================

latest = df.iloc[-1]

print("\n")
print("=" * 50)
print("           SUPERTREND ENGINE")
print("=" * 50)

print(f"Time              : {latest['timestamp']}")
print(f"Open              : {latest['open']}")
print(f"High              : {latest['high']}")
print(f"Low               : {latest['low']}")
print(f"Close             : {latest['close']}")

print("\n")

print(df.tail())

print("\n")
print("=" * 50)